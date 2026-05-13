---
name: zotero-plugin-toolkit
description: API reference for zotero-plugin-toolkit (v5.x). Covers UITool element creation, KeyboardManager, PromptManager (command palette), DialogHelper, SettingsDialogHelper, ProgressWindowHelper, FilePickerHelper, ClipboardHelper, ReaderTool, ExtraFieldTool, FieldHookManager, PatchHelper, LargePrefHelper, VirtualizedTableHelper, and lifecycle/cleanup patterns. Use when implementing plugin UI, keyboard shortcuts, dialogs, progress indicators, or item field customization.
---

# zotero-plugin-toolkit API Reference

**Package**: `zotero-plugin-toolkit` (v5.x, supports Zotero 6/7/8)  
**Install**: `npm install zotero-plugin-toolkit`  
**Docs**: https://windingwind.github.io/zotero-plugin-toolkit/  
**Local source**: `/Users/cboulanger/Code/zotero-plugin-toolkit/src/`

## Import Styles

```typescript
// Full bundle (convenient, larger)
import { ZoteroToolkit } from "zotero-plugin-toolkit";
const ztoolkit = new ZoteroToolkit();

// Selective (recommended — smaller bundle)
import { UITool, KeyboardManager, DialogHelper } from "zotero-plugin-toolkit";
```

## BasicTool

Base class for all toolkit classes. Provides safe global access and logging.

```javascript
import { BasicTool } from "zotero-plugin-toolkit";
const tool = new BasicTool({ log: { prefix: "[MyPlugin]" } });

tool.getGlobal("Zotero")          // type-safe access to Zotero globals
tool.log("msg", someValue)        // logs to console.log + Zotero.debug with stack trace
tool.createXULElement(doc, "menuitem")  // Zotero 6/7/8 compatible XUL creation
```

## UITool — Element Creation

```javascript
import { UITool } from "zotero-plugin-toolkit";
const ui = new UITool();

const panel = ui.createElement(document, "vbox", {
  id: "my-panel",
  namespace: "xul",          // "html" (default) | "xul" | "svg"
  classList: ["panel"],
  styles: { padding: "8px" },
  attributes: { hidden: "false" },
  properties: { innerText: "Hello" },
  listeners: [{ type: "click", listener: (e) => doSomething(e) }],
  children: [
    { tag: "html:input", id: "my-input", attributes: { type: "text" } },
    { tag: "html:button", properties: { textContent: "Go" },
      listeners: [{ type: "click", listener: () => search() }] }
  ]
});
```

**Deduplication options** (add to props):
- `ignoreIfExists: true` — skip if element with same `id` already exists
- `removeIfExists: true` — remove existing element first, then recreate

**Insertion helpers**:

```javascript
ui.appendElement(props, container);
ui.insertElementBefore(props, referenceNode);
ui.replaceElement(props, oldNode);
```

**Cleanup** — all created elements are tracked automatically:

```javascript
ui.unregisterAll();  // removes all tracked elements from DOM
```

## KeyboardManager

```javascript
import { KeyboardManager, KeyModifier } from "zotero-plugin-toolkit";
const keyboard = new KeyboardManager();

keyboard.register((event, options) => {
  if (options.keyboard?.equals("accel,s")) { /* Cmd+S / Ctrl+S */ }
  if (options.keyboard?.equals("accel,shift,p")) openCommandPalette();
});

// KeyModifier helpers
const mod = new KeyModifier("accel,shift,s");
mod.accel; mod.shift; mod.key           // "s"
mod.getLocalized()                      // "⌘⇧S" (Mac) or "Ctrl+Shift+S"
mod.equals("accel,shift,s")             // true

keyboard.unregisterAll();
```

## PromptManager — Command Palette

Adds a fuzzy-searchable command palette (default trigger: Shift+P).

