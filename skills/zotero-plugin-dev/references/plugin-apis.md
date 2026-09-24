# Zotero plugin API reference

Examples follow the official Zotero 7/8/10 developer pages. Authoritative option lists
live in github.com/zotero/zotero under `chrome/content/zotero/xpcom/pluginAPI/`.

Contents: Menus · Item tree columns · Item pane sections · Info rows · Reader ·
Preference panes · Prefs · Notifier · Chrome registration · Data API cheatsheet

---

## Menus — `Zotero.MenuManager` (Zotero 8+)

```js
const menuID = Zotero.MenuManager.registerMenu({
  menuID: "my-plugin-item-menu",
  pluginID: "my-plugin@example.org",
  target: "main/library/item",
  menus: [
    {
      menuType: "menuitem",
      l10nID: "my-plugin-menu-export",
      onShowing: (event, context) => {
        context.setVisible(context.items?.every((i) => i.isRegularItem()));
      },
      onCommand: (event, context) => { MyPlugin.exportItems(context.items); },
    },
    { menuType: "submenu", l10nID: "my-plugin-menu-more", menus: [ /* … */ ] },
  ],
});
// Zotero.MenuManager.unregisterMenu(menuID);  // automatic on shutdown
```

FTL entry must set `.label`:
```
my-plugin-menu-export =
    .label = Export…
```

Targets: `main/menubar/{file,edit,view,go,tools,help}`, `main/library/item`,
`main/library/collection`, `main/library/addAttachment`, `main/library/addNote`,
`main/tab`, `reader/menubar/{file,edit,view,go,window}`, `itemPane/info/row`,
`notesPane/addItemNote`, `notesPane/addStandaloneNote`, `sidenav/locate`.

Zotero 10: in `main/library/*` contexts, `context.collectionTreeRow` throws — use
`context.collectionTreeRows` (array).

Zotero 7 fallback (no MenuManager): create elements with `doc.createXULElement('menuitem')`
in `onMainWindowLoad`, append to e.g. `doc.getElementById('zotero-itemmenu')` or
`'menu_ToolsPopup'`, give them prefixed IDs, and remove them in shutdown. Feature-detect
with `if (Zotero.MenuManager)`.

## Item tree columns — `Zotero.ItemTreeManager`

```js
const key = await Zotero.ItemTreeManager.registerColumn({
  dataKey: "my-plugin-wordcount",    // required
  label: "Words",                    // required
  pluginID: "my-plugin@example.org", // required
  dataProvider: (item, dataKey) => String(MyPlugin.cache.get(item.id) ?? ""),
});
// await Zotero.ItemTreeManager.unregisterColumn(key);
```

`dataProvider` is synchronous and runs per visible row on every render. Precompute and
cache; refresh the tree after async work.

## Item pane sections — `Zotero.ItemPaneManager.registerSection`

```js
const sectionID = Zotero.ItemPaneManager.registerSection({
  paneID: "my-plugin-section",
  pluginID: "my-plugin@example.org",
  header:  { l10nID: "my-plugin-section-header", icon: rootURI + "icons/16.svg" },
  sidenav: { l10nID: "my-plugin-section-header", icon: rootURI + "icons/20.svg" },
  onRender: ({ body, item, editable, tabType }) => {
    body.textContent = item ? item.getField("title") : "";
  },
  // see itemPaneManager.js for onInit, onDestroy, onItemChange, onAsyncRender, sectionButtons
});
```

Do fast synchronous work in `onRender` and fetches in the async render hook; don't inject
into the item pane DOM manually.

## Info rows — `Zotero.ItemPaneManager.registerInfoRow`

```js
Zotero.ItemPaneManager.registerInfoRow({
  rowID: "my-plugin-row",
  pluginID: "my-plugin@example.org",
  label: { l10nID: "my-plugin-row-label" },
  position: "afterCreators",
  multiline: false, nowrap: false, editable: true,
  onGetData: ({ rowID, item, tabType, editable }) => item.getField("extra"),
  onSetData: ({ rowID, item, tabType, editable, value }) => { /* persist */ },
});
```

## Reader — `Zotero.Reader.registerEventListener(type, handler, pluginID)`

Inject-DOM events: `renderTextSelectionPopup`, `renderSidebarAnnotationHeader`,
`renderToolbar`. Context-menu events: `createColorContextMenu`, `createViewContextMenu`,
`createAnnotationContextMenu`, `createThumbnailContextMenu`, `createSelectorContextMenu`.

