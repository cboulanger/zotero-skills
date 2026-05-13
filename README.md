# Zotero Skills for Claude

A collection of [Claude Agent Skills](https://support.claude.com/en/articles/12512176-what-are-skills) for developing Zotero plugins and add-ons. Skills range from general plugin scaffolding to specific Zotero API patterns.

## What are Skills?

Skills are markdown files that Claude loads dynamically to improve performance on specialized tasks. Each skill in this repo teaches Claude how to accomplish a specific Zotero development task in a repeatable, well-informed way.

## Available Skills

| Skill | Description |
| ----- | ----------- |
| [zotero-plugin-basics](skills/zotero-plugin-basics/SKILL.md) | Scaffold, structure, build, and load a Zotero plugin using zotero-plugin-scaffold |
| [zotero-plugin-dialogs](skills/zotero-plugin-dialogs/SKILL.md) | Dialogs (XHTML), menus (XUL), and preference panes |
| [zotero-api](skills/zotero-api/SKILL.md) | Zotero JS API — items, attachments, sync, HTTP, DB, notifier, logging |
| [zotero-plugin-toolkit](skills/zotero-plugin-toolkit/SKILL.md) | zotero-plugin-toolkit API — UITool, dialogs, keyboard, progress, tables |
| [saved-search](skills/saved-search/SKILL.md) | Create, modify, retrieve, and execute Zotero saved searches via `Zotero.Search` |

More skills will be added as needed. Skills reference each other to avoid duplication.

## Installing in Claude Code

Register this repository as a plugin marketplace:

```shell
/plugin marketplace add cboulanger/zotero-skills
```

Or install a skill directly by path — copy the contents of a `SKILL.md` file into your project's `.claude/commands/` directory.

## Skill Scope

Skills in this repo cover:

- **General**: Plugin scaffolding, file structure, build tooling, plugin lifecycle
- **API patterns**: Collections, items, saved searches, notes, attachments, tags
- **UI**: XUL/HTML overlays, preference panes, progress windows, menus
- **Storage**: Zotero database access, custom fields, extra field conventions
- **Sync & integration**: Zotero sync hooks, connectors, translators

## Contributing

To add a new skill:

1. Copy `template/SKILL.md` into a new folder under `skills/<skill-name>/`
2. Fill in the frontmatter `name` and `description`
3. Write the instructions — reference other skills by name rather than duplicating content
4. Add a row to the table above

For the skill format specification, see [agentskills.io](https://agentskills.io).
