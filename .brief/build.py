#!/usr/bin/env python3
"""Build Brent's interactive morning brief from a data JSON file.

Usage: python3 build.py data.json out.html [--preview preview.html]

out.html is the artifact body (no doctype/html/head/body; the Artifact tool
adds the skeleton). --preview also writes a standalone page for screenshots.
The page keeps priorities in the artifact's `db` (collection `tasks`), Brent's
item updates in `notes` (read by the next morning run), and
calls monday.com and Gmail through the `mcp` capability. Publish with
capabilities: {"db": {}, "user": {}, "mcp": {"servers": [
  {"server": "monday.com", "tools": ["change_item_column_values"]},
  {"server": "Gmail", "tools": ["trash_thread"]}]}}
"""
import base64, html, json, math, pathlib, re, sys, urllib.parse
from datetime import date

HERE = pathlib.Path(__file__).parent
e = html.escape


def font_b64():
    for p in [HERE / 'fraunces-latin-600-normal.woff2']:
        if p.exists():
            return base64.b64encode(p.read_bytes()).decode()
    return ''


def seed_href(seed):
    return 'https://claude.ai/new?q=' + urllib.parse.quote(seed, safe='') + '&surface=cowork&composer=mini'


NT = ' target="_blank" rel="noopener"'
OBSIDIAN_VAULT = 'Obsidian'


def btn(b, cls='btn'):
    if not b:
        return ''
    return f'<a class="{cls}" href="{e(seed_href(b["seed"]))}"{NT}>{e(b["label"])}</a>'


def link(title, url):
    return f'<a href="{e(url)}"{NT}>{e(title)}</a>' if url else e(title)


def slug(t):
    return re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')[:40] or 'item'


def agenda_href(path):
    p = path[:-3] if path.endswith('.md') else path
    return 'obsidian://open?vault=' + urllib.parse.quote(OBSIDIAN_VAULT, safe='') + '&file=' + urllib.parse.quote(p, safe='')


def note_box(sec, key, title):
    """A small box under an item: save an update for tomorrow's run, or hand it to Claude now."""
    return (f'<div class="nb" data-sec="{e(sec)}" data-key="{e(key)}" data-title="{e(title)}">'
            f'<textarea rows="1" aria-label="Update or instruction about {e(title)}" '
            f'placeholder="Update, or tell Claude what to do…"></textarea>'
            f'<div class="nb-a"><button type="button" class="btn-sm nb-save">Save for tomorrow</button>'
            f'<a class="btn-sm primary nb-ask" href="#"{NT}>Ask Claude now</a>'
            f'<span class="nb-msg" aria-live="polite"></span></div></div>')


def nudge_seed(w):
    return (f"Draft a short, friendly follow-up nudge to {w['who']} about the item I've titled \"{w['title']}\" in my morning brief. "
            f"I've been waiting since {w['since']} ({w['days']} business days). Find the context in my claude-vault Inbox.md and the "
            "related People/ and Projects/ pages, and in monday.com if it's a monday item. Write it in my voice for the channel the "
            "ask came through (email or a monday update), and keep it to a few sentences. Don't send anything. Done is a draft I can "
            "copy, with a suggested subject line if it's an email.")


def hour_label(h):
    hh = int(h)
    m = int(round((h - hh) * 60))
    suf = 'AM' if hh < 12 else 'PM'
    h12 = hh % 12 or 12
    return f'{h12}:{m:02d} {suf}' if m else f'{h12} {suf}'


# ---------- terrain ----------
def terrain(d):
    W, BASE, H0, H1 = 840, 118, 7, 21
    today = d['days'][0]['events'] if d.get('days') else []
    def x_of(h):
        return (h - H0) / (H1 - H0) * W
    bumps = []
    for ev in today:
        mid = (ev['start'] + ev['end']) / 2
        dur = ev['end'] - ev['start']
        amp = min(46, 14 + 10 * dur) * (1.0 if ev['lane'] == 'au' else 0.75)
        sig = max(26, dur / (H1 - H0) * W * 0.55)
        bumps.append((x_of(mid), amp, sig, ev['lane'], dur))
    pts = []
    for i in range(0, 85):
        x = i * W / 84
        y = BASE - sum(a * math.exp(-((x - cx) ** 2) / (2 * s * s)) for cx, a, s, _, _ in bumps)
        pts.append((x, y))
    path = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)
    dots = ''
    for cx, a, s, lane, dur in bumps:
        r = max(6, min(13, 6 + dur * 2.5))
        cls = 'dot-au' if lane == 'au' else 'dot-fam'
        dots += f'<circle class="{cls}" cx="{cx:.1f}" cy="{BASE - a:.1f}" r="{r:.1f}"/>'
    motif = ''
    if d.get('motif') == 'sun':
        motif = ('<g class="ink-line" fill="none" stroke-width="1.6" stroke-linecap="round"><circle cx="140" cy="58" r="14"/>'
                 '<path d="M140 34v-8 M140 90v-8 M116 58h-8 M172 58h-8 M123 41l-6-6 M163 81l-6-6 M157 41l6-6 M117 81l6-6"/></g>')
    flag = ('<path class="ink-line" d="M826 118 V 72" stroke-width="1.8" fill="none"/>'
            '<path class="clay-fill" d="M826 73 L 838 79 L 826 85 Z"/>') if d.get('flag', True) else ''
    return (f'<svg class="terrain" viewBox="0 0 840 160" role="img" aria-label="Shape of the day">'
            f'<path class="ink-line" d="{path}" fill="none" stroke-width="2.2" stroke-linecap="round"/>'
            f'{motif}{dots}{flag}</svg>')


# ---------- calendar ----------
def calendar(d):
    H0, H1 = 7, 21
    span = H1 - H0
    ticks = ''.join(f'<span style="left:{(h - H0) / span * 100:.2f}%">{hour_label(h).replace(":00", "")}</span>' for h in range(H0, H1 + 1, 2))
    out = ['<div class="cal">']
    for day in d['days']:
        lanes = ''
        has_fam = any(x['lane'] == 'family' for dd in d['days'] for x in dd['events'])
        for lane, label in (('au', 'AU'), ('family', 'Family')):
            if lane == 'family' and not has_fam:
                continue
            blocks = ''
            for ev in [x for x in day['events'] if x['lane'] == lane]:
                left = (max(ev['start'], H0) - H0) / span * 100
                width = max(1.2, (min(ev['end'], H1) - max(ev['start'], H0)) / span * 100)
                tip = f'{hour_label(ev["start"])} to {hour_label(ev["end"])} · {ev["title"]}'
                blocks += f'<span class="blk blk-{lane}" style="left:{left:.2f}%;width:{width:.2f}%" title="{e(tip)}"></span>'
            lanes += f'<div class="lane"><span class="lane-l">{label}</span><div class="track">{blocks}</div></div>'
        evs = sorted(day['events'], key=lambda x: x['start'])
        rows = ''.join(
            f'<li><span class="sw sw-{ev["lane"]}" aria-hidden="true"></span><span class="t">{hour_label(ev["start"])}</span>'
            f'<span class="d">{link(ev["title"], ev.get("url"))}<small>{e(ev.get("sub", ""))}</small></span></li>' for ev in evs)
        if not evs:
            rows = '<li class="quiet">No timed events.</li>'
        allday = ''.join(f'<li>{link(a["title"], a.get("url"))}</li>' for a in day.get('allday', []))
        kate = day.get('kateCount', 0)
        kate_line = f'<p class="kate">Kate also has {kate} work, law school, and chapter items on the Family Calendar.</p>' if kate else ''
        out.append(f'''<div class="cal-day"><div class="cal-h"><b>{e(day["label"])}</b><span>{e(day["date"])}</span></div>
<div class="axis">{ticks}</div>{lanes}
<ul class="cal-list">{rows}</ul>{f'<ul class="allday">{allday}</ul>' if allday else ''}{kate_line}</div>''')
    if any(x['lane'] == 'family' for dd in d['days'] for x in dd['events']):
        out.append('<p class="legend"><span class="sw sw-au"></span>AU calendar <span class="sw sw-family"></span>Family Calendar</p>')
    out.append('</div>')
    return ''.join(out)


# ---------- generic list ----------
def items(lst, sec=None, numbered=True):
    out = '<ol class="list">'
    for i, it in enumerate(lst, 1):
        meta = ''
        if it.get('who'):
            meta = f'<span class="meta">{e(it["who"])}{" · " + e(it["where"]) if it.get("where") else ""}{" · " + e(it["when"]) if it.get("when") else ""}</span>'
        agenda = (f'<p class="agenda"><a href="{e(agenda_href(it["agenda"]))}"{NT}>Open agenda in Obsidian</a></p>'
                  if it.get('agenda') else '')
        box = note_box(sec, it.get('id') or slug(it['title']), it['title']) if sec else ''
        out += (f'<li><span class="n">{i if numbered else ""}</span><div class="li-b"><h3>{link(it["title"], it.get("url"))}</h3>{meta}'
                f'<p>{e(it["body"])}</p>{agenda}{("<p class=b>" + btn(it.get("button")) + "</p>") if it.get("button") else ""}{box}</div></li>')
    return out + '</ol>'


