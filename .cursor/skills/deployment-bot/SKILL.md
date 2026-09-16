---
name: deployment-bot
description: >-
  Deployment Bot — generates Fitness BI / Customize BI deployment release notes
  from Jira Fix Version tickets, writes a Word document matching the team
  template, and in the same run uploads it to SharePoint (deployment bot
  release notes / YYYY-MM). Creates the SHIPIT Change Request when asked.
  Posts Slack notifications only when the user explicitly asks to notify Slack.
  Use when the user asks for Deployment Bot, release notes, Fix Version
  deployment notes, pre-deploy release doc, create Jira ticket / SHIPIT change
  request, Slack notify, or automate release notes from Jira (AN/PIC). Always
  generate AND upload unless the user explicitly says not to upload.
---

# Deployment Bot

## CRITICAL — deterministic generation (do NOT improvise)

The Word document must be produced **only** by the scripts in `scripts/`. The agent must **never** hand-write, reword, re-case, shorten, or reorder any generated content.

- ALWAYS run `scripts/build_from_jira_json.py` (it normalizes tickets and builds the `.docx`).
- The values for Release Summary, Reports / Dashboards Delivered, clients, ticket rows, and category counts come **verbatim** from the scripts. Do not compose these yourself.
- Do NOT open the `.docx` and edit text by hand. If something looks wrong, fix the script, not the document.
- Your only judgement calls: which Fix Version, and which tickets to omit when the user says to remove them.
- **Generate + upload is one job.** A request to generate release notes always includes SharePoint upload in the **same** turn. Do not stop after the `.docx`. Do not ask whether to upload. Do not wait for a second prompt. Skip upload only if the user explicitly says not to upload.
- **SHIPIT Change Request is a separate job** unless the user also asks to create the Jira ticket in the same prompt. Do not create SHIPIT on a generate-only request.
- **Slack notify is a separate job** unless the user also asks to notify Slack in the same prompt. Do not post to Slack on generate-only, generate+upload, or generate+SHIPIT. **Never post to `#insights-customize-squad` or `#customize-bi-buddies` unless the user explicitly asked to notify Slack.** Training and format checks are not a send.
- If you think output should change, tell the user and change the script — never quietly rewrite the text in the doc.

Reports / Dashboards Delivered is produced from each normalized ticket's client, report, and concise change description.

## Goal

For a given **Fix Version** (deployment date, e.g. `2026.3.08.12`):

1. Pull all Jira tickets on that Fix Version
2. Classify Analyze vs Customize and extract client/report details
3. Generate a **pre-deployment** Word release notes doc (team fills testing + deployment IDs later)
4. Save locally **and** upload to SharePoint in the same run: `deployment bot release notes` / month folder (`YYYY-MM` from the Fix Version) / `Release Notes <VERSION>.docx`
5. When asked, create the SHIPIT **Change Request** for that Fix Version (same layout as SHIPIT-17191 / approved test SHIPIT-17289)
6. When asked, notify Slack in `#insights-customize-squad` (CC Sushma and Trent) and `#customize-bi-buddies` (CC Sushma only)

## When to run

User says things like:
- "Deployment Bot: generate release notes for 2026.3.08.12"
- "Generate release notes for 2026.3.08.12"
- "Create pre-deploy release notes for Fix Version …"
- "Automate release notes from Jira"

Any of those phrases means **generate the Word file and upload it**. The user does not need to mention SharePoint.

Create the SHIPIT Change Request when the user says things like:
- "Create the Jira ticket for 2026.3.09.16"
- "Create the SHIPIT change request"
- "Create jira ticket for this deployment"

If they ask for notes **and** the Jira ticket in one prompt, do generate → upload → SHIPIT, in that order.

Notify Slack when the user says things like:
- "Notify Slack"
- "Send the Slack message"
- "Post in the squad channels"

If they ask for notes, Jira, **and** Slack in one prompt, do generate → upload → SHIPIT → Slack, in that order. Still do not post Slack unless Slack was part of that ask.

## Prerequisites

