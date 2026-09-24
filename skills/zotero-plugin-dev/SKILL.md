---
name: zotero-plugin-dev
description: Build, port, debug, and package Zotero desktop plugins (extensions/add-ons, .xpi) for Zotero 7, 8, 9 and 10. Covers the bootstrapped architecture (manifest.json + bootstrap.js), lifecycle and window hooks, the official plugin APIs (MenuManager, ItemTreeManager, ItemPaneManager, PreferencePanes, Reader event listeners, Notifier), Fluent localization, prefs, dialogs, the Zotero JS data API (items, attachments, saved searches), update manifests, and version migrations. Use this skill whenever the user wants to write, scaffold, extend, fix, or update a Zotero plugin, port an old Zotero 6 overlay plugin, make a plugin compatible with a newer Zotero release, add a menu item/column/item-pane section/dialog to Zotero, or asks about zotero-plugin-template, zotero-plugin-toolkit, zotero-types or make-it-red — even if they just say "Zotero extension" or "Zotero add-on". Not for using a Zotero library via MCP/web API or for writing Zotero translators or CSL styles.
license: CC0-1.0
metadata:
  version: 1.0.0
---

# Zotero plugin development

Zotero plugins are privileged, bootstrapped Mozilla add-ons: they run with full chrome
access (XPCOM, file system, the whole `Zotero` object) and can be enabled, disabled and
upgraded without a restart. That combination is where most bugs come from — a plugin
that works on first install but leaks UI, listeners or memory when it is disabled,
upgraded or when the main window is reopened. Much of this skill is about keeping
startup and teardown symmetrical.

Model knowledge of Zotero plugins is often stale (Zotero 6 overlays, `install.rdf`,
`chrome.manifest`, `Services.jsm` imports, Bluebird, single-collection selection). Trust
this skill and the official "Zotero N for Developers" pages over recall.

## 0. Establish the target first

Before writing code, pin down:

- **Zotero versions to support.** Current stable is 10 (Firefox 140 ESR base, same as 9).
  Zotero 8 moved to Firefox 140 and ESM-only; Zotero 10 changed selection, search,
  full-text and local-API behavior. Read `references/version-changes.md` whenever the
  plugin must run on more than one major version or is being ported.
- **Scaffold.** Two sensible paths:
  - *Plain JS, no build step* — copy `assets/minimal-plugin/` (modeled on the official
    Make It Red 2.0 sample). Best for small plugins, bridges, or when the user wants to
    understand every line.
  - *TypeScript + hot reload* — windingwind's `zotero-plugin-template` with
    `zotero-plugin-scaffold`, `zotero-plugin-toolkit` and `zotero-types`. Best for
    anything with real UI or ongoing development. See `references/template-workflow.md`.
  If the user already has a repo, follow its structure; don't migrate scaffolds unasked.
- **Plugin ID** (`name@domain`), a short namespace prefix (used for element IDs, Fluent
  IDs, pref keys, CSS classes), and the pref branch (`extensions.<namespace>.*` or
  `extensions.zotero.<namespace>.*`).

## 1. Anatomy

```
my-plugin/
├── manifest.json      # WebExtension-style metadata; applications.zotero is mandatory
├── bootstrap.js       # lifecycle + window hooks
├── prefs.js           # default prefs, plugin root (NOT defaults/preferences/)
├── my-plugin.js       # main code, loaded via Services.scriptloader.loadSubScript
├── preferences.xhtml  # optional pref-pane fragment (no DOCTYPE, XUL default ns)
├── style.css
└── locale/en-US/my-plugin.ftl   # Fluent; auto-registered, no chrome.manifest needed
```

An .xpi is a zip with `manifest.json` at the archive root — zip the *contents*, not the
folder. `scripts/build_xpi.py` does this and writes `updates.json` with the sha256.

### manifest.json

```json
{
  "manifest_version": 2,
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "…",
  "applications": {
    "zotero": {
      "id": "my-plugin@example.org",
      "update_url": "https://example.org/my-plugin/updates.json",
      "strict_min_version": "7.0",
      "strict_max_version": "10.0.*"
    }
  }
}
```

Set `strict_max_version` to the newest minor you have actually tested (`x.y.*`). Later
compatibility bumps can be made in `updates.json` alone, without a new release. Stable
builds enforce it; beta/source builds of Zotero 10 do not, so a plugin that installs on
beta can still be rejected on stable. Always include `update_url` — installs have been
reported to fail with a misleading "not compatible" error without it.

