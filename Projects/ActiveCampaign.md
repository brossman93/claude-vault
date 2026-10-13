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
- UG inquiry nurture sequence running alongside one-time broadcasts

## Email build rules
- Match AC's own skeleton: one `es-wrapper`, few stripes, all tables (no divs), no DOCTYPE/html/head/body
- Explicit inline font styles on every `<p>`
- Recolor only below "END CONFIG STYLES" in the CSS box

## Open questions
