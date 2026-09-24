# Dialogs and secondary windows

For simple prompts, `Services.prompt.alert/confirm/prompt(win, title, msg)` is enough.
For builder-style dialogs without writing XHTML, see `DialogHelper` in `toolkit.md`.
Menus and preference panes are covered in `plugin-apis.md`.

Contents: XHTML dialog structure · Loading scripts · Opening dialogs · Dialog script
pattern · Finding an open dialog · Streaming responses · Cleanup

## XHTML dialog structure

Zotero 7+ dialogs are XHTML documents. Use HTML elements for content; XUL is only needed
for things like menus.

```xml
<?xml version="1.0"?>
<?xml-stylesheet href="chrome://global/skin/" type="text/css"?>
<?xml-stylesheet href="chrome://zotero/skin/zotero.css" type="text/css"?>
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"
      xmlns:xul="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul"
      windowtype="my-plugin:dialog">
<head>
  <title>Dialog Title</title>
  <meta charset="utf-8"/>
  <link rel="localization" href="my-plugin.ftl"/>
  <script>
    document.addEventListener("DOMContentLoaded", () => {
      Services.scriptloader.loadSubScript("chrome://zotero/content/include.js", this);
      Services.scriptloader.loadSubScript("chrome://my-plugin/content/dialog.js", window);
    });
  </script>
  <link rel="stylesheet" href="dialog.css"/>
</head>
<body>
  <input type="text" id="my-plugin-query"/>
  <button id="my-plugin-submit" data-l10n-id="my-plugin-dialog-submit"/>
  <textarea id="my-plugin-results" readonly="readonly"></textarea>
</body>
</html>
```

- Use `<input>`, `<button>`, `<textarea>`, `<label>`, `<select>`, not XUL equivalents.
- `chrome://zotero/content/include.js` brings `Zotero` and friends into the dialog scope.
- For a `VirtualizedTable` in a dialog, add the extra stylesheets listed in `toolkit.md`.

## Loading scripts

Dialogs do **not** inherit the main window's globals. Load every dependency explicitly
into the dialog's `window`:

```js
Services.scriptloader.loadSubScript("chrome://my-plugin/content/dialog.js", window);
// if you use zotero-plugin-toolkit in the dialog, load its bundle the same way
```

## Opening dialogs

```js
// chrome:// URL — needs chrome registration (see plugin-apis.md)
window.openDialog(
  "chrome://my-plugin/content/dialog.xhtml",
  "my-plugin-dialog",
  "chrome,centerscreen,resizable=yes,width=600,height=500",   // add ",modal" to block
  { plugin: MyPlugin }                                          // → window.arguments[0]
);

// rootURI — no chrome registration, but relative resources resolve against a
// jar:/file: URL, and chrome-only features (e.g. relative chrome:// includes) won't work
window.openDialog(MyPlugin.rootURI + "dialog.xhtml", "my-plugin-dialog",
  "chrome,centerscreen,resizable=yes", { plugin: MyPlugin });
```

Prefer the `chrome://` form once you register chrome anyway. With `modal`, `openDialog`
blocks until the dialog closes, so results can be read back from the args object.

## Dialog script pattern

```js
var MyDialog = {
  plugin: null,

  init() {
    this.plugin = window.arguments?.[0]?.plugin ?? null;
    document.getElementById("my-plugin-submit")
      .addEventListener("click", () => this.submit());
  },

  async submit() {
    const query = document.getElementById("my-plugin-query").value;
    // … do work, then e.g. window.arguments[0].result = …; window.close();
  },
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => MyDialog.init());
} else {
  MyDialog.init();
}
```

- `window.arguments[0]` — the last argument passed to `openDialog()`.
- `window.opener` — the window that opened the dialog.
- `window.closed` — `true` after `window.close()`; check it before touching a dialog you
  hold a reference to.

## Finding an already-open dialog

```js
const existing = Services.wm.getMostRecentWindow("my-plugin:dialog");
if (existing) { existing.focus(); return; }
```

The lookup key is the `windowtype` **attribute on the root element** of the dialog
document, not the `name` argument passed to `openDialog()`.

## Streaming responses (SSE)

`EventSource` is available in dialog windows, e.g. for a local backend:

```js
this.eventSource = new EventSource(`http://localhost:8000/stream?q=${encodeURIComponent(query)}`);
this.eventSource.onmessage = (event) => { const data = JSON.parse(event.data); /* update UI */ };
this.eventSource.onerror = () => { this.eventSource.close(); this.eventSource = null; };
```

Close the stream on `unload` and when the plugin shuts down.

## Cleanup

Open dialogs survive plugin disable. In `shutdown`, close your own windows:

```js
for (const win of Services.wm.getEnumerator("my-plugin:dialog")) win.close();
```
