#!/usr/bin/env python3
"""Write a release version everywhere Claude Code looks for it.

Called by semantic-release (.releaserc.json, prepare step) with the version it derived
from the Conventional Commits since the last release. Don't run it by hand — versions
are not edited manually in this repository.

Usage:
  python tools/set_version.py 2.1.0

Updates metadata.version in every skills/*/SKILL.md and the plugin entries plus
metadata.version in .claude-plugin/marketplace.json. Claude Code only auto-updates
marketplace installs when the plugin `version` changes.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
VERSION_LINE = re.compile(r"^(  version:\s*)(\S+)\s*$", re.MULTILINE)


def write(path, text):
    path.write_bytes(text.encode("utf-8"))   # keep LF line endings on Windows


def main():
    if hasattr(sys.stdout, "reconfigure"):   # Windows consoles default to cp1252
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2 or not SEMVER.match(sys.argv[1]):
        sys.exit(__doc__)
    new = sys.argv[1]

    for md in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = md.read_text(encoding="utf-8")
        head, sep, body = text.partition("\n---")   # only touch the frontmatter
        head, n = VERSION_LINE.subn(rf"\g<1>{new}", head, count=1)
        if not n:
            sys.exit(f"{md}: no 'metadata:\\n  version:' line in frontmatter")
        write(md, head + sep + body)
        print(f"{md.relative_to(ROOT)}: {new}")

    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    data.setdefault("metadata", {})["version"] = new
    for plugin in data["plugins"]:
        plugin["version"] = new
    write(MARKETPLACE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{MARKETPLACE.relative_to(ROOT)}: {new}")


if __name__ == "__main__":
    main()
