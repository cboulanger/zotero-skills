# Zotero data API — items, attachments, searches, sync, HTTP, DB, files

Everything here runs in Zotero's privileged chrome context: `bootstrap.js`, scripts loaded
with `loadSubScript`, and dialog scripts after `chrome://zotero/content/include.js`. Many
of these APIs are undocumented; the source in github.com/zotero/zotero
(`chrome/content/zotero/xpcom/`) is authoritative. Check behavior in
Tools → Developer → Run JavaScript before building on it.

Contents: Libraries · Selection & pane · Items · Creators · Relations · Attachments ·
Saved searches · Notifier semantics · Sync · HTTP · Database · Files & paths

## Libraries

```js
Zotero.Libraries.userLibraryID                    // personal library (always present)
Zotero.Libraries.get(libraryID)                   // sync
Zotero.Libraries.get(libraryID).libraryVersion    // sync version; 0 if never synced
Zotero.Libraries.get(libraryID).editable          // check before writing (group libraries)

for (const g of Zotero.Groups.getAll()) { g.libraryID; g.name; }
```

## Selection & pane

```js
const pane = Zotero.getActiveZoteroPane();
pane.getSelectedItems();                // Zotero.Item[]
pane.getSelectedLibraryIDs();           // Zotero 10: plural — singular getters throw
pane.getSelectedCollections();
await pane.selectItem(itemID);          // focus item, expanding its parent if needed
```

On Zotero 7–9 only the singular getters (`getSelectedLibraryID()`,
`getSelectedCollection()`) exist; feature-detect if you support both ranges.

## Items

```js
const item = await Zotero.Items.getAsync(id);
Zotero.Items.getByLibraryAndKey(libraryID, key);
item.id; item.key; item.libraryID;              // numeric DB id, 8-char key
item.deleted;                                   // true if in trash
item.parentItemID;                              // false/null for top-level items
item.isRegularItem(); item.isNote(); item.isAttachment(); item.isAnnotation();
item.getAttachments();                          // number[] of attachment item IDs
item.getField("title"); item.setField("extra", "…"); await item.saveTx();
```

## Creators

```js
item.getCreators();
// → [{ creatorTypeID, firstName, lastName, fieldMode }, …]
// No creatorType string — map with Zotero.CreatorTypes.getName(creatorTypeID)
item.getCreatorsJSON();   // → [{ creatorType: "author", firstName, lastName }, …]
```

## Relations

```js
item.getRelations();                          // Record<predicate, string | string[]>
item.getRelationsByPredicate(predicate);      // string[] of URIs
Zotero.Relations.linkedObjectPredicate;       // "owl:sameAs"
Zotero.Relations.replacedItemPredicate;       // "dc:replaces"
await Zotero.URI.getURIItem(uri);             // resolve a Zotero URI (cross-library) → Item | null
```

## Attachments

```js
att.attachmentFilename;                  // "paper.pdf"
att.attachmentContentType;               // "application/pdf"
att.attachmentLinkMode;                  // Zotero.Attachments.LINK_MODE_*
att.attachmentSyncedHash;                // MD5; only set by Zotero File Storage, NOT WebDAV
await att.fileExists();                  // Promise<boolean>
await att.getFilePathAsync();            // Promise<string | false> (false if not local)
Zotero.Attachments.getStorageDirectory(att).path;
```

Finding and downloading full text:

```js
// High-level: find & attach. Returns false *silently* if the item already has a PDF/EPUB.
const newAtt = await Zotero.Attachments.addAvailableFile(item, { methods });
Zotero.Attachments.canFindFileForItem(item);   // false if a PDF/EPUB already exists
Zotero.Attachments.FIND_AVAILABLE_FILE_TYPES;  // ['application/pdf', 'application/epub+zip']

// Low-level: resolve and download to a temp path yourself
const resolvers = Zotero.Attachments.getFileResolvers(item, ["doi", "url", "oa", "custom"]);
const { path: tmpDir } = await Zotero.Attachments.createTemporaryStorageDirectory();
const { title, mimeType, url } = await Zotero.Attachments.downloadFirstAvailableFile(
  resolvers, PathUtils.join(tmpDir, "file"), { enforceFileType: true });
// url === null when nothing was found; throws on hard failures
```

Zotero 10: attachment paths containing slashes throw, and `setType()` to or from
attachment/note/annotation throws.

## Saved searches — `Zotero.Search`

