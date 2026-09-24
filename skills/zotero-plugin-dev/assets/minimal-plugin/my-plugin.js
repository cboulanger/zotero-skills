MyPlugin = {
  id: null,
  version: null,
  rootURI: null,
  addedElementIDs: [],
  notifierID: null,

  init({ id, version, rootURI }) {
    this.id = id;
    this.version = version;
    this.rootURI = rootURI;
  },

  log(msg) {
    Zotero.debug("MyPlugin: " + msg);
  },

  // ---- things registered once per app session -------------------------
  registerGlobal() {
    // Official managers clean up by pluginID automatically.
    if (Zotero.MenuManager) {
      Zotero.MenuManager.registerMenu({
        menuID: "my-plugin-item-menu",
        pluginID: this.id,
        target: "main/library/item",
        menus: [{
          menuType: "menuitem",
          l10nID: "my-plugin-menu-hello",
          onCommand: (event, context) => this.hello(context.items || []),
        }],
      });
    }

    // Notifier observers do NOT clean up automatically.
    this.notifierID = Zotero.Notifier.registerObserver({
      notify: (event, type, ids) => this.log(`${event} ${type} ${ids.join(",")}`),
    }, ["item"], "my-plugin");
  },

  unregisterGlobal() {
    if (this.notifierID) {
      Zotero.Notifier.unregisterObserver(this.notifierID);
      this.notifierID = null;
    }
  },

  // ---- things added to each main window -------------------------------
  addToWindow(window) {
    const doc = window.document;
    window.MozXULElement.insertFTLIfNeeded("my-plugin.ftl");

    const link = doc.createElement("link");
    link.id = "my-plugin-stylesheet";
    link.rel = "stylesheet";
    link.href = this.rootURI + "style.css";
    doc.documentElement.appendChild(link);
    this.trackElement(link);
  },

  addToAllWindows() {
    for (const win of Zotero.getMainWindows()) {
      if (win.ZoteroPane) this.addToWindow(win);
    }
  },

  removeFromWindow(window) {
    const doc = window.document;
    for (const id of this.addedElementIDs) doc.getElementById(id)?.remove();
    doc.querySelector('[href="my-plugin.ftl"]')?.remove();
  },

  removeFromAllWindows() {
    for (const win of Zotero.getMainWindows()) {
      if (win.ZoteroPane) this.removeFromWindow(win);
    }
  },

  trackElement(elem) {
    if (!elem.id) throw new Error("Injected elements need a prefixed id");
    if (!this.addedElementIDs.includes(elem.id)) this.addedElementIDs.push(elem.id);
  },

  // ---- features --------------------------------------------------------
  hello(items) {
    const greeting = Zotero.Prefs.get("extensions.my-plugin.greeting", true);
    const titles = items.filter((i) => i.isRegularItem()).map((i) => i.getField("title"));
    Services.prompt.alert(null, "My Plugin", `${greeting}\n\n${titles.join("\n")}`);
  },
};
