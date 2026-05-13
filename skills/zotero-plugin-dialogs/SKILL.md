---
name: zotero-plugin-dialogs
description: Create dialogs, menus, and preference panes in a Zotero 7+ plugin. Covers XHTML dialog structure, script loading, opening dialogs with window.openDialog(), chrome vs. rootURI URL patterns, dialog script patterns, XUL menu injection, and the preferences pane format. Use when adding UI to a Zotero plugin.
---

# Dialogs, Menus, and Preferences in Zotero Plugins

## XHTML Dialog Structure

Zotero 7 dialogs are XHTML documents (not XUL). Use standard HTML elements for content — XUL is needed only for menus.

```xml
<?xml version="1.0"?>
<?xml-stylesheet href="chrome://global/skin/" type="text/css"?>
<?xml-stylesheet href="chrome://zotero/skin/zotero.css" type="text/css"?>
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"
      xmlns:xul="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">
<head>
  <title>Dialog Title</title>
  <meta charset="utf-8"/>
  <script>
    document.addEventListener("DOMContentLoaded", () => {
      Services.scriptloader.loadSubScript(
        "chrome://zotero/content/include.js", this
      );
      Services.scriptloader.loadSubScript(
        "chrome://my-plugin/content/dialog.js", window
      );
    });
  </script>
  <link rel="stylesheet" href="dialog.css"/>
</head>
<body>
  <input type="text" id="query-input"/>
  <button id="submit-btn">Submit</button>
  <textarea id="results" readonly></textarea>
</body>
</html>
```

- Use `<input>`, `<button>`, `<textarea>`, `<label>`, `<select>` — not XUL equivalents.
- Load scripts via `Services.scriptloader.loadSubScript()` (not `<script src="">`).
- `chrome://zotero/content/include.js` bootstraps Zotero globals (`Zotero`, `Services`, `Components`, etc.) in the dialog scope.

## Loading Scripts in Dialogs

Dialogs do **not** inherit the main window's globals. Always load dependencies explicitly:

```javascript
Services.scriptloader.loadSubScript(
  "chrome://my-plugin/content/script.js",
  window   // target scope
);
```

If using `zotero-plugin-toolkit`, load the bundle too:

```javascript
Services.scriptloader.loadSubScript(
  "chrome://my-plugin/content/toolkit.bundle.js",
  window
);
```

## Opening Dialogs

### Method 1 — chrome:// URL (requires chrome registration)

```javascript
window.openDialog(
  "chrome://my-plugin/content/dialog.xhtml",
  "my-plugin-dialog",
  "chrome,centerscreen,modal,resizable=yes,width=600,height=500",
  { plugin: this }   // passed as window.arguments[0]
);
```

### Method 2 — rootURI (no chrome registration needed)

```javascript
window.openDialog(
  this.rootURI + "dialog.xhtml",
  "my-plugin-dialog",
  "chrome,centerscreen,modal,resizable=yes,width=600,height=500",
  { plugin: this }
);
```

Method 2 works without registering the chrome protocol but uses `file://` URLs internally. Method 1 is preferred for plugins that register chrome (which most do — see [zotero-plugin-basics](../zotero-plugin-basics/SKILL.md)).

## Dialog Script Pattern

```javascript
var MyDialog = {
  plugin: null,

  init() {
    if (window.arguments?.[0]) {
      this.plugin = window.arguments[0].plugin;
    }
    document.getElementById("submit-btn").addEventListener("click", () => {
      this.submit();
    });
  },

  async submit() {
    const query = document.getElementById("query-input").value;
    // do work...
  }
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => MyDialog.init());
} else {
  MyDialog.init();
}
```

Key points:
- Access passed arguments via `window.arguments[0]`.
- Access the opening window via `window.opener`.
- Focus an already-open dialog: `Services.wm.getMostRecentWindow("windowtype-string")` — the `windowtype` must be set as an attribute on the root document element, not as the `name` argument to `openDialog`.

## Streaming Responses (SSE)

```javascript
const url = `http://localhost:8000/stream?q=${encodeURIComponent(query)}`;
this.eventSource = new EventSource(url);

this.eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // update UI with data
};

this.eventSource.onerror = () => {
  this.eventSource.close();
  this.eventSource = null;
};

// cleanup in shutdown:
cleanup() {
  this.eventSource?.close();
  this.eventSource = null;
}
```

## Menu Items

Menus must use XUL elements — there is no HTML alternative here:

```javascript
addToWindow(window) {
  const doc = window.document;

  const menuitem = doc.createXULElement("menuitem");
  menuitem.id = "my-plugin-menu-item";
  menuitem.setAttribute("label", "My Plugin Action");
  menuitem.addEventListener("command", () => this.handleCommand(window));

  const toolsMenu = doc.getElementById("menu_ToolsPopup");
  toolsMenu?.appendChild(menuitem);
}

removeFromWindow(window) {
  window.document.getElementById("my-plugin-menu-item")?.remove();
}
```

**Note:** Zotero 8 introduces a new official API for menu items — prefer it over manual XUL injection when available. See the [Zotero 8 developer docs](https://www.zotero.org/support/dev/zotero_8_for_developers).

## Preference Pane

Preference panes are **HTML fragments** (not full documents) injected into Zotero's preferences window. Register them in `startup()`:

```javascript
Zotero.PreferencePanes.register({
  pluginID: "my-plugin@example.com",
  src: rootURI + "preferences.xhtml",
  scripts: [rootURI + "preferences.js"],  // optional: loaded in pref pane context
  image: rootURI + "icons/icon.svg"
});
```

The `preferences.xhtml` is a fragment (no `<html>` wrapper):

```xml
<linkset>
  <html:link rel="stylesheet" href="chrome://global/skin/"
             xmlns:html="http://www.w3.org/1999/xhtml"/>
</linkset>

<html:div xmlns:html="http://www.w3.org/1999/xhtml">
  <html:fieldset>
    <html:legend>Settings</html:legend>
    <html:label>API URL
      <html:input id="pref-api-url" type="text"/>
    </html:label>
  </html:fieldset>
</html:div>
```

Use `Zotero.Prefs.get("myplugin.apiUrl", true)` and `Zotero.Prefs.set(...)` in `preferences.js` to read/write prefs.

## Related Skills

- See [zotero-plugin-basics](../zotero-plugin-basics/SKILL.md) for plugin scaffolding, bootstrap.js, and chrome registration.
- See [zotero-plugin-toolkit](../zotero-plugin-toolkit/SKILL.md) for `DialogHelper`, `SettingsDialogHelper`, `UITool`, and `VirtualizedTableHelper` — higher-level alternatives to hand-rolling dialogs.