```javascript
import { PromptManager } from "zotero-plugin-toolkit";
const prompt = new PromptManager();

prompt.register([
  {
    name: "Export selected items",
    label: "MyPlugin",
    id: "myplugin-export",
    when: () => ZoteroPane.getSelectedItems().length > 0,
    callback: async (promptInstance) => { await exportItems(); }
  }
]);

prompt.unregister("myplugin-export");
prompt.unregisterAll();
```

Return an array of `Command` from `callback` to show a nested sub-menu.

## DialogHelper — Modal Dialogs

Grid-based dialog builder (rows × columns):

```javascript
import { DialogHelper } from "zotero-plugin-toolkit";

const dialog = new DialogHelper(3, 2);  // 3 rows, 2 columns
const data = {};

dialog
  .addCell(0, 0, { tag: "html:label", properties: { innerText: "Name:" } })
  .addCell(0, 1, { tag: "html:input", id: "name-input", attributes: { type: "text" } })
  .addButton("Cancel", "cancel")
  .addButton("OK", "ok", {
    callback: () => {
      processInput(dialog.window.document.getElementById("name-input").value);
    }
  })
  .setDialogData({
    ...data,
    loadCallback: () => { /* set initial values */ },
    unloadCallback: () => { /* read final values */ }
  })
  .open("Export Settings", { width: 400, height: 300, centerscreen: true, resizable: true });

// Check which button was clicked after dialog closes:
await data.unloadLock?.promise;
if (data._lastButtonId === "ok") { /* ... */ }
```

## SettingsDialogHelper — Preference Dialogs

Extends `DialogHelper` with automatic pref binding:

```javascript
import { SettingsDialogHelper } from "zotero-plugin-toolkit";

new SettingsDialogHelper(5, 2)
  .setSettingHandlers(
    (key) => Zotero.Prefs.get(`myplugin.${key}`, true),
    (key, value) => Zotero.Prefs.set(`myplugin.${key}`, value, true)
  )
  .addSetting("Enable feature", "featureEnabled", {
    tag: "html:input", attributes: { type: "checkbox" }
  })
  .addSetting("API URL", "apiUrl", {
    tag: "html:input", attributes: { type: "text" }
  })
  .addSetting("Max results", "maxResults", {
    tag: "html:input", attributes: { type: "number", min: "1", max: "100" }
  }, { valueType: "number" })
  .addButton("Save", "save")
  .open("Plugin Settings", { width: 500, height: 400 });
```

## ProgressWindowHelper

```javascript
import { ProgressWindowHelper } from "zotero-plugin-toolkit";

const win = new ProgressWindowHelper("Importing items", {
  closeOnClick: true,
  closeTime: 3000   // auto-close after 3s
});
const line = win.createLine({ type: "default", text: "Starting...", progress: 0 });
win.show();

win.changeLine({ text: "Processing 5/10...", progress: 50 });
win.changeLine({ type: "success", text: "Done!", progress: 100 });
```

`type` values: `"success"` (green check), `"fail"` (red X), or a custom icon key.

## FilePickerHelper

```javascript
import { FilePickerHelper } from "zotero-plugin-toolkit";

const path = await new FilePickerHelper(
  "Select PDF", "open",
  [["PDF Files", "*.pdf"], ["All Files", "*.*"]]
).open();
if (path !== false) processFile(path);

// Save file
const savePath = await new FilePickerHelper(
  "Export as CSV", "save", [["CSV", "*.csv"]], "export.csv"
).open();

// Folder picker
const folder = await new FilePickerHelper("Select folder", "folder").open();

// Multiple files → string[]
const paths = await new FilePickerHelper("Select files", "multiple").open();
```

## ClipboardHelper

```javascript
import { ClipboardHelper } from "zotero-plugin-toolkit";

new ClipboardHelper()
  .addText("Plain text", "text/unicode")
  .addText("<b>Bold</b>", "text/html")
  .copy();

new ClipboardHelper().addImage("data:image/png;base64,...").copy();
new ClipboardHelper().addFile("/path/to/file.pdf").copy();
```

