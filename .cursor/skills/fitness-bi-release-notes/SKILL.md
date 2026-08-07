---
name: fitness-bi-release-notes
description: >-
  Generates Fitness BI / Customize BI deployment release notes from Jira Fix
  Version tickets, writes a Word document matching the team template, and
  prepares SharePoint upload. Use when the user asks for release notes, Fix
  Version deployment notes, pre-deploy release doc, or Automate release notes
  from Jira (AN/PIC).
---

# Fitness BI Release Notes Agent

## Goal

For a given **Fix Version** (deployment date, e.g. `2026.3.08.12`):

1. Pull all Jira tickets on that Fix Version
2. Classify Analyze vs Customize and extract client/report details
3. Generate a **pre-deployment** Word release notes doc (team fills testing + deployment IDs later)
4. Save locally; upload to SharePoint when configured

## When to run

User says things like:
- "Generate release notes for 2026.3.08.12"
- "Create pre-deploy release notes for Fix Version …"
- "Automate release notes from Jira"

## Prerequisites

1. **Atlassian MCP** connected (`user-atlassian`)
2. Cloud ID: `5c639b1d-82c0-4932-96af-65d4921fcf57` (site `abcfinancial.atlassian.net`)
3. Python with `python-docx` (`py -3 -m pip install python-docx`)
4. Read [config.json](config.json) for defaults (team names, output dir)

## Scope split (quality rule)

### Agent fills from Jira (always)

- Version / Release Date (from Fix Version name)
- Header defaults from config (team, owners, environment) — confirm with user if changed
- Release Summary, Key Highlights, Affected Clients, Custom Clients list
- Standard & Custom Summary
- Dashboards / Reports list
- Change Details: S.No, Ticket#, Parent, Link, Type, Client, Report, Description
- Empty scaffolding for: Deployment table rows (clients only), Sanity checklist (unchecked), Screenshots header, Tickets Excluded table

### Team fills later (leave blank / TBD — do NOT invent)

- Deployment Owner
- Deployment ID & Time
- Status (Done / etc.) after deploy
- Test by / Comments / Testing Status
- Screenshots
- Sanity checklist Yes/No answers
- Tickets Excluded (unless user supplies a list)

## Workflow

Copy and track:

```
Release notes progress:
- [ ] 1. Confirm Fix Version + mode (pre-deploy default)
- [ ] 2. Fetch Jira tickets
- [ ] 3. Normalize ticket rows (type/client/report)
- [ ] 4. Generate Word doc via script
- [ ] 5. Spot-check against sample quality
- [ ] 6. Save path + optional SharePoint upload
```

### Step 1 — Confirm inputs

Ask only if missing:
- **Fix Version** string (required), e.g. `2026.3.08.12`
- Optional overrides: Release Owner, Development Team
- Mode: `pre` (default) vs `post` (only if user provides deploy/test extras)

### Step 2 — Fetch tickets

Use Atlassian MCP `searchJiraIssuesUsingJql`:

```
cloudId: 5c639b1d-82c0-4932-96af-65d4921fcf57
jql: fixVersion = "<VERSION>" ORDER BY key ASC
fields: summary, description, issuetype, status, labels, components, parent, project, fixVersions, assignee
maxResults: 100
responseContentFormat: markdown
```

Paginate with `nextPageToken` if needed. If zero issues, stop and tell the user.

Exclude epics/parents that are only containers **only if** they have no useful deployable summary and user confirms; default = **include every issue on the Fix Version**.

### Step 3 — Normalize each ticket

| Field | Rule |
|---|---|
| Type | Project `AN` → `Analyze`; Project `PIC` → `Custom`. If other projects appear, ask user. |
| Client (Analyze) | `Standard` |
| Client (Custom) | Prefix before ` - ` or `:` in summary (e.g. `Jetts - …` → Jetts). If missing, use `Unknown` and flag for user. |
| Report | **Only** the report, dashboard, semantic model, data model, or dataset name. Remove change instructions and explanations. For Analyze tickets with no identifiable named asset, use `All Reports`. |
| Description | Prefer short highlight from summary; if summary is thin, first meaningful sentence of description (no huge tables/images) |
| Parent | `parent.key` if present |
| Link | A real clickable hyperlink to `https://abcfinancial.atlassian.net/browse/{KEY}` (never plain URL text) |
| Test by / Comments / Testing Status | Empty string for pre-deploy |

Known custom clients from recent releases (not exhaustive): Jetts, Jazzercise, FIT4MOM, FWBC — still parse from summary, do not hard-limit.

### Step 4 — Generate document

1. Write a tickets JSON file (see schema in [document-structure.md](document-structure.md))
2. Run:

```bash
py -3 scripts/generate_release_notes.py --input <tickets.json> --output "<output_dir>/Release Notes <VERSION>.docx"
```

Script lives at [scripts/generate_release_notes.py](scripts/generate_release_notes.py).

### Step 5 — Quality spot-check

Before handing to user:
- Ticket count in Change Details matches Jira fetch
- Every Custom row has a real client name (not Unknown) — call out Unknowns
- Analyze rows show Client `Standard` and Type `Analyze`
- Report cells contain only asset names; Analyze tickets without a named asset show `All Reports`
- Every Link cell is a clickable Jira hyperlink
- Deployment ID / Test by / Screenshots sections are empty placeholders
- Filename: `Release Notes <VERSION>.docx`

### Step 6 — Deliver

- Return local file path
- SharePoint: if `config.json` → `sharepoint.enabled` is false, say draft is ready for manual upload (or ask for site/folder to enable later)
- Remind user what they still fill post-deploy

## Narrative generation rules

Keep tone matching sample docs (plain, operational):

- **Release Summary**: 1 sentence covering reporting enhancements / custom updates / semantic model / docs as applicable from ticket mix
- **Key Highlights**: one bullet per ticket → `{Client}: {Report/short description}`
- **Affected Clients → Analyze**: if any AN tickets → "All Analyze-based (Standard) clients"
- **Custom Clients Summary**: short blurb + bullet list of distinct custom client names
- **Standard & Custom Summary**: 1–2 sentences on usability / reports / custom enhancements
- **Dashboards / Reports**: `{Client} - {Report}` lines, where Report is only the report/dashboard/model/dataset name—never an explanation

Do not invent features not present on tickets.

## Failure modes

- Atlassian Unauthorized → ask user to reconnect Atlassian MCP
- Fix Version not found / 0 issues → verify exact version string in Jira
- Ambiguous client on PIC → list ticket keys and ask once

## References

- Document sections & JSON schema: [document-structure.md](document-structure.md)
- Sample template: [templates/Release Notes SAMPLE.docx](templates/Release%20Notes%20SAMPLE.docx)
- Defaults: [config.json](config.json)