1. **Atlassian MCP** connected (`user-atlassian`)
2. Cloud ID: `5c639b1d-82c0-4932-96af-65d4921fcf57` (site `abcfinancial.atlassian.net`)
3. **Slack MCP** connected (`user-slack`) — Glofox workspace. Needed only when the user asks to notify Slack.
4. Python with `python-docx` (`py -3 -m pip install python-docx`)
5. Read [config.json](config.json) for defaults (team names, output dir)

## Scope split (quality rule)

### Agent fills from Jira (always)

- Version / Release Date (from Fix Version name)
- Centered header defaults from config (team, senior manager, SVP, environment) — confirm with user if changed
- **Release Owner** left blank (filled by the team per deployment)
- **Release Summary** — the only summary section: brief description plus the four category counts (New Reports, Customizations, Looker Exits, Optimizations) from Jira labels
- **Reports / Dashboards Delivered** — one merged list with client, report name, and change description
- Affected Clients list
- Deployment Details table (one row per affected client)
- Ticket Details table: Ticket, clickable Ticket Link, Test, Status
- Testing Evidence heading only (no placeholder text)
- Tickets Excluded table (empty unless user explicitly asks to list excluded tickets)

### Team fills later (leave blank / TBD — do NOT invent)

- Release Owner
- In Deployment Details: Deployment Owner, Status, Deployment ID & Time
- In Ticket Details: Test and Status
- Testing evidence (screenshots or other evidence)
- Tickets Excluded — leave the table empty by default

### Removing a ticket from deployment (prompt rules)

If the user says to **remove / drop / exclude a ticket from deployment** (and nothing more):

1. Omit that ticket from Reports / Dashboards Delivered, Ticket Details, client lists, counts, and any other included sections
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
- [ ] 6. Save locally AND upload to SharePoint (`deployment bot release notes` / `YYYY-MM`) before telling the user you are done
- [ ] 7. Create SHIPIT Change Request only when the user asked for the Jira ticket
- [ ] 8. Notify Slack only when the user explicitly asked — both live channels; never post otherwise
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
| Client (Analyze) | `Glofox Analyze` (never `Standard`) |
| Client (Custom) | Prefix before ` - ` or `:` in summary (e.g. `Jetts - …` → Jetts). If missing, use `Unknown` and flag for user. |
| Report | **Only** the report, dashboard, semantic model, data model, or dataset name. Remove change instructions and explanations. For Analyze tickets with no identifiable named asset, use `All Reports`. |
| Description | Prefer short highlight from summary; if summary is thin, first meaningful sentence of description (no huge tables/images) |
| Parent | `parent.key` if present |
| Link | A real clickable hyperlink to `https://abcfinancial.atlassian.net/browse/{KEY}` (never plain URL text) |
| Deployment Details / Ticket Details manual fields | Empty string for pre-deploy |
| Category | From `fields.labels` via `config.json` → `summary_categories`. Every ticket lands in exactly one of the four categories, so the counts add up to the ticket total. |

Known custom clients from recent releases (not exhaustive): Jetts, Jazzercise, FIT4MOM, FWBC — still parse from summary, do not hard-limit.

### Release size categories (label-driven)

The deployment is sized by **four categories only**: New Reports, Customizations, Looker Exits, Optimizations.

- Jira **labels** decide the category (`Looker-Exit`, `NewRequirement`, `Report_Enhancement` / `Enhancement` / `Customize`, `Optimize`, …). Label matching ignores case and `-`/`_`.
- When a ticket carries labels from more than one category, the `priority` list in `config.json` wins — `Looker-Exit` outranks everything, so a Looker exit is never counted as a customization.
- Summary wording is used **only** when no label maps to a category; the build then prints a `WARNING Category from summary` line naming those tickets. Ask the team to add the right label rather than hand-editing the count.
- New labels appear over time: extend `config.json` → `summary_categories.labels`, never the generated document.

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
[scripts/generate_release_notes.py](scripts/generate_release_notes.py),
[scripts/upload_to_sharepoint.py](scripts/upload_to_sharepoint.py),
[scripts/build_shipit_change_request.py](scripts/build_shipit_change_request.py).

### Step 5 — Quality spot-check