def waiting(d):
    mx = max(10, max(w['days'] for w in d['waiting']))
    scale = math.ceil(mx / 10) * 10
    rows = ''
    for w in d['waiting']:
        pct = w['days'] / scale * 100
        nudge = w['days'] > 3
        nl = (f'<a class="pill-warn nudge" href="{e(seed_href(nudge_seed(w)))}"{NT} title="Draft a follow-up to {e(w["who"])}">'
              '&#9650; Nudge <span aria-hidden="true">&#8599;</span></a>') if nudge else ''
        rows += (f'<li><div class="w-h">{link(w["title"], w.get("url"))}{nl}</div>'
                 f'<div class="w-bar"><span style="width:{pct:.1f}%" title="{w["days"]} business days"></span><b>{w["days"]} business days</b></div>'
                 f'<p>{e(w["who"])} · since {e(w["since"])}. {e(w["note"])}</p>{note_box("waiting", w.get("id") or slug(w["title"]), w["title"])}</li>')
    return f'<ul class="wait">{rows}</ul>'


def yesterday(d):
    return '<ul class="yday">' + ''.join(f'<li><span class="tag">{e(y["tag"])}</span><span>{e(y["text"])}</span></li>' for y in d['yesterday']) + '</ul>'


def bands_block(a):
    """Engagement score bands: active contacts per saved segment, trailing report days, change column."""
    b = a.get('engagementBands')
    if not b:
        return ''
    days = b.get('days') or []
    head = '<th>Band</th>' + ''.join(f'<th>{e(dy)}</th>' for dy in days) + f'<th>{e(b.get("changeLabel", "Change"))}</th>'
    def num(v):
        return '—' if v is None else f'{v:,}'
    def chg(v):
        if v is None:
            return '—'
        return '0' if v == 0 else (f'+{v:,}' if v > 0 else f'−{abs(v):,}')
    rows = ''
    for r in b.get('rows', []):
        lab = link(r['label'], r.get('url'))
        rows += (f'<tr class="{"tot" if r.get("total") else ""}"><td>{lab}</td>' + ''.join(f'<td>{num(v)}</td>' for v in r.get('values', []))
                 + f'<td>{chg(r.get("change"))}</td></tr>')
    cap = e(b.get('caption', 'Engagement score bands'))
    if b.get('url'):
        cap += f' <a href="{e(b["url"])}"{NT}>{e(b.get("linkText", "Segments in AC"))} &#8599;</a>'
    note = f'<p class="note">{e(b["note"])}</p>' if b.get('note') else ''
    return (f'<figure class="ug bands"><figcaption>{cap}</figcaption><table class="sends"><thead><tr>{head}</tr></thead>'
            f'<tbody>{rows}</tbody></table>{note}</figure>')



TP_RE = re.compile(r'TP\s*(\d+)(?:\s*-\s*(\d+))?', re.I)


def touchpoint_charts(emails, as_of):
    """UG nurture by touchpoint: three stacked line charts (open, click, CTOR) plus a
    dropdown table of the numbers by email.

    emails rows: [name, sends, open_rate, click_rate, ctor] exactly as AC's report returns
    them (click_rate = unique_subscriber_clicks / sends; ctor = unique clicks / unique opens).
    Never derive a rate from total clicks.

    Each email is placed at its step (TP number). The line follows the main path: per step,
    the email with no "-N" suffix, else the lowest N (TP4-1 General). Other versions at the
    same step (pathways, TP3-2, TP9-2, TP11-2) are plotted as smaller dots. Under 50 sends =
    hollow dot."""
    has_ctor = any(len(r) > 4 and r[4] is not None for r in emails)
    # ---- table (dropdown) ----
    th = '<th>Email</th><th>Sends</th><th>Open rate</th><th>Click rate</th>' + ('<th>CTOR</th>' if has_ctor else '')
    trs = ''
    for r in emails:
        name, ns, op, cl = r[:4]
        ct = r[4] if len(r) > 4 else None
        cells = f'<td>{e(name)}</td><td>{ns:,}</td><td>{op:.1f}%</td><td>{cl:.1f}%</td>'
        if has_ctor:
            cells += f'<td>{"" if ct is None else f"{ct:.1f}%"}</td>'
        trs += f'<tr{" class=low" if ns < 50 else ""}>{cells}</tr>'
    table = (f'<details class="lc-tbl"><summary>Numbers by email</summary>'
             f'<div class="tbl-scroll"><table class="sends"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'
             f'<p class="note">Faded rows have under 50 sends.</p></details>')
    # ---- placement ----
    pts = []
    for r in emails:
        m = TP_RE.search(r[0])
        if not m:
            continue
        pts.append({'row': r, 'step': int(m.group(1)), 'sub': int(m.group(2)) if m.group(2) else 0})
    steps = sorted({p['step'] for p in pts})
    if len(steps) < 2:
        cap = f'UG Inquiry nurture, by touchpoint <small>lifetime, as of {e(as_of)}</small>'
        return f'<figure class="ug lines"><figcaption>{cap}</figcaption>{table}</figure>'
    main = {}
    for p in pts:
        cur = main.get(p['step'])
        key = (p['sub'] if p['sub'] else 0, -p['row'][1])
        if cur is None or key < (cur['sub'] if cur['sub'] else 0, -cur['row'][1]):
            main[p['step']] = p
    xpct = {st: i / (len(steps) - 1) * 100 for i, st in enumerate(steps)}
    metrics = [(2, 'Open rate', 'o', 'open'), (3, 'Click rate', 'c', 'click')]
    if has_ctor:
        metrics.append((4, 'CTOR', 'k', 'click-to-open'))
    out = ''
    for idx, title, cls, word in metrics:
        vals = [p['row'][idx] for p in pts if len(p['row']) > idx and p['row'][idx] is not None]
        hi = max(vals) if vals else 1
        step_sz = next(sz for sz in (0.5, 1, 2, 5, 10, 20, 25) if hi / sz <= 5)
        ymax = max(step_sz * math.ceil(hi / step_sz + 1e-9), step_sz)
        ticks = [round(i * step_sz, 2) for i in range(int(round(ymax / step_sz)) + 1)]
        yp = lambda v: 100 - v / ymax * 100
        grid = ''.join(f'<line x1="0" x2="100" y1="{yp(t):.2f}" y2="{yp(t):.2f}"/>' for t in ticks)
        ylab = ''.join(f'<span class="yt" style="top:{yp(t):.2f}%">{t:g}%</span>' for t in ticks)
        xlab = ''.join(f'<span class="xt" style="left:{xpct[st]:.2f}%">TP{st}</span>' for st in steps)
        mline = [main[st] for st in steps if len(main[st]['row']) > idx and main[st]['row'][idx] is not None]
        poly = ' '.join(f'{xpct[p["step"]]:.2f},{yp(p["row"][idx]):.2f}' for p in mline)
        dots = ''
        by_step = {}
        for p in pts:
            if p is not main[p['step']] and len(p['row']) > idx and p['row'][idx] is not None:
                by_step.setdefault(p['step'], []).append(p)
        for st, ps in by_step.items():
            n = len(ps)
            for i, p in enumerate(ps):
                dx = (i - (n - 1) / 2) * 7 if n > 1 else 9
                if st == steps[-1]:
                    dx = -abs(dx) - 4
                name, ns = p['row'][0], p['row'][1]
                v = p['row'][idx]
                dots += (f'<span class="pt br{" lo" if ns < 50 else ""}" tabindex="0" style="left:calc({xpct[st]:.2f}% + {dx:.1f}px);top:{yp(v):.2f}%" '
                         f'data-n="{e(name)}" data-v="{v:.1f}% {word}" data-s="{ns:,} sends{" (under 50)" if ns < 50 else ""}" data-t="Branch version"></span>')
        for p in mline:
            name, ns = p['row'][0], p['row'][1]
            v = p['row'][idx]
            dots += (f'<span class="pt mn" tabindex="0" style="left:{xpct[p["step"]]:.2f}%;top:{yp(v):.2f}%" '
                     f'data-n="{e(name)}" data-v="{v:.1f}% {word}" data-s="{ns:,} sends" data-t="Main path"></span>')
        first, last = mline[0]['row'][idx], mline[-1]['row'][idx]
        lab = (f'<span class="dl" style="left:{xpct[mline[0]["step"]]:.2f}%;top:{yp(first):.2f}%">{first:.1f}%</span>'
               f'<span class="dl end" style="left:{xpct[mline[-1]["step"]]:.2f}%;top:{yp(last):.2f}%">{last:.1f}%</span>')
        diff = last - first
        out += (f'<div class="lc {cls}"><div class="lc-h"><b>{title}</b><span>{first:.1f}% → {last:.1f}% <small>({diff:+.1f} pts, TP{mline[0]["step"]} to TP{mline[-1]["step"]})</small></span></div>'
                f'<div class="plot" role="img" aria-label="{title} by touchpoint, main path from {first:.1f}% to {last:.1f}%">'
                f'<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><g class="g">{grid}</g>'
                f'<line class="xh" x1="0" x2="0" y1="0" y2="100"/><polyline class="ln" points="{poly}"/></svg>'
                f'{ylab}{xlab}{dots}{lab}<div class="tip" hidden></div></div></div>')
    cap = (f'UG Inquiry nurture, engagement across the series <small>lifetime, as of {e(as_of)}; rates as AC reports them '
           f'(click = unique clicks ÷ sends, CTOR = unique clicks ÷ unique opens). The line follows the main path '
           f'(TP4-1 General at the pathway step); small dots are other versions at the same step; hollow dots have under 50 sends. '
           f'Hover or tap a point for its email.</small>')
    return f'<figure class="ug lines"><figcaption>{cap}</figcaption><div class="lcs">{out}</div>{table}</figure>'


