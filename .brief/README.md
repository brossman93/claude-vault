# Morning brief builder

The weekday report renders through `build.py` so the page keeps the same design and interactive parts every day. Hidden from Obsidian because the folder name starts with a dot.

```
python3 .brief/build.py data.json out.html --preview preview.html
```

Publish `out.html` to https://claude.ai/artifact/Bvu81Ucp9Tuz2TDZR4CEaL with the Artifact tool, passing that `url` and omitting `capabilities` so the stored ones stay (db, user, mcp: monday.com `change_item_column_values`, Gmail `trash_thread`). Never commit `data.json`: it holds personal email content.

## data.json fields
- `date` (YYYY-MM-DD), `dayDate`, `headline`, `motif` ("sun" or omit), `flag` (bool, clay deadline flag), `acts` [3 × {time, text}]
- `days` [today, tomorrow] (Mondays: one per weekday): {label, date, events [{lane: "au"|"family", start, end (decimal hours), title, sub, url}], allday [{title, url}], kateCount}
- `weekly` (Mon/Fri only): {title, html}
- `meetings` (only if AU meetings today), `needs`, `resolved`, `missed`, `pmail`, `hand`: lists of {title, url, body, who?, where?, when?, button? {label, seed}}
- `tasks`: today's ranked candidates [{id (monday item id), title, url, why, priority, status, due (YYYY-MM-DD or ""), board, boardId, statusCol, rank}]; `goalsNote`
- `waiting` [{title, who, days (business days), since, url, note}], longest first
- `yesterday` [{tag, text}]
- `ac`: {asOf, flag?, automations [{name, status, now, entered, sends, open, click, emails [[name, sends, openRate, clickRate]], note}]}; the first automation is charted by touchpoint
- `news` [{title, source, date, url, summary, why}]
- `deletions` [{sender, what, threads [Gmail thread ids]}]

## Task store (artifact db, collection `tasks`)
One document per task, id = monday item id or `c-…` for Brent's own. Fields: title, url, why, priority, status, due, board, boardId, statusCol, rank, source ("monday"|"custom"), active, done, doneDay, prevStatus, mondaySynced, userRanked, surfaced. The page writes rank, done, doneDay, and custom tasks; the morning run reads them before ranking and writes the day's candidates back.