Before handing to user:
- Ticket count in Ticket Details matches Jira fetch
- Release Summary is the only summary section: description sentence + count table with all four categories (zeros included), Total equal to the ticket count
- Reports / Dashboards Delivered has one bullet per ticket: `{Client} - {Report} - {change description}`
- Affected Clients and Deployment Details contain `Glofox Analyze` plus each custom client
- Ticket Details has exactly: Ticket, Ticket Link, Test, Status
- Every Custom row has a real client name (not Unknown) — call out Unknowns
- Analyze rows show Client `Glofox Analyze` and Type `Analyze`; the word `Standard` appears nowhere
- Report cells contain only asset names; Analyze tickets without a named asset show `All Reports`
- Every Ticket Link cell is a clickable Jira hyperlink
- Testing Evidence heading is present with no placeholder text
- There is no Director field, separate Key Highlights, separate Dashboards / Reports, Change Details, Sanity Checklist, or Screenshots heading
- Excluded table empty unless user explicitly asked to list removed tickets there
- Filename: `Release Notes <VERSION>.docx`

### Step 6 — Deliver and upload to SharePoint (same prompt — always)

This step is part of generate, not a follow-up. Finish it before the reply.

1. Keep the local `.docx` path from Step 4.
2. Upload is **required**. Do not leave the file only in Downloads. Do not ask the user to upload. Skip only if they said not to upload.
3. Read `config.json` → `sharepoint`. Layout is always:
   `Release Notes / deployment bot release notes / YYYY-MM / Release Notes <VERSION>.docx`
   Month folder comes from the Fix Version (`2026.3.09.16` → `2026-09`). Create the root folder and the month folder if they do not exist. Do not upload into `test deployment bot`.
   `upload_method` decides the route:
   - `browser` (current): team library is **not** synced to File Explorer, so upload through the SharePoint web UI with the Playwright MCP browser.
   - `sync`: library is synced; `local_sync_path` holds the local folder.
4. Stage the file first — Playwright can only read files under the repo root:

```bash
py -3 scripts/upload_to_sharepoint.py --docx "<output_dir>/Release Notes <VERSION>.docx" --config config.json --fix-version <VERSION>
```

With `upload_method: browser` this copies the `.docx` into `sharepoint.staging_dir` and prints the staged path plus `root_folder` and `month_folder`. With `sync` it copies into the synced library folder and you are done.

5. Browser upload steps (Playwright MCP), starting from `sharepoint.folder_url`:
   - Ensure folder `deployment bot release notes` exists (Create or upload → Folder). Open it.
   - Ensure the month folder (`YYYY-MM`) exists inside it. Open it.
   - Click **Create or upload → Files upload**, then `browser_file_upload` with the staged path from Step 4.
   - Confirm via `browser_find` on the version string; SharePoint shows `Uploaded <file> to <month folder>`.
   - If the page lands on a Microsoft sign-in screen, ask the user to sign in to that browser window — never enter their password. A signed-in Playwright session does **not** need a new login on every run; only when that session expires.
6. Return the local path, the SharePoint folder URL, and the confirmed file name.
7. Remind the user what they still fill post-deploy.

### Step 7 — Create SHIPIT Change Request (only when asked)