def ac(d):
    a = d['ac']
    tiles = ''
    for au in a['automations']:
        active = au['status'] == 'Active'
        pill = ('<span class="pill-ok">&#9679; Active</span>' if active else
                '<span class="pill-warn">&#10074;&#10074; Paused</span>' if au['status'] == 'Paused' else '<span class="pill-off">&#9675; Inactive</span>')
        rates = (f'<div class="kv"><span>Open</span><b>{au["open"]:.0f}%</b></div><div class="kv"><span>Click</span><b>{au["click"]:.0f}%</b></div>'
                 if au.get('sends') and au.get('open') is not None else '')
        yd = '—' if au.get('yday') is None else f'{au["yday"]:,}'
        tiles += (f'<div class="tile{" off" if not active else ""}"><div class="tile-h"><b>{e(au["name"])}</b>{pill}</div>'
                  f'<div class="kvs"><div class="kv yd"><span>{e(au.get("ydayLabel", "Yesterday"))}</span><b>{yd}</b></div>'
                  f'<div class="kv"><span>In it now</span><b>{au["now"]:,}</b></div><div class="kv"><span>Entered</span><b>{au["entered"]:,}</b></div>'
                  f'<div class="kv"><span>Sends</span><b>{au["sends"]:,}</b></div>{rates}</div><p>{e(au["note"])}</p></div>')
    rfis = ''
    if a.get('rfis'):
        cells = ''
        for r in a['rfis']:
            n = '—' if r.get('count') is None else f'{r["count"]:,}'
            cells += (f'<div class="rfi"><span>{e(r["name"])}</span><b>{n}</b>'
                      f'<small>{e(r.get("label", "Yesterday"))}</small>'
                      + (f'<a href="{e(r["url"])}"{NT}>{e(r.get("linkText", "Full report in AC"))} &#8599;</a>' if r.get('url') else '')
                      + (f'<p>{e(r["note"])}</p>' if r.get('note') else '') + '</div>')
        rfis = f'<div class="rfis">{cells}</div>'
    mails = ''
    for m in a.get('mailings') or []:
        kv = ''.join(f'<div class="kv{" warn" if len(st) > 3 and st[3] else ""}"><span>{e(st[0])}</span><b>{e(st[1])}</b>'
                     + (f'<small>{e(st[2])}</small>' if len(st) > 2 and st[2] else '') + '</div>' for st in m['stats'])
        links = ''.join(f'<a href="{e(u)}"{NT}>{e(t)} &#8599;</a>' for u, t in ((m.get('report'), m.get('reportText', 'Compare with past emails')), (m.get('url'), m.get('urlText', 'Open in Slate'))) if u)
        mails += (f'<div class="mail"><div class="tile-h"><b>{e(m["title"])}</b><span class="asof">{e(m.get("asOf", ""))}</span></div>'
                  + (f'<p class="msub">{e(m["sub"])}</p>' if m.get('sub') else '')
                  + f'<div class="mkvs">{kv}</div>' + (f'<p>{e(m["note"])}</p>' if m.get('note') else '') + f'<div class="mlinks">{links}</div></div>')
    if mails:
        mails = f'<div class="mails">{mails}</div>'
    ug = a['automations'][0]
    lead = f'<p class="flag">{"<span class=pill-warn>&#9650; Stall</span> " if a.get("stall") else ""}<b>{e(a["lead"])}</b></p>' if a.get('lead') else ''
    sends = ''
    if a.get('sends'):
        sends = ('<figure class="ug"><figcaption>' + e(a.get('sendsCaption', 'Recent sends')) + '</figcaption>'
                 '<table class="sends"><thead><tr><th>Email</th><th>Sends</th><th>Opens</th><th>Clicks</th><th>Bounces</th><th>Unsubs</th></tr></thead><tbody>'
                 + ''.join(f'<tr><td>{e(r[0])}</td>' + ''.join(f'<td>{e(str(v))}</td>' for v in r[1:]) + '</tr>' for r in a['sends'])
                 + '</tbody></table>' + (f'<p class="note">{e(a["sendsNote"])}</p>' if a.get('sendsNote') else '') + '</figure>')
    sched = f'<p class="note">{e(a["scheduled"])}</p>' if a.get('scheduled') else ''
    if not ug.get('emails'):
        flag = f'<p class="flag"><span class="pill-warn">&#9650; Check</span> {e(a["flag"])}</p>' if a.get('flag') else ''
        return f'{lead}{rfis}{bands_block(a)}{mails}{flag}<div class="tiles">{tiles}</div>{sends}{sched}'
    chart = touchpoint_charts(ug['emails'], a['asOf'])
    flag = f'<p class="flag"><span class="pill-warn">&#9650; Check</span> {e(a["flag"])}</p>' if a.get('flag') else ''
    return f'{lead}{rfis}{bands_block(a)}{mails}{flag}<div class="tiles">{tiles}</div>{chart}{sends}{sched}'


def news(d):
    return '<div class="news">' + ''.join(
        f'<article><span class="src">{e(n["source"])} · {e(n["date"])}</span><h3>{link(n["title"], n["url"])}</h3>'
        f'<p>{e(n["summary"])}</p><p class="why">For AU: {e(n["why"])}</p></article>' for n in d['news']) + '</div>'


def deletions(d):
    rows = ''
    for i, dl in enumerate(d['deletions']):
        seed = (f"Help me unsubscribe from {dl['sender']} emails in my personal Gmail. Find the most recent message from {dl['sender']}, "
                "locate its unsubscribe link or List-Unsubscribe address, and either complete the unsubscribe in a browser if one is available "
                "or give me the link to open. Then move that sender's messages in my inbox to Trash, but nothing from real people, receipts, "
                "financial records, or security notices. You can reach my personal Gmail and the web. Done is a short note of what was "
                "unsubscribed and how many threads went to Trash.")
        n = len(dl['threads'])
        rows += (f'<li data-del="{i}"><div class="d-b"><b>{e(dl["sender"])}</b><span>{e(dl["what"])}</span></div>'
                 f'<span class="cnt">{n}</span><div class="d-a"><button type="button" class="btn-sm trash" id="trash-{i}">Move {n} to Trash</button>'
                 f'<a class="btn-sm ghost" href="{e(seed_href(seed))}"{NT}>Unsubscribe</a></div><p class="d-msg" aria-live="polite"></p>'
                 f'{note_box("deletions", slug(dl["sender"]), dl["sender"])}</li>')
    return (f'<ul class="dels">{rows}</ul><p class="note">Move to Trash asks once more before it acts, and Gmail keeps trashed mail for 30 days. '
            'Unsubscribe opens Claude to find the link for you.</p>')


