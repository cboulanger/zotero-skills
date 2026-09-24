# Zotero Skills for Claude

A [Claude Agent Skill](https://support.claude.com/en/articles/12512176-what-are-skills)
that teaches an agent how to write, port, debug and package **Zotero desktop plugins**
(.xpi) for Zotero 7, 8, 9 and 10: the bootstrapped architecture, lifecycle and window
hooks, the official plugin APIs (MenuManager, ItemTreeManager, ItemPaneManager,
PreferencePanes, Reader listeners, Notifier), Fluent localization, dialogs,
zotero-plugin-toolkit, the Zotero data API (items, attachments, saved searches, sync,
HTTP, DB), update manifests, and version-by-version migration notes.

It is for *developing* plugins, not for querying a Zotero library from an agent.

## What's in the skill

`skills/zotero-plugin-dev/SKILL.md` holds the core workflow. Details sit in reference
files the agent only reads when it needs them:

| File | Covers |
| ---- | ------ |
| `references/plugin-apis.md` | MenuManager, ItemTreeManager, ItemPaneManager, Reader, PreferencePanes, prefs, Notifier, chrome registration |
| `references/version-changes.md` | Migration notes 6→7, 7→8, 8→9, 9→10 and a porting procedure |
| `references/data-api.md` | Libraries, selection, items, creators, relations, attachments, saved searches, sync, HTTP, `Zotero.DB`, files |
| `references/dialogs.md` | XHTML dialogs, `openDialog`, arguments, finding and closing dialogs |
| `references/toolkit.md` | zotero-plugin-toolkit: UITool, DialogHelper, KeyboardManager, PromptManager, VirtualizedTableHelper, … |
| `references/template-workflow.md` | windingwind's zotero-plugin-template / zotero-plugin-scaffold |
| `assets/minimal-plugin/` | Plain-JS starter plugin (Make It Red style) |
| `scripts/build_xpi.py` | Packages a plugin and writes `updates.json` with the sha256 |

## Install

### Claude Code (plugin marketplace, recommended)

```shell
/plugin marketplace add cboulanger/zotero-skills
/plugin install zotero-skills@zotero-skills
```

**Automatic updates:** Claude Code does not auto-update third-party marketplaces by
default. Enable it once: run `/plugin`, open the **Marketplaces** tab, select
`zotero-skills`, and choose **Enable auto-update**. Claude Code then checks for a new
version shortly after startup; updates apply on the next launch or after
`/reload-plugins`. Without auto-update, run `/plugin marketplace update zotero-skills`.

Upgrading from 1.x: the five skills `zotero-plugin-basics`, `zotero-plugin-dialogs`,
`zotero-api`, `zotero-plugin-toolkit` and `saved-search` are now one skill,
`zotero-plugin-dev`. Their content lives on in the reference files above.

### Claude Code (without the marketplace)

```bash
python tools/package_skill.py --install-claude-code     # copies into ~/.claude/skills/
```

or symlink `skills/zotero-plugin-dev` into `~/.claude/skills/` (user-wide) or
`.claude/skills/` inside a plugin repo (project-scoped); `git pull` then updates it.

### claude.ai / Claude desktop / API

Download `zotero-plugin-dev.skill` from the latest [release](../../releases) and upload
it in the Skills section of your settings, or through the Skills API. Re-upload to update.

## Repository layout

```
.claude-plugin/marketplace.json  plugin marketplace manifest (plugin version lives here)
skills/zotero-plugin-dev/        the skill (SKILL.md, references/, scripts/, assets/)
  evals/evals.json               test prompts (kept in the repo, not shipped)
tools/package_skill.py           validates skill + marketplace, builds dist/<name>.skill
tools/set_version.py             writes the release version (called by semantic-release)
.releaserc.json                  semantic-release configuration
commitlint.config.mjs            Conventional Commits rules (CI + commit-msg hook)
.github/workflows/skill.yml      CI: lint commits, validate, release
```

## Versioning and releases

Versions are **never edited by hand**. They are derived from the commit messages by
[semantic-release](https://semantic-release.gitbook.io/) whenever commits reach `main`,
so every commit must follow [Conventional Commits](https://www.conventionalcommits.org/):

| Commit | Release | Use for |
| ------ | ------- | ------- |
| `fix: …` | patch (2.0.0 → 2.0.1) | corrections to skill content or tooling |
| `feat: …` | minor (2.0.0 → 2.1.0) | new guidance, new reference files, support for a new Zotero version |
| `feat!: …` or a `BREAKING CHANGE:` footer | major (2.0.0 → 3.0.0) | renamed or removed skills, changed install path |
| `docs:`, `chore:`, `ci:`, `refactor:`, `test:`, `style:`, `build:`, `perf:` | none | README, CI, repo housekeeping |

A scope is optional, e.g. `feat(data-api): document Zotero.Relations`. Anything under
`skills/` that users should receive needs a `fix` or `feat` commit.

On each push to `main`, CI

1. lints the pushed commits with commitlint (pull requests: every commit and the PR
   title, which becomes the message on a squash merge),
2. validates and packages the skill,
3. runs semantic-release, which picks the next version, writes it into
   `skills/*/SKILL.md` and `.claude-plugin/marketplace.json` (`tools/set_version.py`),
   prepends release notes to `CHANGELOG.md`, commits `chore(release): x.y.z [skip ci]`,
   tags `vx.y.z` and publishes a GitHub release with `zotero-plugin-dev.skill` attached.

Claude Code only updates a marketplace install when the plugin `version` changes, so
this is also what makes auto-update work for users.

Local setup (Node 22.14+ or 24): `npm install` installs commitlint and a husky
`commit-msg` hook that rejects non-conventional messages before they are committed.
`npm run check` (or `python tools/package_skill.py --check`) validates the skill;
`npm run release:dry` previews the next version (needs a GitHub token).

Validation checks the frontmatter (allowed keys, kebab-case name matching the folder,
description ≤ 1024 chars with no angle brackets), that each skill has exactly one
`SKILL.md`, that every `references/`, `scripts/` and `assets/` path mentioned in
`SKILL.md` exists, and that the marketplace lists existing skills with a version matching the skill's.

## Keeping it current

Zotero's developer notes live in per-version pages
([7](https://www.zotero.org/support/dev/zotero_7_for_developers),
[8](https://www.zotero.org/support/dev/zotero_8_for_developers),
[9](https://www.zotero.org/support/dev/zotero_9_for_developers),
[10](https://www.zotero.org/support/dev/zotero_10_for_developers)). When a new major
appears, add a section to `references/version-changes.md`, update the version range in
`SKILL.md` and the starter plugin's `strict_max_version`, and commit as `feat:`.
The plugin API sources in
[zotero/zotero `xpcom/pluginAPI/`](https://github.com/zotero/zotero/tree/main/chrome/content/zotero/xpcom/pluginAPI)
are the ground truth for option lists.

## Contributing

Keep `SKILL.md` short and put detail in `references/`; mention every new reference file
from `SKILL.md` with a sentence saying when to read it. Add an eval prompt to
`evals/evals.json` for new behaviour, and use Conventional Commits (see above). See [agentskills.io](https://agentskills.io) for
the skill format.

## License

Public domain: [CC0 1.0 Universal](LICENSE). To the extent possible under law, the
authors have waived all copyright and related rights to this work; you may copy, modify
and redistribute it, including for commercial purposes, without asking permission.
The starter plugin follows patterns from Zotero's
[Make It Red](https://github.com/zotero/make-it-red) sample.