```js
const s = new Zotero.Search();
s.name = "Recent climate papers";                       // required to save
s.libraryID = Zotero.Libraries.userLibraryID;           // default
s.addCondition("title", "contains", "climate");
s.addCondition("dateAdded", "isInTheLast", "30 days");
const searchID = await s.saveTx();                      // persist
const itemIDs = await s.search();                       // run (saving not required)
```

- Conditions are ANDed by default. For OR, add `s.addCondition("joinMode", "any")`
  *before* the other conditions.
- **Zotero 10**: conditions can be grouped (`groupStart` / `groupEnd`, with their own
  `joinMode`, plus `resultLevel`); passing the legacy fourth `required` argument to
  `addCondition` **throws**; `fulltextWord` is gone — use `fulltextContent`. The option
  names are defined in `xpcom/data/search.js` / `searchConditions.js`; check there before
  relying on group syntax.
- `addCondition()` returns a condition ID; `s.removeCondition(id)`,
  `s.getConditions()` → `{ id: { condition, operator, value, … } }`.
- Invalid condition/operator combinations aren't rejected at add time; test the search.
- `saveTx()` without a `name` throws "Name not provided for saved search".

Common conditions: `title`, `anyField`, `creator`, `tag`, `note`, `childNote`,
`itemType` (`journalArticle`, `book`, …), `collection` (value = collection key),
`savedSearch`, `dateAdded`, `dateModified`, `fulltextContent`, `deleted`, `unfiled`.
Common operators: `is`/`isNot`, `contains`/`doesNotContain`, `beginsWith`,
`isBefore`/`isAfter`/`isInTheLast` (dates, e.g. `"7 days"`),
`isLessThan`/`isGreaterThan`, `true`/`false`.

```js
const s2 = await Zotero.Searches.getAsync(searchID);    // or Zotero.Searches.get(id)
Zotero.Searches.getByLibrary(libraryID);
await Zotero.Searches.erase([id1, id2]);
```

## Notifier semantics

Registration is in `plugin-apis.md`. Things that surprise people:

- Moving an item to the trash fires `trash`, **not** `delete`. `delete` fires only on
  permanent erasure (empty trash / `item.eraseTx()`).
- On `delete`, `extraData[id]` still contains `{ libraryID, key }` although the item is
  gone from the DB — use it to clean up your own caches.
- Your own `save()` inside `notify` fires another `modify`; guard against loops.

## Sync

```js
Zotero.Sync.Storage.Local.getEnabledForLibrary(libraryID);  // false = metadata-only sync
await Zotero.Sync.Runner.downloadFile(att);                  // then check att.fileExists()
```

## HTTP

Prefer `Zotero.HTTP.request` over `fetch()`: it honours Zotero's proxy settings, cookies
and authentication.

```js
const req = await Zotero.HTTP.request("GET", url, {
  responseType: "json",      // "blob" | "arraybuffer" | "text" | "json"
  headers: { Accept: "application/json" },
  followRedirects: false,
  errorDelayMax: 0,          // fail immediately instead of retrying with backoff
});
req.status; req.response; req.getResponseHeader("Content-Type");
// non-2xx → throws Zotero.HTTP.UnexpectedStatusException (check e.status)
```

Zotero 10: `Zotero.HTTP.download()` returns a `Response`; `Zotero.CookieSandbox` →
`Zotero.HTTP.newCookieContext()`.

## Database

Use `Zotero.DB` from inside Zotero; never open `zotero.sqlite` from outside while Zotero
runs. Prefer the object API — the schema is internal and changes between versions.

```js
await Zotero.DB.columnQueryAsync(sql, params);   // first column of each row
await Zotero.DB.valueQueryAsync(sql, params);    // single value
await Zotero.DB.queryAsync(sql, params);         // rows
await Zotero.DB.executeTransaction(async () => { /* item.save() calls */ });
```

`itemAttachments` columns worth knowing: `itemID`, `linkMode`
(0 imported_file, 1 imported_url, 2 linked_file, 3 linked_url), `path`
(`"storage:<filename>"` for imported files), `storageHash` (NULL for WebDAV),
`contentType`.

## Files & paths

```js
Zotero.getTempDirectory().path;
PathUtils.join(a, b); PathUtils.filename(path); PathUtils.parent(path);
await IOUtils.exists(path);
await IOUtils.readUTF8(path); await IOUtils.writeUTF8(path, text);
await IOUtils.write(path, uint8Array); await IOUtils.copy(src, dest);
await IOUtils.makeDirectory(path, { createAncestors: true, ignoreExisting: true });
await IOUtils.remove(path, { recursive: true });
await Zotero.File.getContentsAsync(path);
```

`OS.File` / `OS.Path` are gone since Zotero 7.