CSS = r'''
/* Layout: two bands. A calm wash band for the day's shape, then a working band of
   sections in one 860px column; the priorities list is the one interactive centerpiece. */
:root{
  --bg:#FCFCFB; --wash:#F6F5F1; --card:#FFFFFF; --ink:#2E2C27; --soft:#5F5E57; --mute:#8E8D84;
  --hair:#E4E3DC; --edge:#DAD9D2; --clay:#C6613F; --clay-h:#AE5133; --on-clay:#FFFFFF;
  --au:#2F6F9F; --fam:#B0761C; --open:#2F6F9F; --click:#B0761C; --ctor:#5E7F4A;
  --ok:#2E7D4F; --ok-bg:#E7F3EC; --warn:#9A5B00; --warn-bg:#FBEFD9; --off:#6B6A63; --off-bg:#EEEDE8;
  --chip:#F1F0EB; --crit:#B3261E; --crit-bg:#FBE9E7;
  --f-display:"Fraunces",Georgia,serif; --f-body:-apple-system,"Segoe UI",system-ui,sans-serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#1A1A19; --wash:#222220; --card:#262624; --ink:#EDEBE4; --soft:#B9B7AE; --mute:#8C8A82;
  --hair:#34332F; --edge:#3B3A36; --clay:#D2704E; --clay-h:#E0805E; --on-clay:#1A1A19;
  --au:#4F93C6; --fam:#B98228; --open:#4F93C6; --click:#B98228; --ctor:#86A86E;
  --ok:#7CC79A; --ok-bg:#1F3328; --warn:#E3B062; --warn-bg:#3A2E18; --off:#A3A19A; --off-bg:#2E2D2A;
  --chip:#2E2D2A; --crit:#F08C82; --crit-bg:#3D2321; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#1A1A19; --wash:#222220; --card:#262624; --ink:#EDEBE4; --soft:#B9B7AE; --mute:#8C8A82;
  --hair:#34332F; --edge:#3B3A36; --clay:#D2704E; --clay-h:#E0805E; --on-clay:#1A1A19;
  --au:#4F93C6; --fam:#B98228; --open:#4F93C6; --click:#B98228; --ctor:#86A86E;
  --ok:#7CC79A; --ok-bg:#1F3328; --warn:#E3B062; --warn-bg:#3A2E18; --off:#A3A19A; --off-bg:#2E2D2A;
  --chip:#2E2D2A; --crit:#F08C82; --crit-bg:#3D2321; color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--f-body)}
a{color:inherit}
.band{padding-inline:16px}
.top{background:var(--wash);border-bottom:1px solid var(--edge)}
.wrap{max-width:860px;margin:0 auto;padding-block:36px 40px}
.date{color:var(--soft);font-size:13px;margin:0 0 8px}
h1{font-family:var(--f-display);font-weight:600;font-size:38px;line-height:1.15;margin:0 0 14px;text-wrap:balance}
.terrain{width:100%;height:auto;display:block}
.ink-line{stroke:var(--ink)} .clay-fill{fill:var(--clay)}
.dot-au{fill:var(--ink)} .dot-fam{fill:var(--fam)}
.acts{display:grid;grid-template-columns:repeat(3,1fr);margin-top:6px}
.act{padding:0 18px;border-left:1px solid var(--hair);min-width:0}.act:first-child{border-left:0;padding-left:0}
.act b{display:block;font-size:13px;margin-bottom:4px}.act p{margin:0;color:var(--soft);font-size:14px}
section{margin-top:40px}
section:first-child{margin-top:0}
h2{font-size:13px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);margin:0 0 14px;display:flex;align-items:baseline;gap:10px}
h2 small{font-weight:400;letter-spacing:0;text-transform:none;color:var(--mute);font-size:13px}
h3{margin:0 0 3px;font-size:15px;font-weight:600;text-wrap:balance}
h3 a{text-decoration:none}h3 a:hover{text-decoration:underline}
p{margin:0}
ol.list{list-style:none;margin:0;padding:0}
ol.list>li{display:flex;gap:14px;padding:12px 0;border-top:1px solid var(--hair)}
ol.list>li:first-child{border-top:0}
.n{color:var(--mute);font-size:14px;min-width:14px;padding-top:2px;font-variant-numeric:tabular-nums}
.li-b{min-width:0;flex:1}.li-b p{color:var(--soft)}
.meta{display:block;font-size:12px;color:var(--mute);margin-bottom:2px}
.b{margin-top:10px!important}
.btn{display:inline-block;background:var(--clay);border:1px solid var(--clay);color:var(--on-clay);border-radius:8px;padding:9px 16px;font:500 13px var(--f-body);text-decoration:none;cursor:pointer}
.btn:hover{background:var(--clay-h);border-color:var(--clay-h)}
.btn-sm{display:inline-flex;align-items:center;gap:6px;border-radius:7px;padding:6px 11px;font:500 12.5px var(--f-body);cursor:pointer;text-decoration:none;border:1px solid var(--edge);background:var(--card);color:var(--ink);white-space:nowrap}
.btn-sm:hover{border-color:var(--ink)}
.btn-sm.primary{background:var(--clay);border-color:var(--clay);color:var(--on-clay)}
.btn-sm.primary:hover{background:var(--clay-h)}
.btn-sm.armed{background:var(--crit);border-color:var(--crit);color:var(--bg)}
.btn-sm.ghost{background:transparent}
button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--au);outline-offset:2px}
.note{color:var(--mute);font-size:13px;margin-top:8px}
/* calendar */
.cal{display:grid;gap:18px}
.cal-day{background:var(--card);border:1px solid var(--hair);border-radius:10px;padding:14px 16px}
.cal-h{display:flex;gap:10px;align-items:baseline;margin-bottom:8px}.cal-h span{color:var(--mute);font-size:13px}
.axis{position:relative;height:16px;margin-left:56px;font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.axis span{position:absolute;transform:translateX(-50%);white-space:nowrap}
.axis span:first-child{transform:none}.axis span:last-child{transform:translateX(-100%)}
.lane{display:flex;align-items:center;gap:8px;margin-top:4px}
.lane-l{width:48px;font-size:12px;color:var(--soft);text-align:right}
.track{position:relative;flex:1;height:18px;background:var(--chip);border-radius:4px}
.blk{position:absolute;top:2px;bottom:2px;border-radius:4px}
.blk-au{background:var(--au)}.blk-family{background:var(--fam)}
.cal-list{list-style:none;margin:12px 0 0;padding:0;display:grid;gap:6px}
.cal-list li{display:grid;grid-template-columns:10px 72px 1fr;gap:8px;align-items:baseline;font-size:14px}
.cal-list .t{color:var(--soft);font-variant-numeric:tabular-nums}
.cal-list .d{min-width:0}.cal-list small{display:block;color:var(--mute);font-size:12.5px}
.cal-list a{text-decoration:none}.cal-list a:hover{text-decoration:underline}
.cal-list .quiet{display:block;color:var(--mute)}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px;vertical-align:baseline}
.sw-au{background:var(--au)}.sw-family{background:var(--fam)}
.allday{list-style:none;margin:10px 0 0;padding:10px 0 0;border-top:1px dashed var(--hair);display:flex;flex-wrap:wrap;gap:6px}
.allday li{font-size:12.5px;background:var(--chip);border-radius:6px;padding:3px 8px}
.allday a{text-decoration:none}
.kate{font-size:12.5px;color:var(--mute);margin-top:8px}
.legend{font-size:12.5px;color:var(--soft);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.legend .sw{margin-left:8px}.legend .sw:first-child{margin-left:0}
/* priorities */
.prio-wrap{background:var(--card);border:1px solid var(--edge);border-radius:12px;padding:6px 6px 12px}
#prio-list{list-style:none;margin:0;padding:0}
.task{display:grid;grid-template-columns:28px 22px 1fr auto;gap:10px;align-items:start;padding:12px 10px;border-radius:9px;border-bottom:1px solid var(--hair);background:var(--card)}
.task:last-child{border-bottom:0}
.task.dragging{box-shadow:0 6px 18px rgba(0,0,0,.18);position:relative;z-index:2;border-bottom-color:transparent}
.grip{width:28px;height:34px;border:0;background:transparent;color:var(--mute);cursor:grab;touch-action:none;border-radius:6px;display:grid;place-items:center}
.grip:hover{background:var(--chip);color:var(--ink)}
.grip:active{cursor:grabbing}
.rk{font:600 15px var(--f-display);color:var(--clay);padding-top:6px;text-align:center;font-variant-numeric:tabular-nums}
.tb{min-width:0;padding-top:4px}
.tb .tt{font-weight:600;text-decoration:none}.tb .tt:hover{text-decoration:underline}
.chips{display:flex;flex-wrap:wrap;gap:5px;margin:5px 0 4px}
.chip{font-size:11.5px;border-radius:5px;padding:1px 7px;background:var(--chip);color:var(--soft)}
.chip.crit{background:var(--crit-bg);color:var(--crit);font-weight:600}
.chip.high{background:var(--warn-bg);color:var(--warn);font-weight:600}
.chip.late{background:var(--crit-bg);color:var(--crit)}
.chip.soon{background:var(--warn-bg);color:var(--warn)}
.chip.mine{background:var(--ok-bg);color:var(--ok)}
.why{font-size:13.5px;color:var(--soft)}
.ta{display:flex;gap:6px;align-items:center;padding-top:2px}
.mv{width:30px;height:30px;padding:0;justify-content:center}
.add{display:flex;gap:8px;margin:10px 10px 0}
.add input{flex:1;min-width:0;font:15px var(--f-body);padding:8px 11px;border:1px solid var(--edge);border-radius:8px;background:var(--bg);color:var(--ink)}
.prio-foot{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin:10px 10px 0;font-size:12.5px;color:var(--mute)}
#prio-done{list-style:none;margin:14px 0 0;padding:0;display:grid;gap:6px}
#prio-done li{display:flex;align-items:center;gap:10px;font-size:14px;color:var(--soft);padding:6px 10px;border-radius:8px;background:var(--ok-bg)}
#prio-done li .x{flex:1;min-width:0;text-decoration:line-through}
#prio-done .check{color:var(--ok);font-weight:700}
.toast{position:fixed;left:50%;bottom:calc(18px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:9px 14px;border-radius:8px;font-size:13.5px;max-width:min(92vw,520px);z-index:9}
/* update boxes */
.nb{margin-top:8px}
.nb textarea{display:block;width:100%;resize:none;overflow:hidden;font:14px/1.45 var(--f-body);color:var(--ink);background:var(--bg);border:1px solid var(--hair);border-radius:8px;padding:6px 10px;min-height:32px}
.nb textarea::placeholder{color:var(--mute)}
.nb textarea:focus{border-color:var(--edge);outline:2px solid var(--au);outline-offset:1px}
.nb-a{display:none;gap:6px;align-items:center;flex-wrap:wrap;margin-top:6px}
.nb.has .nb-a,.nb:focus-within .nb-a{display:flex}
.nb-msg{font-size:12.5px;color:var(--mute)}
.agenda{margin-top:6px!important;font-size:13px}
.agenda a{color:var(--au);text-decoration:none;font-weight:500}.agenda a:hover{text-decoration:underline}
a.nudge{text-decoration:none;cursor:pointer}a.nudge:hover{background:var(--warn);color:var(--bg)}
.kv.yd b{color:var(--ink)}
/* waiting */
.wait{list-style:none;margin:0;padding:0;display:grid;gap:14px}
.w-h{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-weight:600}
.w-h a{text-decoration:none}.w-h a:hover{text-decoration:underline}
.w-bar{display:flex;align-items:center;gap:10px;margin:6px 0 4px}
.w-bar span{display:block;height:10px;border-radius:0 4px 4px 0;background:var(--soft);min-width:4px}
.w-bar b{font-size:12.5px;font-weight:500;color:var(--soft);white-space:nowrap;font-variant-numeric:tabular-nums}
.wait p{font-size:13.5px;color:var(--soft)}
.pill-warn,.pill-ok,.pill-off{font-size:11.5px;font-weight:600;border-radius:999px;padding:1px 8px;white-space:nowrap}
.pill-warn{background:var(--warn-bg);color:var(--warn)}
.pill-ok{background:var(--ok-bg);color:var(--ok)}
.pill-off{background:var(--off-bg);color:var(--off)}
/* yesterday */
.yday{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.yday li{display:grid;grid-template-columns:76px 1fr;gap:10px;align-items:baseline;font-size:14px;color:var(--soft)}
.tag{font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--mute);border:1px solid var(--hair);border-radius:5px;padding:1px 6px;text-align:center}
/* activecampaign */
.flag{font-size:14px;color:var(--soft);margin-bottom:14px}
.mails{display:grid;gap:12px;margin:0 0 14px}
.mail{background:var(--card);border:1px solid var(--hair);border-radius:10px;padding:12px 14px;min-width:0}
.mail .asof{font-size:11.5px;color:var(--mute)}
.mail .msub{font-size:13px;color:var(--soft);margin:0 0 8px}
.mkvs{display:grid;grid-template-columns:repeat(5,1fr);gap:8px 10px;margin-bottom:8px}
.mkvs .kv small{display:block;font-size:11px;color:var(--mute)}
.mkvs .kv.warn b{color:var(--clay,#b4471f)}
.mail p{font-size:13px;color:var(--soft);margin:0 0 6px}
.mlinks{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12.5px}
.rfis{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:0 0 14px}
.rfi{background:var(--card);border:1px solid var(--hair);border-radius:10px;padding:12px 14px;display:grid;grid-template-columns:1fr auto;gap:2px 10px;align-items:baseline;min-width:0}
.rfi span{font-size:13px;font-weight:600}
.rfi b{font-size:26px;font-variant-numeric:tabular-nums;grid-row:span 2;align-self:center}
.rfi small{font-size:11.5px;color:var(--mute)}
.rfi a{grid-column:1/-1;font-size:12.5px;margin-top:6px}
.rfi p{grid-column:1/-1;font-size:12.5px;color:var(--soft);margin:4px 0 0}
.ug.bands{margin:0 0 14px}.bands .sends{min-width:360px}.bands figcaption a{font-weight:400;font-size:12.5px;margin-left:8px}.sends tr.tot td{font-weight:600;border-top:1px solid var(--edge)}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.tile{background:var(--card);border:1px solid var(--hair);border-radius:10px;padding:12px 14px;min-width:0}
.tile.off{background:transparent;border-style:dashed}
.tile-h{display:flex;justify-content:space-between;gap:8px;align-items:baseline;margin-bottom:8px}
.kvs{display:grid;grid-template-columns:repeat(4,1fr);gap:8px 6px;margin-bottom:8px}
.kv span{display:block;font-size:11.5px;color:var(--mute)}
.kv b{font-size:16px;font-variant-numeric:tabular-nums}
.kv.wide{grid-column:span 2}
.tile p{font-size:13px;color:var(--soft)}
.ug{margin:18px 0 0;background:var(--card);border:1px solid var(--hair);border-radius:10px;padding:14px 16px;overflow-x:auto}
.ug figcaption{font-weight:600;margin-bottom:10px}.ug figcaption small{display:block;font-weight:400;color:var(--mute);font-size:12.5px}
.bar-row{display:grid;grid-template-columns:minmax(150px,1.3fr) 1fr 1fr;gap:12px;align-items:center;padding:4px 0;min-width:520px}
.bar-row.three{grid-template-columns:minmax(150px,1.3fr) 1fr 1fr 1fr;min-width:640px}
.bar-row.head{font-size:12px;color:var(--soft);border-bottom:1px solid var(--hair);padding-bottom:6px;margin-bottom:2px}
.bar-row.head small{color:var(--mute)}
.bar-row.low{opacity:.55}
.bl{font-size:13px;min-width:0}.bl small{display:block;color:var(--mute);font-size:11.5px;font-variant-numeric:tabular-nums}
.bt{display:flex;align-items:center;gap:6px;background:linear-gradient(to right,var(--hair) 1px,transparent 1px) 0 0/50% 100%;}
.bo,.bc,.bk{display:block;height:12px;border-radius:0 4px 4px 0;min-width:2px}
.bo{background:var(--open)}.bc{background:var(--click)}.bk{background:var(--ctor)}
.bt em{font-style:normal;font-size:12px;color:var(--soft);font-variant-numeric:tabular-nums}
.bar-row:hover:not(.head){background:var(--chip)}
.ug.lines{overflow:visible}
.lcs{display:grid;gap:22px}
.lc-h{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:4px 12px;font-size:14px;margin-bottom:8px}
.lc-h span{color:var(--soft);font-variant-numeric:tabular-nums;font-size:13px}.lc-h small{color:var(--mute)}
.plot{position:relative;height:170px;margin:0 14px 24px 40px}
.plot svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.plot .g line{stroke:var(--hair);stroke-width:1;vector-effect:non-scaling-stroke}
.plot .xh{stroke:var(--edge);stroke-width:1;vector-effect:non-scaling-stroke;opacity:0}
.plot.on .xh{opacity:1}
.plot .ln{fill:none;stroke:var(--s);stroke-width:2;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}
.yt,.xt{position:absolute;font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums;white-space:nowrap}
.yt{right:calc(100% + 8px);transform:translateY(-50%)}.xt{top:calc(100% + 6px);transform:translateX(-50%)}
.pt{position:absolute;width:9px;height:9px;margin:-4.5px 0 0 -4.5px;border-radius:50%;background:var(--s);box-shadow:0 0 0 2px var(--card);outline:none}
.pt.br{width:7px;height:7px;margin:-3.5px 0 0 -3.5px;opacity:.5;box-shadow:none}
.pt.br.lo{background:var(--card);border:1.5px solid var(--s);opacity:.75}
.pt.hot{transform:scale(1.5);opacity:1;z-index:2}
.dl{position:absolute;transform:translate(6px,-150%);font-size:11.5px;font-weight:600;color:var(--ink);font-variant-numeric:tabular-nums;pointer-events:none}
.dl.end{transform:translate(-100%,-150%)}
.tip{position:absolute;z-index:5;pointer-events:none;background:var(--ink);color:var(--card);border-radius:6px;padding:6px 9px;font-size:12px;line-height:1.35;white-space:nowrap;transform:translate(-50%,calc(-100% - 10px))}
.tip b{display:block;font-weight:600}.tip span{opacity:.8}
.lc.o{--s:var(--open)}.lc.c{--s:var(--click)}.lc.k{--s:var(--ctor)}
.lc-tbl{margin-top:4px}.lc-tbl summary{cursor:pointer;font-size:13px;color:var(--soft);padding:4px 0}
.lc-tbl .tbl-scroll{overflow-x:auto;margin-top:6px}.lc-tbl tr.low td{opacity:.55}
.sends{width:100%;border-collapse:collapse;font-size:13px;min-width:520px}
.sends th{text-align:left;font-weight:500;color:var(--mute);font-size:12px;border-bottom:1px solid var(--hair);padding:4px 6px}
.sends td{padding:5px 6px;border-bottom:1px solid var(--hair);color:var(--soft);font-variant-numeric:tabular-nums}
.sends td:first-child{color:var(--ink)}
/* news */
.news{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.news article{border-top:2px solid var(--ink);padding-top:10px;min-width:0}
.src{font-size:12px;color:var(--mute)}
.news p{font-size:14px;color:var(--soft);margin-top:4px}.news .why{color:var(--ink)}
/* deletions */
.dels{list-style:none;margin:0;padding:0;display:grid;gap:0}
.dels li{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:center;padding:9px 0;border-top:1px solid var(--hair)}
.dels li:first-child{border-top:0}
.d-b{min-width:0}.d-b b{display:block;font-size:14px}.d-b span{font-size:12.5px;color:var(--mute)}
.cnt{font:600 13px var(--f-body);background:var(--chip);border-radius:999px;min-width:26px;text-align:center;padding:2px 8px;font-variant-numeric:tabular-nums}
.d-a{display:flex;gap:6px}
.d-msg{grid-column:1/-1;font-size:12.5px;color:var(--soft)}
.d-msg:empty{display:none}
.dels li.gone .d-b{opacity:.5;text-decoration:line-through}
.two{display:grid;grid-template-columns:1fr 1fr;gap:28px}
.two>div{min-width:0}
@media (max-width:640px){
  h1{font-size:29px}
  .acts{grid-template-columns:1fr}.act{border-left:0;border-top:1px solid var(--hair);padding:10px 0}.act:first-child{border-top:0}
  .news,.two{grid-template-columns:1fr}
  .task{grid-template-columns:26px 18px 1fr;}
  .ta{grid-column:2/-1}
  .dels li{grid-template-columns:1fr auto}
  .d-a{grid-column:1/-1}
  .yday li{grid-template-columns:1fr}.tag{justify-self:start}
  .kvs{grid-template-columns:repeat(2,1fr)}
  .mkvs{grid-template-columns:repeat(2,1fr)}
  .task .nb{grid-column:1/-1}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
'''

