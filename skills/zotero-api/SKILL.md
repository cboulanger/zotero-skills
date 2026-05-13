---
name: zotero-api
description: Reference for Zotero's JavaScript API — items, attachments, relations, sync, HTTP, database, notifier, pane, libraries, and utilities. Use when implementing plugin features that access or manipulate Zotero data, respond to library events, or make network requests. Many of these APIs are undocumented or hard to find.
---

# Zotero JavaScript API Reference

Zotero's internal API runs in a privileged chrome JavaScript context. All of the following is available from `bootstrap.js`, scripts loaded via `loadSubScript`, and dialog scripts after loading `chrome://zotero/content/include.js`.

## Logging

In a chrome context, `console.log()` is **silent** — nothing appears anywhere. Use `Services.console` instead.

### In bootstrap.js

`console` is not defined here at all:

```javascript
function log(msg) {
  Services.console.logStringMessage("My Plugin: " + msg);
}
```

### In window/dialog scripts

`console` exists but its methods are no-ops. Patch them at the top of every dialog script (wrap in an IIFE to avoid `const` redeclaration errors on hot-reload):

```javascript
;(function() {
  const makeLogger = (level) => (...args) => {
    const msg = "[My Plugin] " + args.join(" ");
    if (level === "log" || level === "info") {
      Services.console.logStringMessage(msg);
    } else {
      const e = Cc["@mozilla.org/scripterror;1"].createInstance(Ci.nsIScriptError);
      const flags = { warn: 0x1, error: 0x0 };
      e.init(msg, "", null, 0, 0, flags[level], "chrome javascript");
      Services.console.logMessage(e);
    }
  };
  ["log", "info", "warn", "error"].forEach(level => { console[level] = makeLogger(level); });
})();
```

For scripts loaded via `loadSubScript` where `console` may not exist at all:

```javascript
;(function() {
  const makeLogger = (level) => (...args) => {
    const msg = "[My Plugin] " + args.join(" ");
    if (level === "log" || level === "info") {
      Services.console.logStringMessage(msg);
    } else {
      const e = Cc["@mozilla.org/scripterror;1"].createInstance(Ci.nsIScriptError);
      const flags = { warn: 0x1, error: 0x0 };
      e.init(msg, "", null, 0, 0, flags[level], "chrome javascript");
      Services.console.logMessage(e);
    }
  };
  if (typeof console === "undefined") {
    globalThis.console = { log: makeLogger("log"), info: makeLogger("info"), warn: makeLogger("warn"), error: makeLogger("error") };
  } else {
    ["log", "info", "warn", "error"].forEach(level => { console[level] = makeLogger(level); });
  }
})();
```

### Where to view output

**Tools → Developer → Browser Console** (`Cmd+Shift+J` on macOS). This is the Parent Process Browser Console that shows chrome-context output.

| `nsIScriptError` flag | Value | Display |
|---|---|---|
| `errorFlag` | `0x0` | Red (error) |
| `warningFlag` | `0x1` | Yellow (warning) |
| `infoFlag` | `0x8` | Renders as error in practice — use `logStringMessage` for neutral output |

## Libraries

```javascript
Zotero.Libraries.userLibraryID                   // numeric ID of personal library (always present)
Zotero.Libraries.get(libraryID)                  // synchronous
Zotero.Libraries.get(libraryID).libraryVersion   // sync version (0 if never synced); increases on item add/modify

const groups = Zotero.Groups.getAll();
groups[0].libraryID                              // convert group → numeric library ID
groups[0].name

const pane = Zotero.getActiveZoteroPane();
pane.getSelectedLibraryID()
```

## Items

```javascript
// Check whether an attachment's local file exists
await item.fileExists()                          // Promise<boolean>

// Get full local file path (null if not downloaded)
await item.getFilePathAsync()                    // Promise<string|null>

// Attachment properties
item.attachmentFilename                          // filename only, e.g. "paper.pdf"
item.attachmentSyncedHash                        // MD5 hex; only set by Zotero File Storage, NOT WebDAV
item.attachmentContentType                       // MIME type, e.g. "application/pdf"
item.parentItemID                                // numeric ID of parent, or false/null for top-level
item.libraryID
item.key                                         // 8-char alphanumeric Zotero key
item.id                                          // numeric database ID
item.deleted                                     // true if in trash

// Creators — returns raw DB objects, not typed strings
item.getCreators()
// → Array<{creatorTypeID: number, firstName: string, lastName: string, name: string, fieldMode: number}>
// NOTE: no .creatorType string — use creatorTypeID or don't filter by type

// Relations
item.getRelations()                              // → Record<predicate, string|string[]>
item.getRelationsByPredicate(predicate)          // → string[] of URIs

// Attachment IDs on a regular item
item.getAttachments()                            // → number[] of attachment itemIDs
```

## Relations

```javascript
Zotero.Relations.linkedObjectPredicate           // 'owl:sameAs'
Zotero.Relations.replacedItemPredicate           // 'dc:replaces' URI

// Resolve a Zotero URI to an item (works cross-library)
await Zotero.URI.getURIItem(uri)                 // → Zotero.Item | null
```