## ReaderTool — PDF/EPUB Reader

```javascript
import { ReaderTool } from "zotero-plugin-toolkit";
const reader = new ReaderTool();

const instance = await reader.getReader(5000);   // waits up to 5s
const annotation = reader.getSelectedAnnotationData(instance);
// → { text, color, pageLabel, position, sortIndex, type }
const text = reader.getSelectedText(instance);
const windows = reader.getWindowReader();        // all open reader windows
```

## ExtraFieldTool — item.extra Fields

```javascript
import { ExtraFieldTool } from "zotero-plugin-toolkit";
const extraField = new ExtraFieldTool();

const fields = extraField.getExtraFields(item);  // → Map<string, string[]>
const doi = extraField.getExtraField(item, "DOI");           // first value or undefined
const dois = extraField.getExtraField(item, "DOI", true);    // string[]

await extraField.setExtraField(item, "myKey", "myValue");    // replace
await extraField.setExtraField(item, "tag", "new", { append: true });  // append

const newFields = new Map([["DOI", ["10.1234/foo"]]]);
await extraField.replaceExtraFields(item, newFields);
```

## FieldHookManager — Virtual Item Fields

Override how Zotero reads/writes item fields:

```javascript
import { FieldHookManager } from "zotero-plugin-toolkit";
const hooks = new FieldHookManager();

hooks.register("getField", "myVirtualField",
  (field, unformatted, includeBaseMapped, item, original) => {
    return item.itemType === "journalArticle"
      ? computeVirtualValue(item)
      : original.apply(item, [field, unformatted, includeBaseMapped]);
  }
);

hooks.register("isFieldOfBase", "myVirtualField",
  (field, baseField, original) => baseField === "title" || original(field, baseField)
);

hooks.unregisterAll();
```

## PatchHelper — Monkey-Patching

```javascript
import { PatchHelper } from "zotero-plugin-toolkit";

const patch = new PatchHelper();
patch.setData({
  target: Zotero.Items,
  funcSign: "merge",
  patcher: (original) => async function(item, otherItems, ...args) {
    Zotero.log("merge called");
    return original.apply(this, [item, otherItems, ...args]);
  },
  enabled: true
});

patch.enable();
patch.disable();   // restores original
```

## LargePrefHelper — Big Data in Prefs

```javascript
import { LargePrefHelper } from "zotero-plugin-toolkit";

const store = new LargePrefHelper(
  "myplugin.dataKeys",   // pref storing the list of sub-keys
  "myplugin.data.",      // prefix for value prefs
  "default"              // hook preset: auto JSON parse/stringify
);

const obj = store.asObject();   // Proxy — use like a plain object
obj.myKey = { list: [1, 2, 3] };
console.log(obj.myKey.list);    // [1, 2, 3]

const map = store.asMapLike();  // Map-like interface
map.set("foo", "bar");
```

## VirtualizedTableHelper — Large Tables

For thousands of rows with efficient windowed rendering.

```javascript
import { VirtualizedTableHelper } from "zotero-plugin-toolkit";

const table = new VirtualizedTableHelper(window)
  .setProp("id", "my-table")
  .setProp("getRowCount", () => items.length)
  .setProp("getRowData", (i) => ({ title: items[i].title, year: String(items[i].year) }))
  .setProp("columns", [
    { dataKey: "title", label: "Title", flex: 2 },
    { dataKey: "year",  label: "Year",  fixedWidth: true, width: 48 }
  ])
  .setProp("multiSelect", true)
  .setProp("onSelectionChange", (selection) => {
    console.log("selected:", [...selection.selected]);
  })
  .setContainerId("my-table-container");   // must exist in DOM

table.render();

// Refresh rows after state change:
table.treeInstance.invalidateRow(index);
table.treeInstance.invalidate();           // repaint all
```

