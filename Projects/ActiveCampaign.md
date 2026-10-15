# ActiveCampaign

AU's email/CRM infrastructure build-out.

## Built so far
- 14 lists in four streams: Prospective Students, Alumni, Advancement, Institutional
- Deal-based admissions pipeline with six automations triggered by field changes
- Universal throttle: a weekly send counter plus the "Has been sent" condition
- AC-to-Slate integration via Reworkflow and Zapier
- Alumni templates rebuilt for the Stripo drag-and-drop editor
- Contact cleanup of ~120K contacts, tiered by engagement
- SMS consent compliance (10DLC registration, privacy policy, form fixes)
- UG inquiry nurture sequence running alongside one-time broadcasts ([[UG Inquiry Sequence]])
- Recruiter assignment automation (124), audited and fixed 10/15 ([[Recruiter Assignment]])

## Slate sync and scoring
- Site tracking script is live on the RFI form (9/30) and works for new contacts (confirmed 10/6). Bailey Raffield (Reworkflow) is adding it to the visit forms the week of 10/12.
- Lead scoring bug: Visit Scheduled Date and RFI Date rules don't calculate. AC support escalated to engineering 9/17; no fix as of 9/29.
- Program Finder fills score 15 points, behind RFI. Revisit after site tracking is fixed.
- Send scoring bands (high/medium/low) to Slate instead of raw scores (10/7).
- VIP status from the Program Finder isn't reaching Slate; [[Tracy Lantz|TL]] is building a query to tag them in AC.
- Program Finder creates duplicate records in Slate; the degree-type field was showing codes (9/29).
- Slate records should link to the AC contact; Tracy has an AC seat.
- Events: Tracy requires campus events and registrations be built in Slate (ticket), not AC (10/13). Brent wants AC registration/attendance to flow into Slate; meeting requested.

## Email build rules
- Match AC's own skeleton: one `es-wrapper`, few stripes, all tables (no divs), no DOCTYPE/html/head/body
- Explicit inline font styles on every `<p>`
- Recolor only below "END CONFIG STYLES" in the CSS box

## Open questions
- What share of funnel contacts has site-tracking data?