Do this when the user asks to create the Jira / SHIPIT / change-request ticket. Approved shape: [SHIPIT-17191](https://abcfinancial.atlassian.net/browse/SHIPIT-17191) (live) and [SHIPIT-17289](https://abcfinancial.atlassian.net/browse/SHIPIT-17289) (test).

1. Use the same Fix Version JSON as the release notes (fetch it first if this is a ticket-only request).
2. Build the payload with the script — do **not** free-write field text:

```bash
py -3 scripts/build_shipit_change_request.py --jira-json <jira_VERSION.json> --fix-version <VERSION> --config config.json
```

Add `--test-ticket` only when the user asked for a test ticket. That prefixes summary and every section with TEST TICKET / DO NOT ACTION.

3. Create the issue with Atlassian MCP `createJiraIssue`:
   - `cloudId` from config
   - `projectKey`: `SHIPIT`
   - `issueTypeName`: `Change Request`
   - `summary` and `description` from the script JSON
   - `contentFormat`: `markdown`
   - `additional_fields`: the script JSON object as-is
   - **Do not set `assignee_account_id`.** Assignee stays Unassigned. Deployment owner is filled by the team later.
   - **Do not set Request Type.** Leave it blank. The API cannot stamp Manual Change.
   - Reporter is whoever is signed in to Atlassian MCP. Do not try to blank it.

4. For each work ticket key in `link.inward_keys`, call `createIssueLink`:
   - `type`: `Discovery - Connected`
   - `inwardIssue`: the PIC/AN key
   - `outwardIssue`: the new SHIPIT key

5. Return the SHIPIT URL. Do not transition, approve, or close the ticket.

Do not copy dummy TRZCX keys from older tickets. Verification is one line per work ticket plus the standard smoke test.

### Step 8 — Slack notify (only when explicitly asked)

Read `config.json` → `slack`. Post with Slack MCP `slack_send_message` (`unfurl_app_links: true`). The post is sent as **whoever is signed into Slack in Cursor**, not as a bot and not as the deployment owner.

**Do not send during this training, format review, or any generate/SHIPIT run that did not include Slack.** These two channels are live. First live send is when the user asks during a real deployment.

Channels (always both, when sending):

| Channel | ID | CC |
|---|---|---|
| `#insights-customize-squad` | `C08HB93PEVD` | Sushma and Trent (`<@U08LDAQ7SDV> <@U0ASR2XGRPZ>`) |
| `#customize-bi-buddies` | `C08KM1USMM1` | Sushma only (`<@U08LDAQ7SDV>`) |

CC rule: **Sushma only in `#customize-bi-buddies`.** **Sushma and Trent in `#insights-customize-squad`.** Do not swap these.

Message body (same wording in both channels except the CC line):

```
Hello Team,

Our upcoming deployment is scheduled for {weekday}, {month} {day}, {year}.
Release notes and the deployment ticket are below for reference:

SharePoint: [Release Notes {VERSION}.docx]({sharepoint_url})
Service Desk: [{SHIPIT-key}](https://abcfinancial.atlassian.net/browse/{SHIPIT-key})

Thanks!
```

Append a CC line per channel:

- `#insights-customize-squad`: `CC: <@U08LDAQ7SDV> <@U0ASR2XGRPZ>`
- `#customize-bi-buddies`: `CC: <@U08LDAQ7SDV>`

Date comes from the Fix Version (`2026.3.09.16` → Wednesday, September 16, 2026). SharePoint URL is the uploaded file under `deployment bot release notes / YYYY-MM`. SHIPIT key is the ticket created (or the live ticket the user named). Both must be markdown links, not plain URLs.

Do not post to DMs for live notify. Do not use `slack_send_message_draft` unless the user asks for a draft. Return both message permalinks after sending.

## How each section is produced (reference only — the scripts do this)

These are implemented in the scripts. They are documented here so you can verify output, **not** so you can generate it yourself.

- **Release Summary**: `size_sentence()` writes the description + counts sentence (e.g. "This release delivers 5 new reports, 1 customization, and 1 Looker exit for Glofox Analyze, Jazzercise, and Lift."), and `count_categories()` produces the `category_counts` rendered as the count table under the same heading. Zero-count categories are omitted from the sentence but still shown in the table. There is no separate Custom Clients Summary or Standard & Custom Summary.
- **Reports / Dashboards Delivered**: one bullet per ticket—`{Client} - {Report name} - {change description}`. The change description comes from the concise ticket summary; do not paste long Jira user-story boilerplate.
- **Affected Clients**: the distinct client names in the release — `Glofox Analyze` when there are AN tickets, plus each custom client.
- **Deployment Details**: one row per affected client; manual deployment fields blank pre-deploy.
- **Ticket Details**: one row per ticket with Ticket, clickable Ticket Link, Test, Status; Test and Status blank pre-deploy.

The scripts never invent features not present on tickets, and neither should you.

## Failure modes

- Atlassian Unauthorized → ask user to reconnect Atlassian MCP
- Slack Unauthorized → ask user to reconnect Slack MCP; do not post anywhere else as a workaround
- Fix Version not found / 0 issues → verify exact version string in Jira
- Ambiguous client on PIC → list ticket keys and ask once

## References

- Document sections & JSON schema: [document-structure.md](document-structure.md)
- Sample template: [templates/Release Notes SAMPLE.docx](templates/Release%20Notes%20SAMPLE.docx)
- Defaults: [config.json](config.json)
