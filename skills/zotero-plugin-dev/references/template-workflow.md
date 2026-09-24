# windingwind/zotero-plugin-template workflow

TypeScript scaffold using `zotero-plugin-scaffold` (build/serve/release/test),
`zotero-plugin-toolkit` (UI helpers) and `zotero-types` (typings for the Zotero codebase).

## Setup

```bash
# Use GitHub "Use this template", then:
git clone <your-repo> && cd <your-repo>
npm install
cp .env.example .env
```

`.env`:
- `ZOTERO_PLUGIN_ZOTERO_BIN_PATH` — Zotero binary (`…/Zotero.app/Contents/MacOS/zotero` on macOS)
- `ZOTERO_PLUGIN_PROFILE_PATH` — a dedicated dev profile (create with `zotero -p`)
- `ZOTERO_PLUGIN_DATA_DIR` — optional separate data dir (recommended)

Edit `package.json` → `config`: `addonName`, `addonID`, `addonRef` (namespace used for
chrome paths, FTL, prefs), `addonInstance` (global name on `Zotero`), `prefsPrefix`.

Check `addon/manifest.json` `strict_max_version` — the template may lag the current
Zotero major (it has shipped with `8.*`); raise it to what you test.

## Commands

- `npm start` — build, launch Zotero with the dev profile, hot-reload on change
- `npm run build` — production .xpi in `.scaffold/build` + `tsc --noEmit`
- `npm run release` — bump, tag, build, publish to GitHub Releases with update.json
- `npm test` — mocha/chai tests run inside Zotero
- `npm run lint:fix`

## Layout

- `addon/` — static files copied into the xpi: `bootstrap.js`, `manifest.json`,
  `prefs.js`, `locale/`, `content/` (xhtml, icons). Placeholders like `__addonRef__`
  are replaced at build time.
- `src/index.ts` — creates the addon instance, attaches it to `Zotero[addonInstance]`.
- `src/hooks.ts` — `onStartup`, `onMainWindowLoad`, `onMainWindowUnload`, `onShutdown`,
  `onNotify`, `onPrefsEvent`; this is where features are wired in.
- `src/modules/examples.ts` — examples of notifier, prefs, shortcuts, menus, columns,
  item-pane sections, reader hooks, dialogs, progress windows. Delete what you don't use.
- `src/utils/` — `ztoolkit`, locale helpers (`getString`), prefs wrappers.

## Notes

- The bootstrap loads the bundled script with `loadSubScript` into a sandbox `ctx`;
  put shared state on `addon.data`, not on bare globals.
- toolkit helpers are convenient, but for menus/columns/sections prefer calling the
  official Zotero managers directly when targeting 8+; the toolkit wraps some of them.
- FTL files in `addon/locale/*/` get prefixed with `addonRef` at build; use the
  generated `getString()` helper and reference IDs with the prefix convention the
  template enforces.