JS = r'''
(function(){
  const D = JSON.parse(document.getElementById('brief-data').textContent);
  const $ = s => document.querySelector(s);
  const listEl = $('#prio-list'), doneEl = $('#prio-done'), statusEl = $('#prio-status');
  let db = null, mcp = null, tasks = [], dragging = false, toastT = null;

  function toast(msg){ let t=$('.toast'); if(!t){t=document.createElement('div');t.className='toast';t.setAttribute('role','status');document.body.appendChild(t);} t.textContent=msg; t.hidden=false; clearTimeout(toastT); toastT=setTimeout(()=>{t.hidden=true},4200); }
  function esc(s){ const d=document.createElement('div'); d.textContent=s==null?'':String(s); return d.innerHTML; }
  function dayDiff(iso){ if(!iso) return null; const a=new Date(D.date+'T12:00:00'), b=new Date(iso+'T12:00:00'); return Math.round((b-a)/864e5); }
  function dueChip(iso){ const n=dayDiff(iso); if(n===null) return ''; const wd=new Date(iso+'T12:00:00').toLocaleDateString('en-US',{weekday:'short'});
    if(n<0) return '<span class="chip late">'+(-n)+(n===-1?' day':' days')+' late</span>';
    if(n===0) return '<span class="chip late">due today</span>';
    if(n===1) return '<span class="chip soon">due tomorrow</span>';
    if(n<=3) return '<span class="chip soon">due '+wd+'</span>';
    return '<span class="chip">due '+wd+'</span>'; }
  function prChip(p){ if(!p) return ''; const c=p==='Critical'?'crit':(p==='High'?'high':''); return '<span class="chip '+c+'">'+esc(p)+'</span>'; }
  const visible = () => tasks.filter(t=>t.active!==false && !t.done).sort((a,b)=>(a.rank??999)-(b.rank??999));
  const doneToday = () => tasks.filter(t=>t.done && t.doneDay===D.date);
  const find = id => tasks.find(t=>t.id===id);
  const GRIP = '<svg width="12" height="18" viewBox="0 0 12 18" aria-hidden="true"><g fill="currentColor"><circle cx="3" cy="3" r="1.6"/><circle cx="9" cy="3" r="1.6"/><circle cx="3" cy="9" r="1.6"/><circle cx="9" cy="9" r="1.6"/><circle cx="3" cy="15" r="1.6"/><circle cx="9" cy="15" r="1.6"/></g></svg>';

  function render(){
    const v = visible();
    listEl.innerHTML = v.map((t,i)=>{
      const title = t.url ? '<a class="tt" href="'+esc(t.url)+'" target="_blank" rel="noopener">'+esc(t.title)+'</a>' : '<span class="tt">'+esc(t.title)+'</span>';
      const chips = (t.source==='custom' ? '<span class="chip mine">Your task</span>' : '') + prChip(t.priority) + (t.status?'<span class="chip">'+esc(t.status)+'</span>':'') + dueChip(t.due) + (t.board?'<span class="chip">'+esc(t.board)+'</span>':'');
      return '<li class="task" data-id="'+esc(t.id)+'"><button type="button" class="grip" aria-label="Drag to reorder '+esc(t.title)+'">'+GRIP+'</button>'+
        '<span class="rk">'+(i+1)+'</span><div class="tb">'+title+'<div class="chips">'+chips+'</div>'+(t.why?'<p class="why">'+esc(t.why)+'</p>':'')+noteBox('priorities',t.id,t.title)+'</div>'+
        '<div class="ta"><button type="button" class="btn-sm mv up" aria-label="Move up"'+(i===0?' disabled':'')+'>&uarr;</button><button type="button" class="btn-sm mv dn" aria-label="Move down"'+(i===v.length-1?' disabled':'')+'>&darr;</button>'+
        '<button type="button" class="btn-sm primary done">&#10003; Done</button></div></li>'; }).join('') || '<li class="task"><span></span><span></span><p class="why">Nothing open. Add a task below.</p></li>';
    restoreBoxes(listEl);
    const d = doneToday();
    doneEl.innerHTML = d.map(t=>'<li data-id="'+esc(t.id)+'"><span class="check">&#10003;</span><span class="x">'+esc(t.title)+'</span><button type="button" class="btn-sm ghost undo">Undo</button></li>').join('');
  }
  function renumber(){ [...listEl.children].forEach((li,i)=>{ const r=li.querySelector('.rk'); if(r) r.textContent=i+1; }); }

  async function save(t){ if(!db) return; const {id,...body}=t; try{ await db.doc('tasks/'+id).set(body); }catch(err){ statusEl.textContent = err && err.code==='quota_exceeded' ? 'The task store is full; remove some done tasks.' : 'Could not save that change. It will be lost on reload.'; } }
  async function persistOrder(ids){
    const changed=[]; ids.forEach((id,i)=>{ const t=find(id); if(t && t.rank!==i+1){ t.rank=i+1; t.userRanked=true; changed.push(t);} });
    render(); for(const t of changed){ await save(t); }
    if(changed.length) toast('Order saved.');
  }
  function mcpMsg(err, server){
    const c = err && err.code;
    if(c==='needs_reauth') return 'Reconnect '+server+' in claude.ai Settings → Connectors, then try again.';
    if(c==='server_not_connected') return 'Add '+server+' in claude.ai Settings → Connectors to do this from the page.';
    if(c==='not_in_manifest'||c==='approval_required') return server+' is not allowed for this page. Turn it on in the page’s permissions and try again.';
    if(c==='blocked_by_policy') return 'Your organization blocks this '+server+' action.';
    if(c==='tool_error') return server+' refused the change: '+(err.message||'no details');
    if(c==='server_unavailable') return server+' did not answer. Check it before trying again; the change may have gone through.';
    return 'Could not reach '+server+' ('+(c||'unknown')+').';
  }
  async function setMonday(t,label){
    if(!mcp) return 'monday.com is not reachable from this view, so the item there is unchanged.';
    try{ await mcp.callTool('monday.com','change_item_column_values',{boardId:Number(t.boardId),itemId:Number(t.id),columnValues:JSON.stringify({[t.statusCol]:{label}})}); return true; }
    catch(err){ return mcpMsg(err,'monday.com'); }
  }
  async function markDone(id){
    const t=find(id); if(!t) return; t.done=true; t.doneDay=D.date; t.prevStatus=t.status||''; t.mondaySynced=false; render();
    let msg='Marked done.';
    if(t.source!=='custom' && t.boardId && t.statusCol){ const r=await setMonday(t,'Done'); if(r===true){ t.mondaySynced=true; msg='Marked done here and in monday.'; } else msg='Marked done here. '+r; }
    await save(t); toast(msg);
  }
  async function undo(id){
    const t=find(id); if(!t) return; t.done=false; t.doneDay=''; render(); let msg='Back on the list.';
    if(t.mondaySynced && t.prevStatus){ const r=await setMonday(t,t.prevStatus); msg = r===true ? 'Back on the list; monday status restored to '+t.prevStatus+'.' : 'Back on the list. '+r; t.mondaySynced=false; }
    await save(t); toast(msg);
  }
  async function addTask(title){
    title=title.trim(); if(!title) return;
    const rank=Math.max(0,...visible().map(t=>t.rank||0))+1;
    const t={id:'c-'+Date.now().toString(36)+Math.random().toString(36).slice(2,6),title,source:'custom',active:true,done:false,rank,created:D.date,why:'',userRanked:true};
    tasks.push(t); render(); await save(t); toast('Added to your priorities.');
  }

  listEl.addEventListener('click', e=>{
    const li=e.target.closest('li.task'); if(!li||!li.dataset.id) return; const id=li.dataset.id;
    if(e.target.closest('.done')) return markDone(id);
    const ids=visible().map(t=>t.id), i=ids.indexOf(id);
    if(e.target.closest('.up') && i>0){ [ids[i-1],ids[i]]=[ids[i],ids[i-1]]; persistOrder(ids); }
    if(e.target.closest('.dn') && i<ids.length-1){ [ids[i+1],ids[i]]=[ids[i],ids[i+1]]; persistOrder(ids); }
  });
  doneEl.addEventListener('click', e=>{ const li=e.target.closest('li'); if(li && e.target.closest('.undo')) undo(li.dataset.id); });
  listEl.addEventListener('pointerdown', e=>{
    const grip=e.target.closest('.grip'); if(!grip) return; e.preventDefault();
    const li=grip.closest('li'); dragging=true; li.classList.add('dragging');
    try{ grip.setPointerCapture(e.pointerId); }catch(_){}
    const move=ev=>{ const y=ev.clientY; let before=null; for(const it of listEl.children){ if(it===li) continue; const r=it.getBoundingClientRect(); if(y<r.top+r.height/2){ before=it; break; } } if(before!==li.nextSibling) { listEl.insertBefore(li,before); renumber(); } };
    const up=()=>{ grip.removeEventListener('pointermove',move); grip.removeEventListener('pointerup',up); grip.removeEventListener('pointercancel',up); li.classList.remove('dragging'); dragging=false; persistOrder([...listEl.children].map(x=>x.dataset.id).filter(Boolean)); };
    grip.addEventListener('pointermove',move); grip.addEventListener('pointerup',up); grip.addEventListener('pointercancel',up);
  });
  $('#add-form').addEventListener('submit', e=>{ e.preventDefault(); const inp=$('#new-task'); addTask(inp.value); inp.value=''; });

  // Mail: move a sender's threads to Trash (two-step confirm), unsubscribe goes through Claude.
  document.querySelectorAll('.trash').forEach(b=>{
    b.addEventListener('click', async ()=>{
      const li=b.closest('li'), i=Number(li.dataset.del), del=D.deletions[i], msg=li.querySelector('.d-msg');
      if(!b.classList.contains('armed')){ b.classList.add('armed'); b.dataset.label=b.textContent; b.textContent='Confirm: Trash '+del.threads.length; setTimeout(()=>{ if(b.classList.contains('armed')){ b.classList.remove('armed'); b.textContent=b.dataset.label; } },6000); return; }
      b.classList.remove('armed'); b.disabled=true; b.textContent='Moving…';
      if(!mcp){ msg.textContent='Gmail is not reachable from this view. Use Unsubscribe to have Claude do it.'; b.disabled=false; b.textContent=b.dataset.label; return; }
      let ok=0, err=null;
      for(const id of del.threads){ try{ await mcp.callTool('Gmail','trash_thread',{threadId:id}); ok++; }catch(x){ err=x; break; } }
      if(err){ msg.textContent=(ok?ok+' moved to Trash. ':'')+mcpMsg(err,'Gmail'); b.disabled=false; b.textContent=b.dataset.label; }
      else { msg.textContent=ok+' moved to Trash.'; b.textContent='In Trash'; li.classList.add('gone'); }
    });
  });

  // Update boxes: "Save for tomorrow" stores a note the next morning run reads and applies;
  // "Ask Claude now" opens a new Claude chat with the item and Brent's words.
  const SEC = {meetings:'Meetings today', needs:'Needs attention', priorities:'Today\u2019s priorities', missed:'Missed in monday',
    replies:'AU email, replies owed', waiting:'Waiting on others', pmail:'Personal email, important', deletions:'Personal email, suggested deletions', hand:'Could hand to Claude'};
  const drafts = {}, saved = {};
  const noteId = (sec,key) => (D.date+'_'+sec+'_'+key).replace(/[^A-Za-z0-9_-]/g,'-').slice(0,120);
  function noteBox(sec,key,title){
    return '<div class="nb" data-sec="'+esc(sec)+'" data-key="'+esc(key)+'" data-title="'+esc(title)+'"><textarea rows="1" aria-label="Update or instruction about '+esc(title)+'" placeholder="Update, or tell Claude what to do\u2026"></textarea>'+
      '<div class="nb-a"><button type="button" class="btn-sm nb-save">Save for tomorrow</button><a class="btn-sm primary nb-ask" href="#" target="_blank" rel="noopener">Ask Claude now</a><span class="nb-msg" aria-live="polite"></span></div></div>';
  }
  function seedFor(box,text){
    const sec=SEC[box.dataset.sec]||box.dataset.sec;
    return 'From my morning brief for '+D.dayDate+', the item I\u2019ve titled "'+box.dataset.title+'" under '+sec+'. My note: '+text+
      '\n\nFind this item\u2019s details in my claude-vault (Daily/'+D.date+'.md and Inbox.md) and in my connected tools, then do what my note asks. '+
      'Draft any message rather than sending it unless my note says to send. Done is the action finished, or a draft ready for me to review.';
  }
  const askHref = (box,text) => 'https://claude.ai/new?q='+encodeURIComponent(seedFor(box,text))+'&surface=cowork&composer=mini';
  function grow(ta){ ta.style.height='auto'; ta.style.height=Math.min(ta.scrollHeight,180)+'px'; }
  function boxState(box){
    const ta=box.querySelector('textarea'), id=noteId(box.dataset.sec,box.dataset.key), text=ta.value.trim();
    box.querySelector('.nb-ask').href = text ? askHref(box,text) : '#';
    box.classList.toggle('has', !!text);
    const msg=box.querySelector('.nb-msg');
    if(saved[id] && saved[id]===text) msg.textContent='Saved. Tomorrow\u2019s brief will pick it up.';
    else if(saved[id]) msg.textContent='Edited since you saved.';
    else msg.textContent='';
  }
  function restoreBoxes(root){
    (root||document).querySelectorAll('.nb').forEach(box=>{
      const id=noteId(box.dataset.sec,box.dataset.key), ta=box.querySelector('textarea');
      const v = drafts[id]!=null ? drafts[id] : (saved[id]||'');
      if(ta.value!==v){ ta.value=v; grow(ta); }
      boxState(box);
    });
  }
  async function saveNote(box, status){
    const ta=box.querySelector('textarea'), text=ta.value.trim(), msg=box.querySelector('.nb-msg'), id=noteId(box.dataset.sec,box.dataset.key);
    if(!text){ msg.textContent='Type an update first.'; return false; }
    if(!db){ msg.textContent='Saving needs this page open on claude.ai.'; return false; }
    try{
      await db.doc('notes/'+id).set({date:D.date, section:box.dataset.sec, key:box.dataset.key, title:box.dataset.title, text, status, savedAt:new Date().toISOString()});
      saved[id]=text; boxState(box);
      if(status==='asked') msg.textContent='Opened in Claude, and saved for tomorrow.';
      return true;
    }catch(err){ msg.textContent = err && err.code==='quota_exceeded' ? 'The note store is full.' : 'Could not save this note.'; return false; }
  }
  document.addEventListener('input', ev=>{
    const ta=ev.target.closest('.nb textarea'); if(!ta) return; const box=ta.closest('.nb');
    drafts[noteId(box.dataset.sec,box.dataset.key)]=ta.value; grow(ta); boxState(box);
  });
  document.addEventListener('click', ev=>{
    const sv=ev.target.closest('.nb-save'); if(sv){ saveNote(sv.closest('.nb'),'new'); return; }
    const ask=ev.target.closest('.nb-ask'); if(!ask) return;
    const box=ask.closest('.nb');
    if(!box.querySelector('textarea').value.trim()){ ev.preventDefault(); box.querySelector('.nb-msg').textContent='Type what you want Claude to do first.'; return; }
    saveNote(box,'asked');
  });
  restoreBoxes();

  // Start from today's list in the page; the store replaces it once it answers.
  tasks = D.tasks.map(t=>Object.assign({source:'monday',active:true,done:false},t));
  render();
  statusEl.textContent='Connecting to your saved order…';
  const C = window.claude;
  if(!C || !C.use){ statusEl.textContent='Open this page on claude.ai to save your order and done tasks.'; return; }
  C.use('mcp').then(m=>{ mcp=m; }).catch(()=>{});
  C.use('db').then(d=>{
    db=d; if(!db){ statusEl.textContent='Saving is off in this view, so changes last until you reload.'; return; }
    statusEl.textContent='Your order and done tasks are saved.';
    db.collection('notes').onSnapshot(snap=>{
      snap.docs.forEach(x=>{ const v=x.data(); if(v && v.date===D.date) saved[x.id]=v.text||''; });
      restoreBoxes();
    }, ()=>{});
    db.collection('tasks').onSnapshot(snap=>{
      if(snap.empty) return;
      tasks = snap.docs.map(s=>Object.assign({id:s.id}, s.data()));
      if(!dragging) render();
    }, err=>{ statusEl.textContent = 'Saved order is unavailable right now ('+err.code+').'; });
  }).catch(()=>{ statusEl.textContent='Saving is off in this view, so changes last until you reload.'; });
})();
'''



