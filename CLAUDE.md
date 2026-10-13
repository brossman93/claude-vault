# Claude Vault: Operating Notes

This vault is Claude's working memory for Brent's work at Ashland University (AU). Claude writes here. Brent reads, browses, and corrects.

## Rules
- **Brent's primary vault (`brossman93/obsidian-vault`) is read-only.** Never commit, push, or change anything there. Read it for context only.
- Scope is AU work, plus a light `Personal/` section (interests, faith, reading, Phi Psi, productivity). Leave out JP2 contract work, health, finances, and anything about Kate or family unless Brent asks.
- Write facts and decisions, not transcripts. Keep pages short. Link with `[[wikilinks]]`.
- If Brent edits a page, his version wins. Don't overwrite his changes.
- Once a week (Fridays), consolidate: merge duplicates, trim stale detail, and roll old daily notes into a monthly summary.

## Structure
- `Home.md`: the index and current focus
- `Glossary.md`: AU shorthand, acronyms, and tools
- `People/`: one page per colleague, covering role and what we work on together
- `Projects/`: one page per ongoing area, covering status, decisions, and open questions
- `Personal/`: Brent's non-work interests and context, kept light
- `Inbox.md`: open threads from Brent's AU Outlook inbox; the morning report reads it for Needs attention and Waiting on others, and moves closed items to Done
- `This Week.md`: Brent's 2–3 goals for the week, set Mondays; rank daily priorities against them
- `Daily/`: one note per weekday morning report (`YYYY-MM-DD.md`)
- `Weekly/`: one Friday review per week (`YYYY-Www.md`)
- `.brief/`: the morning brief page builder (see `.brief/README.md`); hidden in Obsidian

## Commits and pushes
- Commit and push vault changes straight to `main` so they sync to Obsidian. Brent approved this on 2026-10-13. No feature branches or pull requests for routine vault updates, even if a session assigns a branch.
- Pull `main` before writing, so Brent's edits from Obsidian aren't overwritten.
- Use `claude: <what changed>` as the message, e.g. `claude: daily note 2026-10-14`.