## Attachments

```javascript
// Storage directory for an attachment (nsIFile)
const dir = Zotero.Attachments.getStorageDirectory(attachmentItem)
// dir.path → absolute path string

// Find available PDF/file resolvers
const resolvers = Zotero.Attachments.getFileResolvers(parentItem, methods, automatic)
// methods defaults to ['doi', 'url', 'oa', 'custom']

const { title, mimeType, url } =
  await Zotero.Attachments.downloadFirstAvailableFile(resolvers, tmpFilePath, options)
// options: { enforceFileType, onAccessMethodStart, onBeforeRequest, onRequestError }
// Throws on failure; url=null if nothing found

// High-level: find & attach — creates a new attachment item
// NOTE: returns false silently if the item already has a PDF/EPUB attachment
const newAtt = await Zotero.Attachments.addAvailableFile(item, { methods })
// → Zotero.Item | false

Zotero.Attachments.canFindFileForItem(item)      // → boolean (false if PDF/EPUB already exists)
Zotero.Attachments.FIND_AVAILABLE_FILE_TYPES     // ['application/pdf', 'application/epub+zip']

const { path: tmpDir } = await Zotero.Attachments.createTemporaryStorageDirectory()
```

## Sync

```javascript
// Check whether file sync is configured for a library
Zotero.Sync.Storage.Local.getEnabledForLibrary(libraryID)  // → boolean
// Returns false for libraries that only sync metadata (no WebDAV / Zotero Storage)

// Trigger a file download
await Zotero.Sync.Runner.downloadFile(attachmentItem)
// Check fileExists() afterwards; throws on network error
```

## HTTP

Prefer `Zotero.HTTP.request` over `fetch()` — it honours Zotero proxy settings, cookies, and authentication:

```javascript
const req = await Zotero.HTTP.request("GET", url, {
  responseType: "blob",        // "blob" | "arraybuffer" | "text" | "json"
  followRedirects: false,      // optional
  errorDelayMax: 0,            // optional; set to 0 to throw immediately on non-2xx
})
// req.status, req.response, req.getResponseHeader(name)
// Throws Zotero.HTTP.UnexpectedStatusException on non-2xx when errorDelayMax !== 0
```

## Database

```javascript
// Direct SQL query — returns array of first-column values
const ids = await Zotero.DB.columnQueryAsync(sql, [param1, param2])

// itemAttachments columns of interest:
//   itemID       — FK to items.itemID
//   linkMode     — 0=imported_file, 1=imported_url, 2=linked_file, 3=linked_url
//   path         — "storage:<filename>" for imported attachments (linkMode 0/1)
//   storageHash  — MD5 hex; only populated by Zotero File Storage, NULL for WebDAV
//   contentType  — MIME type string
```

## Notifier

```javascript
const id = Zotero.Notifier.registerObserver(
  { notify(event, type, ids, extraData) { /* ... */ } },
  ["item", "collection"]  // event types: 'item', 'collection', 'library', 'search', ...
)
Zotero.Notifier.unregisterObserver(id)
```

**Important details:**
- Permanent item deletion: `event="delete"`, `type="item"`. `extraData[id]` contains `{ libraryID, key }` even after the item is gone from the DB.
- Trashing an item does **not** fire `"delete"` — only permanent erasure (empty trash / `erase()`) does.

## Pane & Window

```javascript
const pane = Zotero.getActiveZoteroPane()
pane.getSelectedLibraryID()
await pane.selectItem(itemID)             // focus item in list, expanding parent if needed

// Focus an already-open dialog (windowtype must be set on the document element)
Services.wm.getMostRecentWindow("windowtype-string")   // → Window | null

// Inside a dialog opened via openDialog():
window.arguments[0]    // args object passed as last arg to openDialog()
window.opener          // the window that called openDialog()
window.closed          // boolean — true after window.close()
```

## Saved Searches

See [saved-search](../saved-search/SKILL.md) for the full `Zotero.Search` API.

## Utilities & Globals

```javascript
// Temporary directory
Zotero.getTempDirectory().path           // absolute path string

// Cross-platform path helpers
PathUtils.join(a, b, ...)
PathUtils.filename(path)                 // basename

// File I/O
await IOUtils.copy(srcPath, destPath)
await IOUtils.makeDirectory(path, { createAncestors: true, ignoreExisting: true })
await IOUtils.write(path, uint8Array)
await IOUtils.remove(path, { recursive: true })
```

## References

- [Zotero 7 for Developers](https://www.zotero.org/support/dev/zotero_7_for_developers)
- [Zotero 8 for Developers](https://www.zotero.org/support/dev/zotero_8_for_developers)
- [Zotero Web API v3 Syncing](https://www.zotero.org/support/dev/web_api/v3/syncing)

## Related Skills

- See [zotero-plugin-basics](../zotero-plugin-basics/SKILL.md) for plugin scaffolding and bootstrap.js.
- See [zotero-plugin-dialogs](../zotero-plugin-dialogs/SKILL.md) for dialogs and menus.
- See [saved-search](../saved-search/SKILL.md) for `Zotero.Search` API.