## 2. Lifecycle — the contract

`bootstrap.js` exports (as plain top-level functions):

| Hook | Called | Do here |
|---|---|---|
| `install(data, reason)` | first install / upgrade | usually nothing |
| `startup({id, version, rootURI}, reason)` | enable, app start, upgrade | load code, register APIs (menus, columns, sections, pref pane, notifier), then add to existing windows |
| `onMainWindowLoad({window})` | each main window opens | inject window DOM: FTL link, stylesheet, toolbar buttons, shortcuts |
| `onMainWindowUnload({window})` | each main window closes | drop references to that window, clear its timers/listeners |
| `shutdown(data, reason)` | disable, uninstall, upgrade, app quit | undo everything from `startup` and remove your DOM from all open windows |
| `uninstall(data, reason)` | removal | optional pref/data cleanup |

Key facts:
- `Zotero`, `Services`, `Cc`, `Ci`, `ChromeUtils`, `URL`, etc. are already in scope
  (Zotero ≥ 7). Don't import `Services.jsm` — that throws on Zotero 8+.
- `rootURI` ends in `/`; build file URLs as `rootURI + 'file.js'` (no extra slash).
- `startup` runs *after* Zotero is initialized, but the main window may or may not
  already be open. So `startup` must call your "add to window" routine for every
  window in `Zotero.getMainWindows()`, and `onMainWindowLoad` covers windows opened later.
- In `shutdown`, `if (reason === APP_SHUTDOWN) return;` is a common, safe shortcut —
  the process is exiting anyway.
