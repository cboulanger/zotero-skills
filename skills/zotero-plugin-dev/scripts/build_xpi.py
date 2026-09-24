#!/usr/bin/env python3
"""Package a Zotero plugin directory as an .xpi and write a matching updates.json.

Usage:
  python build_xpi.py <plugin-dir> [--out build] [--update-link URL]
                      [--min 7.0] [--max 10.0.*]

manifest.json must be at the root of <plugin-dir>. The update_link defaults to a
placeholder; pass the real download URL of the xpi you will publish.
"""
import argparse, hashlib, json, pathlib, sys, zipfile

EXCLUDE = {".git", ".DS_Store", "node_modules", "build", "__pycache__"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plugin_dir")
    ap.add_argument("--out", default="build")
    ap.add_argument("--update-link")
    ap.add_argument("--min")
    ap.add_argument("--max")
    a = ap.parse_args()

    src = pathlib.Path(a.plugin_dir).resolve()
    manifest_path = src / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"error: {manifest_path} not found (manifest.json must be at the plugin root)")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    z = manifest.get("applications", {}).get("zotero")
    if not z or "id" not in z:
        sys.exit("error: manifest.json lacks applications.zotero.id — Zotero will refuse to install")
    if "update_url" not in z:
        print("warning: applications.zotero.update_url missing; some Zotero versions reject the install",
              file=sys.stderr)
    if not (src / "bootstrap.js").exists():
        print("warning: no bootstrap.js at plugin root", file=sys.stderr)

    pid, version = z["id"], manifest["version"]
    stem = pid.split("@")[0]
    out = pathlib.Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    xpi = out / f"{stem}-{version}.xpi"

    with zipfile.ZipFile(xpi, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(src.rglob("*")):
            rel = p.relative_to(src)
            if p.is_dir() or any(part in EXCLUDE for part in rel.parts):
                continue
            if out in p.parents:
                continue
            zf.write(p, rel.as_posix())

    digest = hashlib.sha256(xpi.read_bytes()).hexdigest()
    updates = {"addons": {pid: {"updates": [{
        "version": version,
        "update_link": a.update_link or f"https://example.org/REPLACE/{xpi.name}",
        "update_hash": f"sha256:{digest}",
        "applications": {"zotero": {
            "strict_min_version": a.min or z.get("strict_min_version", "7.0"),
            "strict_max_version": a.max or z.get("strict_max_version", "10.0.*"),
        }},
    }]}}}
    (out / "updates.json").write_text(json.dumps(updates, indent=2) + "\n", encoding="utf-8")
    print(f"built {xpi}\nsha256 {digest}\nwrote {out / 'updates.json'}")

if __name__ == "__main__":
    main()