### Required stylesheets (dialog windows)

Without these, cells stack vertically instead of rendering as flex rows:

```xml
<?xml-stylesheet href="chrome://zotero-platform/content/zotero-react-client.css" type="text/css"?>
<?xml-stylesheet href="chrome://zotero-platform/content/zotero.css" type="text/css"?>
```

Add before `<!DOCTYPE html>` in your `.xhtml`.

### Container CSS

The container must have a definite pixel height for windowed rendering to work:

```css
.dialog-container {
  display: flex; flex-direction: column; height: 100%;
  padding: 12px 12px 0; box-sizing: border-box;
}
#table-container {
  flex: 1; min-height: 0;
  overflow: auto;         /* NOT hidden — needed for scrollbar */
  border: 1px solid #ccc; border-radius: 4px;
}
#table-container .virtualized-table-header {
  position: sticky; top: 0; z-index: 1;
}
```

### Checkboxes — independent `selected` Set

VirtualizedTable has no built-in checkbox selection. Keep a separate `Set` of selected indices:

```javascript
this.selected = new Set();

// In column definition:
{
  dataKey: "checked", label: "", fixedWidth: true, width: 32,
  renderer: (index, _data, column) => {
    const span = document.createElement("span");
    span.className = `cell ${column.className}`;
    span.style.cssText = "display:flex;align-items:center;justify-content:center;";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = this.selected.has(index);
    cb.addEventListener("change", () => {
      if (cb.checked) this.selected.add(index);
      else this.selected.delete(index);
      this.updateButtons();
      // do NOT call invalidateRow here
    });
    span.appendChild(cb);
    return span;
  }
}

// Leave onSelectionChange as no-op — NEVER call clearSelection() inside it
.setProp("onSelectionChange", () => {})
```

**Known limitation**: the first click on an unselected row moves the native cursor AND fires the checkbox change; subsequent clicks on the same row only fire the checkbox change. This means unchecking a pre-checked row that isn't the current cursor row requires two clicks.

### Custom cell rendering

Use `column.renderer` rather than a global `renderItem` override. Return a `<span>`, not a `<div>`:

```javascript
renderer: (index, _data, column) => {
  const span = document.createElement("span");
  span.className = `cell ${column.className}`;  // column.className auto-set by VirtualizedTable
  span.textContent = myData[index].label;
  return span;
}
```

## Utility: waitUntil / waitUntilAsync

```javascript
import { waitUntil, waitUntilAsync, waitForReader } from "zotero-plugin-toolkit";

waitUntil(
  () => document.getElementById("my-el") !== null,
  () => initElement(),
  100,   // poll interval ms
  5000   // timeout ms
);

await waitUntilAsync(() => Zotero.Schema.schemaUpdatePromise.resolved, 200, 10000);
await waitForReader(readerInstance);
```

## Lifecycle & Cleanup

Managers auto-unregister on plugin unload when the plugin ID is in scope. In your `shutdown()`:

```javascript
ztoolkit.unregisterAll();   // full bundle
// or:
keyboard.unregisterAll();
prompt.unregisterAll();
ui.unregisterAll();
```

## Cross-Version Compatibility

The toolkit handles these automatically — always prefer toolkit methods over raw API calls:

| Feature | Zotero 6 | Zotero 7+ |
|---|---|---|
| XUL element creation | `createElementNS(xulNS, tag)` | `createXULElement(tag)` |
| Module import | `ChromeUtils.import()` | `ChromeUtils.importESModule()` |

## Related Skills

- See [zotero-plugin-basics](../zotero-plugin-basics/SKILL.md) for plugin scaffolding and setup.
- See [zotero-plugin-dialogs](../zotero-plugin-dialogs/SKILL.md) for XHTML dialog structure and script loading.
- See [zotero-api](../zotero-api/SKILL.md) for the Zotero data API (items, attachments, sync, etc.).
