#!/usr/bin/env python3
"""Validate and package the skills in this repository.

Also checks that .claude-plugin/marketplace.json lists existing skills and that its
plugin `version` equals each skill's metadata.version (set by tools/set_version.py during release).

Stdlib only (PyYAML is used if installed, otherwise a small built-in parser).

Usage:
  python tools/package_skill.py                  # validate + package every skill in skills/ to dist/
  python tools/package_skill.py --check          # validate only (CI)
  python tools/package_skill.py --expect-version 0.2.0   # fail unless metadata.version matches
  python tools/package_skill.py --install-claude-code    # also copy into ~/.claude/skills/
  python tools/package_skill.py skills/zotero-plugin-dev --out build

Output: dist/<name>.skill (a zip whose single top-level folder is the skill),
which can be uploaded in claude.ai or via the Skills API.
"""
import argparse, fnmatch, re, shutil, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git"}
ROOT_EXCLUDE_DIRS = {"evals"}          # kept in the repo, not shipped
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}
EXCLUDE_GLOBS = {"*.pyc", "*~"}
ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        raise ValueError("SKILL.md must start with a YAML frontmatter block (---)")
    block = m.group(1)
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(block)
    except ImportError:
        data, current = {}, None
        for line in block.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.startswith((" ", "\t")) and current:
                k, _, v = line.strip().partition(":")
                if not isinstance(data[current], dict):
                    data[current] = {}
                data[current][k.strip()] = v.strip().strip("'\"")
                continue
            k, _, v = line.partition(":")
            current = k.strip()
            data[current] = v.strip().strip("'\"") or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data


def excluded(rel):  # rel is relative to the skill folder
    parts = rel.parts
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    if len(parts) > 1 and parts[0] in ROOT_EXCLUDE_DIRS:
        return True
    return rel.name in EXCLUDE_FILES or any(fnmatch.fnmatch(rel.name, g) for g in EXCLUDE_GLOBS)


def validate(skill):
    errors = []
    md = skill / "SKILL.md"
    if not md.is_file():
        return None, [f"{md} not found"]
    try:
        fm = parse_frontmatter(md.read_text(encoding="utf-8"))
    except ValueError as e:
        return None, [str(e)]

    extra = set(fm) - ALLOWED_KEYS
    if extra:
        errors.append(f"unexpected frontmatter key(s): {', '.join(sorted(extra))}")
    name = str(fm.get("name", "")).strip()
    desc = str(fm.get("description", "")).strip()
    if not name:
        errors.append("missing 'name'")
    elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        errors.append(f"name '{name}' must be kebab-case, max 64 chars")
    elif name != skill.name:
        errors.append(f"name '{name}' should match folder name '{skill.name}'")
    if not desc:
        errors.append("missing 'description'")
    else:
        if len(desc) > 1024:
            errors.append(f"description is {len(desc)} chars (max 1024)")
        if "<" in desc or ">" in desc:
            errors.append("description must not contain angle brackets")

    nested = [p for p in skill.rglob("SKILL.md")
              if p != md and not excluded(p.relative_to(skill))]
    if nested:
        errors.append("extra SKILL.md files (only one allowed): "
                      + ", ".join(str(p.relative_to(skill)) for p in nested))

    for ref in re.findall(r"`((?:references|scripts|assets)/[^`\s]+)`", md.read_text(encoding="utf-8")):
        if not (skill / ref.rstrip("/")).exists():
            errors.append(f"SKILL.md references missing path: {ref}")
    return fm, errors


def skill_version(fm):
    meta = (fm or {}).get("metadata")
    return str(meta.get("version")) if isinstance(meta, dict) and meta.get("version") else None


def validate_marketplace(versions):
    """Check .claude-plugin/marketplace.json against the skills' metadata.version.

    Claude Code only auto-updates an installed plugin when the plugin entry's `version`
    changes, so every listed skill, the plugin entry and metadata.version must agree.
    """
    path = ROOT / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        return []
    import json
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    errors = []
    for key in ("name", "owner", "plugins"):
        if key not in data:
            errors.append(f"missing '{key}'")
    for plugin in data.get("plugins", []):
        pname = plugin.get("name", "?")
        pver = plugin.get("version")
        if not pver:
            errors.append(f"plugin '{pname}' has no 'version' (needed for auto-update)")
        for ref in plugin.get("skills", []):
            sdir = (ROOT / plugin.get("source", "./") / ref).resolve()
            if not (sdir / "SKILL.md").is_file():
                errors.append(f"plugin '{pname}' lists missing skill {ref}")
            elif sdir.name in versions and versions[sdir.name] != pver:
                errors.append(f"plugin '{pname}' version {pver!r} != {sdir.name} "
                              f"metadata.version {versions[sdir.name]!r}")
        mver = (data.get("metadata") or {}).get("version")
        if mver and pver and mver != pver:
            errors.append(f"metadata.version {mver!r} != plugin '{pname}' version {pver!r}")
    return errors


def package(skill, out):
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{skill.name}.skill"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(skill.rglob("*")):
            rel = f.relative_to(skill)
            if f.is_file() and not excluded(rel):
                zf.write(f, (Path(skill.name) / rel).as_posix())
    return target


def install_claude_code(skill):
    dest = Path.home() / ".claude" / "skills" / skill.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(skill, dest, ignore=lambda d, names: [
        n for n in names if excluded((Path(d) / n).relative_to(skill))])
    return dest


def main():
    if hasattr(sys.stdout, "reconfigure"):   # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skills", nargs="*", help="skill folders (default: every folder in skills/)")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--expect-version", help="require metadata.version to equal this (e.g. from a git tag)")
    ap.add_argument("--install-claude-code", action="store_true", help="copy into ~/.claude/skills/")
    a = ap.parse_args()

    dirs = [Path(s).resolve() for s in a.skills] or sorted(
        p for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists())
    if not dirs:
        sys.exit("no skills found")

    failed = False
    versions = {}
    for skill in dirs:
        fm, errors = validate(skill)
        version = skill_version(fm)
        versions[skill.name] = version
        if a.expect_version and str(version) != a.expect_version.lstrip("v"):
            errors.append(f"metadata.version is {version!r}, expected {a.expect_version.lstrip('v')!r}")
        if errors:
            failed = True
            print(f"✗ {skill.name}")
            for e in errors:
                print(f"    - {e}")
            continue
        print(f"✓ {skill.name} {version or ''}".rstrip())
        if a.check:
            continue
        print(f"    packaged → {package(skill, Path(a.out).resolve())}")
        if a.install_claude_code:
            print(f"    installed → {install_claude_code(skill)}")

    mp_errors = validate_marketplace(versions)
    if mp_errors:
        failed = True
        print("✗ .claude-plugin/marketplace.json")
        for e in mp_errors:
            print(f"    - {e}")
    elif (ROOT / ".claude-plugin" / "marketplace.json").is_file():
        print("✓ .claude-plugin/marketplace.json")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
