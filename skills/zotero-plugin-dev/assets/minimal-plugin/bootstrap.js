/* Lifecycle glue only; feature code lives in my-plugin.js. */
var MyPlugin;

function install(data, reason) {}

async function startup({ id, version, rootURI }, reason) {
  Services.scriptloader.loadSubScript(rootURI + "my-plugin.js");
  MyPlugin.init({ id, version, rootURI });

  Zotero.PreferencePanes.register({
    pluginID: id,
    src: rootURI + "preferences.xhtml",
  });

  MyPlugin.registerGlobal();      // menus, columns, notifier, …
  MyPlugin.addToAllWindows();     // windows already open at enable time
}

function onMainWindowLoad({ window }) {
  MyPlugin?.addToWindow(window);
}

function onMainWindowUnload({ window }) {
  MyPlugin?.removeFromWindow(window);
}

function shutdown(data, reason) {
  if (reason === APP_SHUTDOWN) return;
  MyPlugin?.removeFromAllWindows();
  MyPlugin?.unregisterGlobal();
  MyPlugin = undefined;
}

function uninstall(data, reason) {}
