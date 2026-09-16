# Release Notes Document Structure

Matches team sample: `Release Notes <VERSION>.docx` (e.g. `2026.3.08.05`).

## Sections (pre-deploy)

1. **Title** — `Release Notes`
2. **Header block**
   - Centered, borderless two-column block; labels right-aligned so colons line up and values left-aligned
   - Version: `v{fix_version}`
   - Release Date: derived from Fix Version (`2026.3.08.05` → `05-August-2026`)
   - Development Team, Senior Manager, SVP, Environment (from config)
   - Release Owner left blank for the team to fill per deployment
3. **Release Summary** — the only summary section. A brief description sentence carrying the counts (e.g. "This release delivers 5 new reports, 1 customization, and 1 Looker exit for Glofox Analyze, Jazzercise, and Lift."), followed by the count table:

| Category | Count |
|---|---|
| New Reports | _n_ |
| Customizations | _n_ |
| Looker Exits | _n_ |
| Optimizations | _n_ |
| Total | _ticket count_ |

Four categories only, zeros included. Categories come from Jira labels (see `config.json` → `summary_categories`). Each ticket counts once, so Total equals the number of tickets in Ticket Details. There is no Custom Clients Summary and no Standard & Custom Summary.

4. **Reports / Dashboards Delivered** — merged replacement for Key Highlights and Dashboards / Reports. One bullet per ticket: `{Client} - {Report name} - {change description}`.
5. **Affected Clients** — bullets of distinct client names (`Glofox Analyze` when the release has AN tickets, plus each custom client).
6. **Deployment Details** — one row per affected client:

| Client | Deployment Owner | Status | Deployment ID & Time |
|---|---|---|---|
| Glofox Analyze | _(blank)_ | _(blank)_ | _(blank)_ |
| …each custom client… | | | |

7. **Ticket Details** — renamed and simplified replacement for Change Details:

| Ticket | Ticket Link | Test | Status |
|---|---|---|---|

Ticket Link contains a real clickable Jira hyperlink. Test and Status are blank pre-deploy.

8. **Testing Evidence** — heading only; the team adds screenshots or other evidence later.
9. **Tickets Excluded from Deployment**:

| Ticket | Ticket Link | Client | Report | Notes |
|---|---|---|---|---|

Header + empty row by default. Populate rows **only** when the user explicitly asks to list removed tickets there. A plain “remove ticket from deployment” prompt means omit from the included sections only—do not auto-fill this table.

## Fix Version → Release Date

Pattern: `YYYY.Quarter.MM.DD`

- Segment 1 = Year
- Segment 2 = Quarter / release cycle (NOT the month)
- Segment 3 = Month
- Segment 4 = Day

Example: `2026.3.08.05` → `05-August-2026`

**Preferred:** use the Fix Version `releaseDate` returned by Jira (`fixVersions[].releaseDate`) as the source of truth; fall back to parsing the version string only if absent.

## Tickets JSON schema (script input)

```json
{
  "fix_version": "2026.3.08.05",
  "mode": "pre",
  "meta": {
    "development_team": "Customize BI Team",
    "release_owner": "",
    "senior_manager": "Sushma Bhamidipati",
    "svp": "Rahul Das",
    "environment": "Production"
  },
  "narratives": {
    "release_summary": "..."
  },
  "category_counts": [
    { "key": "new_reports", "label": "New Reports", "count": 5 },
    { "key": "customizations", "label": "Customizations", "count": 1 },
    { "key": "looker_exits", "label": "Looker Exits", "count": 1 },
    { "key": "optimizations", "label": "Optimizations", "count": 0 }
  ],
  "tickets": [
    {
      "key": "PIC-5234",
      "parent": "PIC-4211",
      "link": "https://abcfinancial.atlassian.net/browse/PIC-5234",
      "type": "Custom",
      "client": "Jetts",
      "report": "Custom model dataset replacing with Jetts Dataset",
      "description": "Custom model dataset replacing with Jetts Dataset",
      "labels": ["Report_Enhancement"],
      "category": "customizations",
      "category_from_label": true,
      "test_by": "",
      "comments": "",
      "testing_status": ""
    }
  ],
  "excluded": []
}
```

`test_by` and `deployment_status` are only rendered in `post` mode; pre-deploy the Ticket Details Test and Status columns remain blank.

## Classification quick rules

- `AN-*` → Type `Analyze`, Client `Glofox Analyze`
- `PIC-*` → Type `Custom`, Client from summary prefix before ` - ` / `:` / first hyphenated client token
- Special case: summary starts with `Analyze -` → still Analyze / `Glofox Analyze`; report is text after prefix
