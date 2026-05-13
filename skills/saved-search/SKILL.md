---
name: saved-search
description: Create, modify, retrieve, and execute Zotero saved searches programmatically using the Zotero.Search API. Covers conditions, operators, join modes, and the saveTx() persistence pattern.
---

# Saved Searches

How to create, modify, retrieve, and run saved searches in Zotero using `Zotero.Search`.

## Overview

Saved searches in Zotero are persistent, named queries stored in the database. They live in `chrome/content/zotero/xpcom/data/search.js` and extend `Zotero.DataObject`. The plural manager class `Zotero.Searches` handles retrieval. Saved searches appear in the collections pane and are re-evaluated dynamically each time they are opened.

## Key Concepts

- **Conditions**: Each condition is a triple of `(condition, operator, value)` — e.g., `('title', 'contains', 'climate')`. Conditions are stored by integer ID returned from `addCondition()`.
- **Join mode**: Conditions default to AND logic. Add `joinMode`/`any` as the first condition to switch to OR.
- **Required flag**: The optional fourth argument to `addCondition()` marks a condition as required when using ANY join mode.
- **saveTx()**: Persists the search and its conditions to SQLite. Returns the new integer `searchID` for new objects.
- **search()**: Executes the search and returns an array of matching item IDs. Does not require saving first.

## Steps

1. Instantiate `new Zotero.Search()`
2. Set `name` (required) and optionally `libraryID`
3. Add one or more conditions with `addCondition()`
4. Call `await search.saveTx()` to persist

## Code Examples

### Create and save a basic search

```javascript
const search = new Zotero.Search();
search.name = "Recent climate papers";
search.libraryID = Zotero.Libraries.userLibraryID; // optional, this is the default

search.addCondition('title', 'contains', 'climate');
search.addCondition('dateAdded', 'isInTheLast', '30 days');

const searchID = await search.saveTx();
```

### OR logic with joinMode

```javascript
const search = new Zotero.Search();
search.name = "Papers by Smith or Jones";
search.addCondition('joinMode', 'any'); // must be added before other conditions
search.addCondition('creator', 'contains', 'Smith');
search.addCondition('creator', 'contains', 'Jones');
await search.saveTx();
```

### Run without saving

```javascript
const search = new Zotero.Search();
search.libraryID = Zotero.Libraries.userLibraryID;
search.addCondition('tag', 'is', 'to-read');
const itemIDs = await search.search();
```

### Retrieve and modify an existing search

```javascript
const search = await Zotero.Searches.getAsync(searchID);
search.addCondition('itemType', 'is', 'journalArticle');
await search.saveTx();
```

### Remove a condition

```javascript
const search = new Zotero.Search();
search.name = "Test";
const condID = search.addCondition('title', 'contains', 'foo');
search.removeCondition(condID);
```

### Inspect conditions

```javascript
const conditions = search.getConditions();
// { 0: { id: 0, condition: 'title', operator: 'contains', value: 'foo', required: false }, ... }
```

## Common Conditions

| Condition | Notes |
|---|---|
| `title`, `anyField` | Item field matching |
| `creator`, `author`, `editor`, `lastName` | Creator fields |
| `tag` | Tag matching |
| `note`, `childNote` | Note content |
| `itemType` | e.g., `'journalArticle'`, `'book'` |
| `collection` | Restrict to a collection (value = collection key) |
| `savedSearch` | Restrict to results of another saved search |
| `dateAdded`, `dateModified` | Date fields |
| `fulltextContent`, `fulltextWord` | Full-text search |
| `deleted` | Include/exclude deleted items |
| `unfiled` | Items not in any collection |
| `joinMode` | `'any'` or `'all'` (default) |

## Common Operators

| Operator | Applicable to |
|---|---|
| `is`, `isNot` | Most fields |
| `contains`, `doesNotContain` | String fields |
| `beginsWith` | String fields |
| `isBefore`, `isAfter` | Date fields |
| `isInTheLast` | Date fields; value like `'7 days'`, `'1 month'` |
| `isLessThan`, `isGreaterThan` | Numeric fields |
| `true`, `false` | Boolean conditions |

## Manager API (`Zotero.Searches`)

```javascript
Zotero.Searches.get(id)                   // synchronous
await Zotero.Searches.getAsync(id)        // async
Zotero.Searches.getByLibrary(libraryID)   // all searches in a library
Zotero.Searches.getAll(libraryID)         // all, sorted by name
await Zotero.Searches.erase([id1, id2])   // delete
```

## Validation

- `name` is required — `saveTx()` throws `"Name not provided for saved search"` if empty.
- `libraryID` defaults to the user library if not set.
- Conditions are not validated at add time; invalid condition/operator combinations are silently ignored at search time.

## Related Skills

- See [zotero-plugin-basics](../zotero-plugin-basics/SKILL.md) for plugin scaffolding and the general Zotero data object lifecycle.