LC_JS = r"""
(function(){
  document.querySelectorAll('.plot').forEach(function(plot){
    var tip = plot.querySelector('.tip'), xh = plot.querySelector('.xh'), pts = [].slice.call(plot.querySelectorAll('.pt')), cur = null;
    function show(p){
      if(cur) cur.classList.remove('hot');
      cur = p; p.classList.add('hot');
      var pr = plot.getBoundingClientRect(), r = p.getBoundingClientRect();
      var x = r.left + r.width/2 - pr.left, y = r.top + r.height/2 - pr.top;
      tip.innerHTML = '';
      var b = document.createElement('b'); b.textContent = p.dataset.n; tip.appendChild(b);
      var v = document.createElement('div'); v.textContent = p.dataset.v; tip.appendChild(v);
      var s = document.createElement('span'); s.textContent = p.dataset.s + ' · ' + p.dataset.t; tip.appendChild(s);
      tip.hidden = false;
      var w = tip.offsetWidth, left = Math.max(w/2 - 40, Math.min(x, pr.width - w/2 + 14));
      tip.style.left = left + 'px'; tip.style.top = y + 'px';
      var pct = x / pr.width * 100; xh.setAttribute('x1', pct); xh.setAttribute('x2', pct);
      plot.classList.add('on');
    }
    function hide(){ if(cur) cur.classList.remove('hot'); cur = null; tip.hidden = true; plot.classList.remove('on'); }
    function nearest(ev){
      var best = null, bd = 28;
      pts.forEach(function(p){ var r = p.getBoundingClientRect(); var d = Math.hypot(r.left + r.width/2 - ev.clientX, r.top + r.height/2 - ev.clientY); if(d < bd){ bd = d; best = p; } });
      return best;
    }
    plot.addEventListener('pointermove', function(ev){ var p = nearest(ev); if(p){ if(p !== cur) show(p); } else hide(); });
    plot.addEventListener('pointerdown', function(ev){ var p = nearest(ev); if(p) show(p); else hide(); });
    plot.addEventListener('pointerleave', function(ev){ if(ev.pointerType === 'mouse') hide(); });
    pts.forEach(function(p){ p.addEventListener('focus', function(){ show(p); }); p.addEventListener('blur', hide); });
  });
})();
"""

