# Recruiter Assignment

AC automation 124, "ENR: update - Assigned Recruiter", sets each contact's admission counselor fields. Source of truth for territories: the Counselor Recruiter Assignments spreadsheet (with FA, SMS, email, phone). Part of [[ActiveCampaign]].

## How it works
- Multi-entry; fires from three start triggers.
- Sets four dropdown fields: Recruiter Full Name (445), Recruiter Email (446), Recruiter First Name (447), Recruiter Phone (450). Each value must exist as a dropdown option first.
- An if/else chain where the first match wins. Each branch matches on the Slate Assigned Recruiter Code (field 374, Slate username such as `afinley4`), plus AC criteria where noted.

| Order | Territory | Recruiter | AC criteria besides the Slate code |
|---|---|---|---|
| 1 | SEM | [[Cara Selan]] | Inq or App Student Type = Seminary |
| 2 | INTL | Allison Gilbert | Slate code only |
| 3 | HCL (homeschool, classical, honors, Ashbrook) | James Metzger | Slate code only |
| 4 | MVS (military-veterans) | Ryan Yeater | Slate code only; no Slate SMS number |
| 5 | Grad COE / CAS | Julia Huston | Graduate + COE/CAS pathways |
| 6 | Grad COBE | [[John McCabe]] | Graduate + Business |
| 7 | Grad CONHS | Mason Feeman | Graduate + Health Professions |
| 8 | UG TX + all non-Ohio | Josh Marcoux | UG + state not Ohio, not OH, not blank |
| 9 | UG A–D (+ Elyria applicants) | Amanda Finley | Last name A–D |
| 10 | UG E–J | Aaron Hilt | Last name E–J |
| 11 | UG K–O | David Maloney (temporary) | Last name K–O |
| 12 | UG P–T | Anna Sanders | Last name P–T |
| 13 | UG U–Z | David Maloney | Last name U–Z |
| Fallback | No match | David Maloney | Also emails Brent an error notice (blank or odd last name) |

## Decisions (10/15 audit)
- Fixed Josh's segment: it used OR'd groups (state ≠ Ohio, or state ≠ OH), which caught every Ohio UG. Now one AND group with state not blank.
- Julia's branch now catches the CAS pathways, not just Education.
- Phones fixed: Cara's branch now sets her phone; Ryan's no longer leaves a stale phone number from a prior assignment.
- David Maloney stays as the fallback.
- Last-name branches stay last and keep the Slate code OR'd in. Slate assigns by the same letters, so codes and last names shouldn't disagree. They handle contacts that start outside Slate (e.g., the InPursuit form) with no code yet.
- Dropped the Recruiter Photo URL field (475).

## Known limits
- INTL, HCL, MVS, and Elyria rely entirely on Slate sending the code; without it, contacts sort by last name.
- State is free text: spellings other than "Ohio" or "OH" count as out of state.
- Grad branches checked Inq Student Type only, not App Student Type (as of the 10/15 audit).
- FA counselors are in the spreadsheet but not in AC (no fields).
- AC uses "Allison Gilbert"/"Allison"; the spreadsheet says "Alli."