- DOM you inject is destroyed with its window, but on *disable* the windows stay open,
  so `shutdown` must remove it from every window. Give every injected element an ID with
  your prefix and track them (Make It Red's `storeAddedElement` pattern).
- Objects registered through the official managers (`MenuManager`, `ItemTreeManager`,
  `ItemPaneManager`, `Reader.registerEventListener`) are removed automatically by
  `pluginID` when the plugin shuts down. Everything else — `Zotero.Notifier` observers,
  `chromeHandle` from `registerChrome`, timers, `Zotero.ftl.addResourceIds`, event
  listeners on long-lived objects, globals you set on `Zotero` — you must undo yourself.

When writing or reviewing a plugin, walk the teardown checklist explicitly: for every
`register*`, `add*`, `set*`, `setInterval`, `addEventListener` and global assignment in
startup/window-load code, point to the line that reverses it.

## 3. Prefer the official APIs to DOM injection

Menus, item-tree columns, item-pane sections and info rows, reader popups/context menus
and preference panes all have first-class APIs; use them before hand-rolling DOM, since
they survive Zotero UI refactors and clean up after themselves. Signatures and examples
are in `references/plugin-apis.md` — read it before implementing any UI.

- Menus → `Zotero.MenuManager.registerMenu` (Zotero 8+). On Zotero 7 you need DOM
  injection in `onMainWindowLoad`; if supporting 7 and 8+, feature-detect
  `Zotero.MenuManager`.
- Columns → `Zotero.ItemTreeManager.registerColumn`
- Item pane → `Zotero.ItemPaneManager.registerSection` / `registerInfoRow`
- Reader → `Zotero.Reader.registerEventListener`
- Prefs → `Zotero.PreferencePanes.register` + `prefs.js` + `preference="…"` binding
- Data changes → `Zotero.Notifier.registerObserver`

For things without an official API:

- Dialogs and secondary windows (XHTML dialogs, `openDialog`, passing arguments,
  finding an open dialog) → `references/dialogs.md`.
- zotero-plugin-toolkit helpers (DialogHelper, SettingsDialogHelper, KeyboardManager,
  PromptManager, ProgressWindowHelper, FilePickerHelper, VirtualizedTableHelper,
  ExtraFieldTool, PatchHelper …) → `references/toolkit.md`. Use them when the project
  already depends on the toolkit (e.g. the template); don't add the dependency to a
  plain-JS plugin just for one helper.

## 4. Localization (Fluent)

- `.ftl` files under `locale/<locale>/` are registered automatically.
- Fluent **IDs share a global namespace per document** and **filenames share a global
  namespace** — prefix every ID (`my-plugin-menu-export`) and name the file after the
  plugin (or use a subfolder).
- Add to an existing window with `window.MozXULElement.insertFTLIfNeeded("my-plugin.ftl")`
  *before* inserting localized DOM; remove the `<link>` in teardown.
- Use `data-l10n-id` / `document.l10n.setAttributes()`; for strings outside the DOM,
  `await document.l10n.formatValue(id, args)` or a `new Localization(["my-plugin.ftl"])`.
- MenuManager and similar APIs take an `l10nID`; the FTL entry must set `.label`.
- Undo labels (Zotero 10) resolve via `Zotero.ftl`, so register with
  `Zotero.ftl.addResourceIds(['my-plugin.ftl'])` and remove on shutdown.

## 5. Working with library data

Common calls below; `references/data-api.md` covers attachments and file resolvers,
saved searches (`Zotero.Search`, incl. Zotero 10 changes), relations, sync, HTTP,
`Zotero.DB`, file I/O and notifier edge cases.

```js
const items = Zotero.getActiveZoteroPane().getSelectedItems();
const item = await Zotero.Items.getAsync(id);          // or Zotero.Items.getByLibraryAndKey
item.getField('title'); item.setField('extra', '…');
await item.saveTx();                                    // Zotero 10: saveTx({ undoAction, undoActionArgs })
await Zotero.DB.executeTransaction(async () => { … await item.save(); });  // batch
```

- Always `await` saves; use `saveTx()` outside a transaction, `save()` inside one.
  Transactions take async functions (no generators, no Bluebird).
- Zotero 10: never assume a single selected collection/library — use the plural
  getters (`getSelectedCollections()`, `getSelectedLibraryIDs()`, …).
- Check `item.isRegularItem()` / `isNote()` / `isAttachment()` / `isAnnotation()`
  before field access; notes and attachments have different field sets.
- Respect `library.editable`/`item.library.editable` before writing (group libraries).
- Don't read `zotero.sqlite` directly from outside Zotero; from inside, use `Zotero.DB`.

## 6. Dev loop and debugging

- Use a **separate profile and data directory** for development (`zotero -P` to create
  one). Plugins have unrestricted access; a bug can damage a real library.
- Load an unpacked plugin: in the dev profile's `extensions/` folder, create a text file
  named with the plugin ID whose only content is the absolute path to the source folder;
  delete `extensions.lastAppBuildId` and `extensions.lastAppVersion` lines from the
  profile's `prefs.js`, then start Zotero with `-purgecaches`. The template's
  `npm start` automates this plus hot reload.
- Start with `-ZoteroDebugText -jsdebugger` for debug output on stdout and the Browser
  Toolbox. Log with `Zotero.debug("MyPlugin: …")`; view via Help → Debug Output Logging.
- `console` is unreliable in chrome scopes: it is undefined in `bootstrap.js` and may be a
  no-op in dialog windows. To see messages in Tools → Developer → Browser Console, use
  `Services.console.logStringMessage("MyPlugin: …")`, or for warnings/errors an
  `nsIScriptError`:

  ```js
  function logError(msg, isWarning = false) {
    const e = Cc["@mozilla.org/scripterror;1"].createInstance(Ci.nsIScriptError);
    e.init("MyPlugin: " + msg, "", null, 0, 0, isWarning ? 0x1 : 0x0, "chrome javascript");
    Services.console.logMessage(e);
  }
  ```

  In dialog scripts, wrap such a shim in an IIFE so reloading the script doesn't hit
  `const` redeclaration errors.
- Tools → Developer → Run JavaScript lets you prototype API calls live — suggest it for
  checking an assumption before building around it. If a Zotero-dev MCP server is
  connected (tools like `zotero_execute_js`, `zotero_plugin_reload`,
  `zotero_scaffold_serve`), use it to run code, reload the plugin and build instead of
  asking the user to do it by hand.
- Test the *second* cycle: disable → re-enable, and close → reopen the main window.
  Duplicate menu items or lingering columns mean teardown is incomplete.

## 7. Packaging and updates

Run `python scripts/build_xpi.py <plugin-dir> --update-link <url-of-xpi>`; it zips the
plugin, and writes `updates.json` with the correct `update_hash`. Host `updates.json`
at the manifest's `update_url` (GitHub Releases is typical). Keep `version` in
manifest.json and updates.json in sync; the hash must match the exact uploaded file.

## 8. When unsure

The source is the documentation for the plugin APIs:
`chrome/content/zotero/xpcom/pluginAPI/*.js` and `xpcom/preferencePanes.js` in
github.com/zotero/zotero. The dev list (zotero-dev on Google Groups) is where API
questions go. Tell the user when you are inferring from source rather than docs.
