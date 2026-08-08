# Release Notes Document Structure

Matches team sample: `Release Notes <VERSION>.docx` (e.g. `2026.3.08.05`).

## Sections (pre-deploy)

1. **Title** — `Release Notes`
2. **Header block**
   - Version: `v{fix_version}`
   - Release Date: derived from Fix Version (`2026.3.08.05` → `05-August-2026`)
   - Development Team, Senior Manager, Director, SVP, Environment (from config)
   - Release Owner left blank for the team to fill per deployment
3. **Release Summary** — short paragraph
4. **Key Highlights** — bullets
5. **Affected Clients**
   - Analyze Clients → All Analyze-based (Standard) clients (if any AN tickets)
   - Custom Clients Summary + client name list
6. **Standard & Custom Summary** — short paragraph
7. **Dashboards / Reports** — bullets `{Client} - {Report}` using only the report/dashboard/model/dataset name. Analyze tickets with no named asset use `All Reports`.
8. **Deployment table** (scaffold only pre-deploy)

| Client | Deployment Owner | Status | Deployment ID & Time |
|---|---|---|---|
| Analyze | _(blank)_ | _(blank)_ | _(blank)_ |
| …each custom client… | | | |

9. **Change Details** table

| S.No | Ticket# | Parent | Link | Type | Client | Report | Description | Test by | Comments | Testing Status |
|---|---|---|---|---|---|---|---|---|---|---|

Pre-deploy: last three columns empty.
The Link column contains real clickable Jira hyperlinks. The Report column never contains change explanations.

10. **Sanity Checklist After Production Deployment** — questions only, no Yes/No filled
11. **Screenshots** — heading only
12. **Tickets Excluded from Deployment** — header + empty table (same columns as Change Details minus testing cols, plus Notes)

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
    "director": "Trent Vanest",
    "svp": "Rahul Das",
    "environment": "Production"
  },
  "narratives": {
    "release_summary": "...",
    "custom_clients_summary": "...",
    "standard_custom_summary": "..."
  },
  "tickets": [
    {
      "key": "PIC-5234",
      "parent": "PIC-4211",
      "link": "https://abcfinancial.atlassian.net/browse/PIC-5234",
      "type": "Custom",
      "client": "Jetts",
      "report": "Custom model dataset replacing with Jetts Dataset",
      "description": "Custom model dataset replacing with Jetts Dataset",
      "test_by": "",
      "comments": "",
      "testing_status": ""
    }
  ],
  "excluded": []
}
```

## Classification quick rules

- `AN-*` → Type `Analyze`, Client `Standard`
- `PIC-*` → Type `Custom`, Client from summary prefix before ` - ` / `:` / first hyphenated client token
- Special case: summary starts with `Analyze -` → still Analyze/Standard; report is text after prefix