```js
Zotero.Reader.registerEventListener("renderTextSelectionPopup", (event) => {
  const { reader, doc, params, append } = event;
  const div = doc.createElement("div");
  div.textContent = params.annotation.text;
  append(div);
}, "my-plugin@example.org");

Zotero.Reader.registerEventListener("createAnnotationContextMenu", (event) => {
  const { reader, params, append } = event;
  append({ label: "Copy IDs", onCommand() { /* params.ids */ } });
}, "my-plugin@example.org");
```

Create elements with the provided `doc` (the reader's document), not the main window's.

## Preference panes — `Zotero.PreferencePanes.register`

```js
Zotero.PreferencePanes.register({
  pluginID: "my-plugin@example.org",
  src: rootURI + "preferences.xhtml",
  scripts: [rootURI + "preferences.js"],
  stylesheets: [rootURI + "preferences.css"],
});
```

`preferences.xhtml` is a fragment — no `<!DOCTYPE>`, XUL default namespace, HTML under
`html:`. Top-level `<groupbox>`es make the pane work well with preference search.

```xml
<linkset><html:link rel="localization" href="my-plugin.ftl"/></linkset>
<vbox id="my-plugin-prefs">
  <groupbox>
    <label><html:h2 data-l10n-id="my-plugin-prefs-title"/></label>
    <html:input type="text" preference="extensions.my-plugin.apiURL"/>
  </groupbox>
</vbox>
```

Bind with `preference="<full pref key>"` (no `<preference>` elements). Namespace every
`id`, `class` and `data-l10n-id`. Zotero 8+: each pane script runs in its own global
scope — set things on `window` explicitly to share them.

## Prefs

`prefs.js` in the plugin root: `pref("extensions.my-plugin.apiURL", "https://…");`

```js
Zotero.Prefs.get("extensions.my-plugin.apiURL", true);   // true = global key
Zotero.Prefs.set("extensions.my-plugin.apiURL", v, true);
// without `true`, the key is relative to "extensions.zotero."
```

## Notifier — observe library changes (manual cleanup required)

```js
const observerID = Zotero.Notifier.registerObserver({
  notify: async (event, type, ids, extraData) => {
    // event: add | modify | delete | trash | …; type: item | collection | tag | …
    if (type === "item" && event === "add") { /* ids: array of item IDs */ }
  },
}, ["item"], "my-plugin");
// in shutdown:
Zotero.Notifier.unregisterObserver(observerID);
```

Keep `notify` quick, and guard against loops if the handler itself saves items (your own
save fires another `modify`). Trashing fires `trash`, not `delete`; see `data-api.md`.

## Chrome registration (only if needed)

Needed for `chrome://` URLs (module imports, dialogs opened by chrome URL, .dtd/.properties):

```js
const aomStartup = Cc["@mozilla.org/addons/addon-manager-startup;1"]
  .getService(Ci.amIAddonManagerStartup);
chromeHandle = aomStartup.registerChrome(
  Services.io.newURI(rootURI + "manifest.json"),
  [["content", "my-plugin", rootURI + "content/"]]);
// shutdown: chromeHandle.destruct(); chromeHandle = null;
```

## Data API cheatsheet

For attachments, saved searches, relations, sync, HTTP, DB and files see `data-api.md`.

```js
const pane = Zotero.getActiveZoteroPane();
pane.getSelectedItems();                 // Zotero.Item[]
pane.getSelectedCollections();           // plural getters (required on Zotero 10)
Zotero.Libraries.userLibraryID;

await Zotero.Items.getAsync(id);
Zotero.Items.getByLibraryAndKey(libraryID, key);
item.itemType; item.isRegularItem(); item.getCreators(); item.getTags();
item.getField("date"); item.setField("extra", "…"); item.addTag("x");
await item.saveTx();                     // Zotero 10: saveTx({ undoAction, undoActionArgs })

const s = new Zotero.Search();
s.libraryID = Zotero.Libraries.userLibraryID;
s.addCondition("title", "contains", "law");
const ids = await s.search();

const note = new Zotero.Item("note");
note.libraryID = item.libraryID; note.parentID = item.id;
note.setNote("<p>…</p>"); await note.saveTx();

await Zotero.DB.executeTransaction(async () => {
  for (const it of items) { it.addTag("done"); await it.save(); }
});

await Zotero.HTTP.request("GET", url, { responseType: "json" });
await Zotero.File.getContentsAsync(path);   // IOUtils / PathUtils for other file work
```

Dialogs: `Services.prompt.alert(win, title, msg)`; progress: `new Zotero.ProgressWindow()`.
File picker: `const { FilePicker } = ChromeUtils.importESModule('chrome://zotero/content/modules/filePicker.mjs');`
