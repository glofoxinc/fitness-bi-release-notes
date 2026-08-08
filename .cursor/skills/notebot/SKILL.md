---
name: notebot
description: >-
  NoteBot — generates Fitness BI / Customize BI deployment release notes from
  Jira Fix Version tickets, writes a Word document matching the team template,
  and prepares SharePoint upload. Use when the user asks for NoteBot, release
  notes, Fix Version deployment notes, pre-deploy release doc, or automate
  release notes from Jira (AN/PIC).
---

# NoteBot

## CRITICAL — deterministic generation (do NOT improvise)

The Word document must be produced **only** by the scripts in `scripts/`. The agent must **never** hand-write, reword, re-case, shorten, or reorder any generated content.

- ALWAYS run `scripts/build_from_jira_json.py` (it normalizes tickets and builds the `.docx`).
- The values for Key Highlights, Dashboards / Reports, Report column, Description, clients, and summaries come **verbatim** from the scripts. Do not compose these yourself.
- Do NOT open the `.docx` and edit text by hand. If something looks wrong, fix the script, not the document.
- Your only judgement calls: which Fix Version, and which tickets to omit when the user says to remove them.
- If you think output should change, tell the user and change the script — never quietly rewrite the text in the doc.

Key Highlights and the Report column are produced from **different** fields (`highlight` vs `report`) on purpose. Never make one look like the other.

## Goal

For a given **Fix Version** (deployment date, e.g. `2026.3.08.12`):

1. Pull all Jira tickets on that Fix Version
2. Classify Analyze vs Customize and extract client/report details
3. Generate a **pre-deployment** Word release notes doc (team fills testing + deployment IDs later)
4. Save locally; upload to SharePoint when configured

## When to run

User says things like:
- "NoteBot: generate release notes for 2026.3.08.12"
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
- Header defaults from config (team, senior manager, director, SVP, environment) — confirm with user if changed
- **Release Owner** left blank (filled by the team per deployment)
- Release Summary, Key Highlights, Affected Clients, Custom Clients list
- Standard & Custom Summary
- Dashboards / Reports list
- Change Details: S.No, Ticket#, Parent, Link, Type, Client, Report, Description
- Empty scaffolding for: Deployment table rows (clients only), Sanity checklist (unchecked), Screenshots heading only (no placeholder text), Tickets Excluded table (empty unless user explicitly asks to list excluded tickets)

### Team fills later (leave blank / TBD — do NOT invent)

- Release Owner
- Deployment Owner
- Deployment ID & Time
- Status (Done / etc.) after deploy
- Test by / Comments / Testing Status
- Screenshots (heading only in the generated doc)
- Sanity checklist Yes/No answers
- Tickets Excluded — leave the table empty by default

### Removing a ticket from deployment (prompt rules)

If the user says to **remove / drop / exclude a ticket from deployment** (and nothing more):

1. Omit that ticket from Key Highlights, Dashboards / Reports, Change Details, clients lists, and any other included sections
2. Do **NOT** add it to **Tickets Excluded from Deployment**
3. Leave the Excluded table empty (header + blank row only)

Only if the user **explicitly** asks to list/record the removed ticket(s) in **Tickets Excluded from Deployment**, put them there (with Notes if provided).

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
- Optional override: Development Team
- Mode: `pre` (default) vs `post` (only if user provides deploy/test extras)

Do **not** default a Release Owner — leave that field blank unless the user explicitly provides a name.

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

### Step 4 — Generate document (always via script)

1. Save the raw Jira search result (the object with `issues[]`) to a JSON file, e.g. `jira_<VERSION>.json`.
2. If the user asked to remove tickets, delete those issues from that JSON's `issues[]` **before** running (that is the only allowed manual step). Do not touch anything else.
3. Run the canonical builder — it normalizes tickets and writes the `.docx`:

```bash
py -3 scripts/build_from_jira_json.py --jira-json <jira_VERSION.json> --fix-version <VERSION> --config config.json --output-json "<output_dir>/Release Notes <VERSION>.pre.json" --output-docx "<output_dir>/Release Notes <VERSION>.docx"
```

Use the resulting `.docx` **exactly as produced**. Never edit its text by hand. Scripts:
[scripts/build_from_jira_json.py](scripts/build_from_jira_json.py),
[scripts/normalize_tickets.py](scripts/normalize_tickets.py),
[scripts/generate_release_notes.py](scripts/generate_release_notes.py).

### Step 5 — Quality spot-check

Before handing to user:
- Ticket count in Change Details matches Jira fetch
- Every Custom row has a real client name (not Unknown) — call out Unknowns
- Analyze rows show Client `Standard` and Type `Analyze`
- Report cells contain only asset names; Analyze tickets without a named asset show `All Reports`
- Every Link cell is a clickable Jira hyperlink
- Deployment ID / Test by / Screenshots heading present with no placeholder text under Screenshots
- Excluded table empty unless user explicitly asked to list removed tickets there
- Filename: `Release Notes <VERSION>.docx`

### Step 6 — Deliver

- Return local file path
- SharePoint: if `config.json` → `sharepoint.enabled` is false, say draft is ready for manual upload (or ask for site/folder to enable later)
- Remind user what they still fill post-deploy

## How each section is produced (reference only — the scripts do this)

These are implemented in the scripts. They are documented here so you can verify output, **not** so you can generate it yourself.

- **Release Summary / Standard & Custom Summary / Custom Clients Summary**: built by `build_from_jira_json.py` from the ticket mix.
- **Key Highlights**: one bullet per ticket from each ticket's `highlight` field (`{Client}: {concise ticket info}`). Fuller than the Report column — leave it as the script emits it.
- **Affected Clients → Analyze**: if any AN tickets → "All Analyze-based (Standard) clients".
- **Dashboards / Reports** and **Change Details → Report**: from each ticket's `report` field — report/dashboard/model/dataset name only, never an explanation.

The scripts never invent features not present on tickets, and neither should you.

## Failure modes

- Atlassian Unauthorized → ask user to reconnect Atlassian MCP
- Fix Version not found / 0 issues → verify exact version string in Jira
- Ambiguous client on PIC → list ticket keys and ask once

## References

- Document sections & JSON schema: [document-structure.md](document-structure.md)
- Sample template: [templates/Release Notes SAMPLE.docx](templates/Release%20Notes%20SAMPLE.docx)
- Defaults: [config.json](config.json)
