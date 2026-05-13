---
name: zotero-plugin-basics
description: Scaffold, structure, build, and load a Zotero 7+ plugin using zotero-plugin-scaffold. Use when creating a new Zotero plugin, setting up the build toolchain, understanding the plugin lifecycle, or loading a plugin into a running Zotero instance for development.
---

# Zotero Plugin Development with zotero-plugin-scaffold

This skill covers creating a Zotero 7+ plugin from scratch using [zotero-plugin-scaffold](https://github.com/windingwind/zotero-plugin-scaffold) as the build tool.

## Scaffolding a New Plugin

The fastest start is cloning the official starter template:

```bash
git clone https://github.com/windingwind/zotero-plugin-template my-plugin
cd my-plugin
npm install
```

Alternatively, add `zotero-plugin-scaffold` to an existing project:

```bash
npm install --save-dev zotero-plugin-scaffold zotero-types
```

Then create `zotero-plugin.config.js` (or `.ts`) at the project root (see Configuration below).

## Plugin File Structure

```
my-plugin/
├── zotero-plugin.config.js   # scaffold build config
├── package.json
├── src/                      # TypeScript/JS source (compiled by scaffold)
│   ├── index.ts              # main entry point (exports bootstrap hooks)
│   ├── modules/              # feature modules
│   └── utils/                # helpers
├── addon/                    # static plugin assets (copied as-is)
│   ├── manifest.json         # plugin metadata (required)
│   ├── bootstrap.js          # Zotero-facing entry point (required)
│   ├── chrome/
│   │   └── content/          # XUL/XHTML UI files
│   ├── locale/               # Fluent (.ftl) strings
│   │   └── en-US/
│   └── prefs/
│       └── defaults.js       # default preference values
└── dist/                     # built XPI output
```

For simpler plugins (no TypeScript build step), `bootstrap.js` and the JS source can live directly under `addon/` and `plugin/src/` respectively, using `Services.scriptloader.loadSubScript()` to load files at startup.

## manifest.json

Required metadata file at the plugin root:

```json
{
  "manifest_version": 2,
  "name": "My Plugin",
  "version": "0.1.0",
  "description": "What this plugin does",
  "author": "Your Name",
  "homepage_url": "https://github.com/you/my-plugin",
  "applications": {
    "zotero": {
      "id": "my-plugin@yourdomain.com",
      "update_url": "https://raw.githubusercontent.com/you/my-plugin/main/updates.json",
      "strict_min_version": "7.0",
      "strict_max_version": "9.*"
    }
  }
}
```

- The `id` must be unique and follow the `name@domain` convention.
- `strict_min_version: "7.0"` targets Zotero 7+ (Firefox 115 ESR engine).

## bootstrap.js — Plugin Lifecycle

Zotero 7 plugins are bootstrapped (no `install.rdf`, no restartless shim). The `bootstrap.js` file must export these functions:

```javascript
var MyPlugin;
var chromeHandle;

function install() { /* first install only */ }

async function startup({ id, version, rootURI }) {
  // Register chrome:// protocol so your files are accessible
  const aomStartup = Components.classes[
    "@mozilla.org/addons/addon-manager-startup;1"
  ].getService(Components.interfaces.amIAddonManagerStartup);
  const manifestURI = Services.io.newURI(rootURI + "manifest.json");
  chromeHandle = aomStartup.registerChrome(manifestURI, [
    ["content", "my-plugin", rootURI]
  ]);

  // Load your compiled JS bundle
  Services.scriptloader.loadSubScript(rootURI + "my-plugin.js");

  // Register preference pane (optional)
  Zotero.PreferencePanes.register({
    pluginID: id,
    src: rootURI + "prefs.xhtml",
    scripts: [rootURI + "prefs.js"],   // loaded in the pref pane context
    image: rootURI + "icons/icon.svg"
  });

  MyPlugin.init({ id, version, rootURI });
  MyPlugin.addToAllWindows();
  await MyPlugin.main();
}

function onMainWindowLoad({ window }) {
  MyPlugin?.addToWindow(window);
}

function onMainWindowUnload({ window }) {
  MyPlugin?.removeFromWindow(window);
}

function shutdown() {
  MyPlugin?.removeFromAllWindows();
  MyPlugin = undefined;

  if (chromeHandle) {
    chromeHandle.destruct();
    chromeHandle = null;
  }
}

function uninstall() { /* cleanup on removal */ }
```

**Lifecycle order:** `install` (once) → `startup` (every Zotero start) → `onMainWindowLoad` (per window) → `onMainWindowUnload` (per window) → `shutdown` (Zotero quit or plugin disable).

## zotero-plugin.config.js

Scaffold configuration at the project root:

```javascript
import { defineConfig } from "zotero-plugin-scaffold";

export default defineConfig({
  name: "My Plugin",
  id: "my-plugin@yourdomain.com",
  namespace: "myPlugin",           // global var name used in bootstrap.js
  source: ["src"],                 // TS/JS source dirs to compile
  build: {
    assets: ["addon/**/*.*"]       // static files to copy into the build
  },
  fluent: {
    dts: "typings/i18n.d.ts"       // generated type file for .ftl strings
  },
  server: {
    prefs: {
      "extensions.zotero.httpServer.port": 23119,
      "extensions.zotero-plugin.dev-mode": true
    }
  }
});
```

## npm scripts

Add to `package.json`:

```json
{
  "scripts": {
    "build": "zotero-plugin build",
    "serve": "zotero-plugin serve",
    "release": "zotero-plugin release"
  }
}
```

| Command | What it does |
|---------|-------------|
| `npm run build` | Compiles TS, copies assets, packages `dist/*.xpi` |
| `npm run serve` | Watches source, rebuilds on change, hot-reloads in Zotero via HTTP server |
| `npm run release` | Builds and bumps version for distribution |

## Loading the Plugin in Zotero

**For development (recommended):**

1. Run `npm run serve` — scaffold starts a local server and hot-reloads changes.
2. On first use, point Zotero at your plugin: Tools → Developer → Load Plugin From Manifest → select `addon/manifest.json`.

**To install a built XPI:**

1. Run `npm run build`.
2. In Zotero: Tools → Add-ons → gear icon → Install Add-on From File → select `dist/my-plugin-0.1.0.xpi`.

**Via MCP tools (Claude Code with zotero-dev MCP):**

```
zotero_scaffold_serve   — start the dev server / hot-reload
zotero_scaffold_build   — build the XPI
zotero_plugin_reload    — force-reload a loaded plugin by ID
zotero_execute_js       — run JS in Zotero's context to test API calls
```

## Using zotero-plugin-toolkit

[zotero-plugin-toolkit](https://github.com/windingwind/zotero-plugin-toolkit) provides typed wrappers for common Zotero operations. Install it:

```bash
npm install zotero-plugin-toolkit
```

Import in your source:

```typescript
import { ZoteroToolkit } from "zotero-plugin-toolkit";
const ztoolkit = new ZoteroToolkit();
```

It covers UI helpers, preference management, keyboard shortcuts, progress windows, and more. Prefer it over raw Zotero API calls where possible.

## TypeScript Setup

Add `zotero-types` for full Zotero API type coverage:

```bash
npm install --save-dev zotero-types
```

In `tsconfig.json`:

```json
{
  "compilerOptions": {
    "types": ["zotero-types"]
  }
}
```

This exposes `Zotero`, `ZoteroItem`, `ZoteroCollection`, etc. as global types.

## Common Pitfalls

- **`rootURI` always ends with `/`** — don't double-slash when concatenating paths.
- **Chrome registration must happen in `startup`**, not `onMainWindowLoad`.
- **`Zotero` global is available in `startup` but not before** — don't call Zotero API at module load time.
- **Preferences** must be registered in `startup` via `Zotero.PreferencePanes.register()`, not via `defaults.js` alone in Zotero 7.
- **XUL is largely replaced by HTML** in Zotero 7 — prefer `.xhtml` and standard DOM APIs over XUL elements.

## Logging

In a Zotero plugin, `console.log()` is **silent** in chrome context — use `Services.console` instead. See the full logging setup (including dialog scripts and hot-reload safety) in [zotero-api](../zotero-api/SKILL.md#logging).

Quick version for `bootstrap.js`:

```javascript
function log(msg) {
  Services.console.logStringMessage("My Plugin: " + msg);
}
```

View output in **Tools → Developer → Browser Console** (`Cmd+Shift+J` on macOS).

## Related Skills

- See [zotero-plugin-dialogs](../zotero-plugin-dialogs/SKILL.md) for dialogs, menus, and the preferences pane format.
- See [zotero-api](../zotero-api/SKILL.md) for the Zotero data API (items, attachments, sync, logging, notifier, etc.).
- See [zotero-plugin-toolkit](../zotero-plugin-toolkit/SKILL.md) for higher-level UI helpers (DialogHelper, UITool, ProgressWindowHelper, etc.).
- See [saved-search](../saved-search/SKILL.md) for creating and querying saved searches via the Zotero API.