def build(d):
    f64 = font_b64()
    font_css = (f'@font-face{{font-family:"Fraunces";src:url(data:font/woff2;base64,{f64}) format("woff2");font-weight:600;font-style:normal}}' if f64 else '')
    acts = ''.join(f'<div class="act"><b>{e(a["time"])}</b><p>{e(a["text"])}</p></div>' for a in d['acts'])
    js_data = {'date': d['date'], 'tasks': d['tasks'], 'deletions': d['deletions'], 'dayDate': d['dayDate']}
    data_json = json.dumps(js_data).replace('</', '<\\/')
    fam_today = d['days'][0]
    pmail_html = items(d['pmail'], 'pmail')
    secs = []
    if d.get('weekly'):
        secs.append(f'<section><h2>{e(d["weekly"]["title"])}</h2>{d["weekly"]["html"]}</section>')
    secs.append(f'<section><h2>{"Today and tomorrow" if len(d["days"]) > 1 else "Today"}</h2>{calendar(d)}</section>')
    if d.get('meetings'):
        secs.append(f'<section><h2>Meetings today</h2>{items(d["meetings"], "meetings")}</section>')
    secs.append(f'<section><h2>Needs attention</h2>{items(d["needs"], "needs")}</section>')
    secs.append(f'''<section id="priorities"><h2>Today’s priorities <small>drag to reorder, or add your own</small></h2>
<div class="prio-wrap"><ol id="prio-list" aria-label="Priorities, in order"></ol>
<form class="add" id="add-form" autocomplete="off"><label for="new-task" class="sr" hidden>New task</label>
<input id="new-task" name="new-task" placeholder="Add a task that isn’t listed…" maxlength="160"><button class="btn-sm primary" type="submit">Add</button></form>
<div class="prio-foot"><span id="prio-status" aria-live="polite"></span><span>Done also sets the item to Done in monday.</span></div></div>
<ul id="prio-done" aria-label="Done today"></ul><p class="note">{e(d.get("goalsNote", ""))}</p></section>''')
    secs.append(f'<section><div class="two"><div><h2>Missed in monday</h2>{items(d["missed"], "missed")}</div><div><h2>Resolved</h2>{items(d["resolved"])}</div></div></section>')
    if d.get('replies'):
        secs.append(f'<section><h2>AU email, replies owed</h2>{items(d["replies"], "replies")}</section>')
    secs.append(f'<section><h2>Waiting on others</h2>{waiting(d)}</section>')
    secs.append(f'<section><h2>Yesterday’s work</h2>{yesterday(d)}</section>')
    secs.append(f'<section><h2>ActiveCampaign <small>ENR nurture automations</small></h2>{ac(d)}</section>')
    secs.append(f'<section><h2>Higher ed news</h2>{news(d)}</section>')
    secs.append(f'<section><h2>Personal email, important</h2>{pmail_html}</section>')
    secs.append(f'<section><h2>Personal email, suggested deletions</h2>{deletions(d)}</section>')
    secs.append(f'<section><h2>Could hand to Claude</h2>{items(d["hand"], "hand")}</section>')
    return f'''<title>Morning Brief</title>
<base target="_blank">
<style>{font_css}{CSS}</style>
<div class="band top"><div class="wrap">
<p class="date">{e(d["dayDate"])}</p>
<h1>{e(d["headline"])}</h1>
{terrain(d)}
<div class="acts">{acts}</div>
</div></div>
<div class="band"><div class="wrap">
{"".join(secs)}
</div></div>
<script type="application/json" id="brief-data">{data_json}</script>
<script>{JS}</script>
<script>{LC_JS}</script>'''


if __name__ == '__main__':
    data = json.loads(pathlib.Path(sys.argv[1]).read_text())
    body = build(data)
    pathlib.Path(sys.argv[2]).write_text(body)
    if '--preview' in sys.argv:
        p = sys.argv[sys.argv.index('--preview') + 1]
        pathlib.Path(p).write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + body + '</body></html>')
    print('built', len(body))
