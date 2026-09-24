# Version-specific changes and migration checklist

Read the section(s) for every version between the oldest and newest the plugin supports.

## Zotero 6 → 7 (Firefox 60 → 115) — the big rewrite

- `install.rdf` → `manifest.json` with `applications.zotero` (required).
- `update.rdf` → JSON `updates.json` (Mozilla format). Serve the JSON from the old RDF
  URL too so existing users aren't stranded.
- XUL overlays → `bootstrap.js` with lifecycle + window hooks; all DOM from JS.
- `chrome.manifest` → runtime `registerChrome` only if `chrome://` URLs are required.
- `defaults/preferences/*.js` → `prefs.js` in plugin root.
- `.dtd`/`.properties` → Fluent `.ftl` under `locale/<locale>/`.
- `.xul` → `.xhtml`; `createElement` → `createXULElement` for XUL; XBL gone (custom elements).
- `OS.File`/`OS.Path` → `IOUtils`/`PathUtils`.
- XUL box layout → CSS flexbox (`-moz-box-flex` → `flex`); no `width`/`height` attrs on XUL.
- `.jsm` → `.sys.mjs` via `ChromeUtils.importESModule`.
- `Zotero.platform`/`oscpu` removed → `Zotero.isWin/isMac/isLinux`, `Zotero.arch`.
- `DB.executeTransaction()` takes async functions, not generators.
- Item pane redesign: use `ItemPaneManager`, not DOM injection; columns via `ItemTreeManager`.

## Zotero 7 → 8 (Firefox 115 → 140)

- Remove manual `Services.jsm` imports (Services is global).
- All JSMs → ESMs; global imports gone — assign imports to variables; ESMs are strict.
- **Bluebird removed**: no `.map/.filter/.each/.isPending/.cancel` on promises,
  `Zotero.spawn()` removed; `Zotero.Promise.delay/defer` still exist (`defer()` not as
  constructor). Zotero ships `migrate-fx140/migrate.py` (`esmify`, `asyncify`) to
  convert code automatically.
- `XPCOMUtils.defineLazyGetter` → `ChromeUtils.defineLazyGetter`.
- `nsIScriptableUnicodeConverter`, `nsIOSFileConstantsService`, `nsIDOMChromeWindow` removed.
- `DataTransfer#types.contains` → `.includes`.
- `ZOTERO_CONFIG` must be imported. `hiddenDOMWindow` gone outside macOS.
- Pref-pane scripts get their own global scope.
- Button labels: set `.label` property, not attribute.
- New: `Zotero.MenuManager`.

## Zotero 8 → 9

No major developer-facing changes. Test, then bump `strict_max_version` to `9.0.*`
(can be done in `updates.json` alone).

## Zotero 9 → 10 (same Firefox 140 base)

- **Multi-selection in collections pane**: singular getters now *throw*.
  `getSelectedCollection()` → `getSelectedCollections()`, `getSelectedLibraryID()` →
  `getSelectedLibraryIDs()`, `getCollectionTreeRow()` → `getCollectionTreeRows()`,
  `getSelectedSavedSearch()` → `getSelectedSavedSearches()`; groups: filter rows by
  `isGroup()`. Collections and searches can be selected together.
- `ItemTree#collectionTreeRow` gone → `itemsView.viewMode` (`'default'`, `'trash'`,
  `'duplicates'`, `'unfiled'`, `'feed'`…) or `itemsView.collectionTreeRows`.
- Items list may contain library header/spacer rows: check `row.isObjectRow`
  (`getSortedItems()` already filters).
- MenuManager contexts: `collectionTreeRow` throws → `collectionTreeRows`.
- Search: condition groups (`groupStart`/`groupEnd`, `joinMode`, `resultLevel`);
  `addCondition` with legacy `required` throws; `fulltextWord` removed → `fulltextContent`.
- Advanced Search window removed (now in main window).
- Full-text rewritten on FTS5; `fulltextWords` tables dropped; various `Zotero.FullText`
  methods changed.
- Undo/redo: `item.saveTx({ undoAction, undoActionArgs })` or
  `Zotero.UndoHistory.stageAction()` inside a transaction; labels come from `Zotero.ftl`.
- Local HTTP server (23119) hardening: Host must be localhost; browser-like requests need
  `Zotero-Allowed-Request` header; custom endpoints can set
  `allowRequestsFromUnsafeWebContent = true`. Local `/api/` supports writes with
  `Zotero-Server-ID`.
- `setType()` to/from attachment/note/annotation throws; attachment paths with slashes throw.
- SQLite WAL mode; `Zotero.DB.loadExtension()`, `onIdle()`, `addCorruptionHandler()`.
- `ItemTree` split (`ItemTreeRow`, `CollectionViewItemTree`); some methods moved.
- `Zotero.CookieSandbox` → `Zotero.HTTP.newCookieContext()`.
- `Zotero.HTTP.download()` returns a `Response`.
- FTL registration consolidated with per-locale fallback.
- Plugin `prefs.js` reloads on update without restart.
- Beta/source builds ignore `strict_max_version`; stable enforces it.

## Porting procedure

1. Grep for removed APIs listed above (`Services.jsm`, `getSelectedCollection(`,
   `.isPending(`, `Zotero.spawn`, `OS.File`, `collectionTreeRow`, `install.rdf`, `.xul`).
2. Fix, then test on the oldest and newest supported Zotero in separate profiles.
3. Run the disable/enable and window close/reopen cycle.
4. Bump `strict_max_version` and `version`, rebuild, update `updates.json`.
