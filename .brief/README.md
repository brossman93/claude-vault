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
- `meetings` (only if AU meetings today), `needs`, `resolved`, `missed`, `replies`, `pmail`, `hand`: lists of {id, title, url, body, who?, where?, when?, button? {label, seed}}. `id` keeps each item's update box stable across days: the monday item id, or a short slug of the topic.
- `meetings[].agenda` (optional): path of an agenda note that already exists in Brent's Obsidian vault, relative to the vault root, e.g. `2026.10.14 Team Touchbase.md` or `AU Meetings/2026.10.14 ADV x Marketing.md`. The page links it as `obsidian://open?vault=Obsidian&file=…`. Never create an agenda.
- `tasks`: today's ranked candidates [{id (monday item id), title, url, why, priority, status, due (YYYY-MM-DD or ""), board, boardId, statusCol, rank}]; `goalsNote`
- `waiting` [{id, title, who, days (business days), since, url, note}], longest first. Items over 3 business days get a Nudge link that opens Claude to draft a follow-up.
- `yesterday` [{tag, text}]
- `replies` (optional): AU email replies owed, same item shape as `needs`
- `ac`: {asOf, lead? (UG nurture line), stall?, sends? [[name, sends, opens, clicks, bounces, unsubs]], sendsCaption?, sendsNote?, scheduled?, flag?, automations [{name, status, now, entered, sends, open, click, emails [[name, sends, openRate, clickRate, ctor]], note}]}; the first automation is charted by touchpoint when its `emails` list is non-empty, as three stacked line charts (Open rate, Click rate, CTOR) by step (TP number). Each line follows the main path: per step, the email with no `-N` suffix, else the lowest N (TP4-1 General). Other versions at the same step are small dots; under 50 sends is a hollow dot. Y axes scale to the data. Hover or tap a point for its email, rate, and sends. A "Numbers by email" dropdown under the charts holds the full table; `open`/`click` may be null to hide rates. The Family lane shows only when a family event is passed
- Touchpoint rates come from ONE `run_campaign_performance_report` call (explore `all_campaigns_performance`, filter campaign_name CONTAINS "UG INQ") and are used exactly as returned, rounded to one decimal: `open_rate`, `click_rate` (unique_subscriber_clicks ÷ sends), `click_to_open_rate` (unique clicks ÷ unique opens). Never compute a click rate from total or non-unique link clicks, and never use list_campaigns' `linkclicks` for rates. `ctor` is optional; rows without it leave the CTOR cell empty.
- `ac.rfis` (optional): RFI form counts shown above the automation cards, [{name, count (null if the call failed), label ("Yesterday" or "Fri–Sun"), url, linkText, note?}]. Ashland.edu link: saved AC segment 1507 "Brief: Ashland.edu RFIs yesterday" (Origin Source = Form Fills, RFI date = yesterday, no InPursuit tag).
- `ac.engagementBands` (optional): engagement score bands table shown under the RFI counts, {caption, url, linkText, days [labels, oldest first, e.g. "Wed 10/14"], changeLabel, rows [{label, url, values [one per day, null if a call failed], change, total?}]}. Values are ACTIVE contacts per band segment (legacy ids 1529/1528/1527/1526), read from the audiences call's `last_active_total`. The trailing days come from the "Engagement bands" lines in `Daily/` notes.
- `ac.mailings` (optional): Slate mailing cards shown under the RFI counts, [{title, sub, asOf, endsOn, stats [[label, value, comparison?, warn?]], note, report, reportText, url, urlText}]. The morning run copies them from `.brief/mailings.json`, a snapshot Claude updates in a live chat (Slate can't be reached unattended). Comparison reports live in `.brief/reports/` and are published as their own artifacts (Preview Day emails: https://claude.ai/artifact/K5kQ3amzkUXP6kiqGaceFJ).
- `news` [{title, source, date, url, summary, why}]
- `deletions` [{sender, what, threads [Gmail thread ids]}]

## Task store (artifact db, collection `tasks`)
One document per task, id = monday item id or `c-…` for Brent's own. Fields: title, url, why, priority, status, due, board, boardId, statusCol, rank, source ("monday"|"custom"), active, done, doneDay, prevStatus, mondaySynced, userRanked, surfaced. The page writes rank, done, doneDay, and custom tasks; the morning run reads them before ranking and writes the day's candidates back.

## Update boxes (artifact db, collection `notes`)
Every action item (meetings, needs, priorities, missed, replies, waiting, personal email, deletions, hand-offs) has a box. "Save for tomorrow" writes a document with id `<date>_<section>_<item id>` and fields date, section, key, title, text, status ("new"), savedAt. "Ask Claude now" opens a new Claude chat seeded with the item and Brent's words, and saves the note with status "asked". The next morning run reads notes with status "new" or "asked", applies them, and sets status to "applied" with appliedOn.

## Links
Every link opens in a new tab (`<base target="_blank">` plus explicit targets).
