---
name: deployment-bot
description: >-
  Deployment Bot — generates Fitness BI / Customize BI deployment notes
  from Jira Fix Version tickets, writes a Word document matching the team
  template, and in the same run uploads it to SharePoint (deployment bot
  release notes / YYYY-MM) together with client-facing Release Notes, and
  creates the SHIPIT Change Request in Review Ready. The ticket and the later
  Slack message include both documents. Posts Slack notifications only when
  the user later asks to notify Slack. Use when the user asks for Deployment
  Bot, deployment notes, release notes, Fix Version deployment notes,
  pre-deploy release doc, create Jira ticket / SHIPIT change request, Slack
  notify, or automate deployment notes from Jira (AN/PIC). Always generate,
  upload, and create SHIPIT unless the user explicitly says not to upload or
  not to create the ticket.
---

# Deployment Bot

## CRITICAL — deterministic generation (do NOT improvise)

The Word document must be produced **only** by the scripts in `scripts/`. The agent must **never** hand-write, reword, re-case, shorten, or reorder any generated content.

- ALWAYS run `scripts/build_from_jira_json.py` (it normalizes tickets and builds the `.docx`).
- The values for Deployment Summary, Reports / Dashboards Delivered, clients, ticket rows, and category counts come **verbatim** from the scripts. Do not compose these yourself.
- Do NOT open the `.docx` and edit text by hand. If something looks wrong, fix the script, not the document.
- Your only judgement calls: which Fix Version, and which tickets to omit when the user says to remove them.
- **Lineage is fixed:** check PR merge state → generate deployment notes and client-facing release notes → upload both to SharePoint → create the SHIPIT ticket in Review Ready, with both document links. Then **stop**. Slack is a later job, and that message includes both documents.
- **Generate + upload + SHIPIT is one job.** A request to generate deployment notes (or the older phrase “release notes”) always includes both Word files, SharePoint upload of both, **and** the SHIPIT Change Request in the **same** turn. Do not stop after the deployment `.docx`. Do not ask whether to upload or create the ticket. Do not wait for a second prompt. Skip upload only if the user explicitly says not to upload. Skip SHIPIT only if the user explicitly says not to create the ticket.
- **Merged PRs are a hard gate.** Before generating any document, every included Fix Version ticket must have at least one attached PR and all attached PRs must be merged. If a ticket has no PR or any PR is not merged, stop before creating files, uploading, creating SHIPIT, or notifying Slack. List the blocking ticket keys and states for the user.
- **After notes and ticket exist, say the PR result out loud.** In the same reply, list each included ticket key and that its PR is merged. Do not bury this in a SharePoint path. Example: “PR check passed. AN-5526, AN-5527, and PIC-6085 each have a merged PR.” Then give both SharePoint file names and the SHIPIT URL. Remind the user that Slack has not been sent.
- **Slack notify is a separate job.** Do not post to Slack after generate, upload, or SHIPIT. Post only when the user later says to notify Slack / send the message. **Never post to `#insights-customize-squad` or `#customize-bi-buddies` unless the user explicitly asked to notify Slack.** Training and format checks are not a send.
- If you think output should change, tell the user and change the script — never quietly rewrite the text in the doc.

Reports / Dashboards Delivered is produced from each normalized ticket's client, report, and concise change description.

Call the generated document **deployment notes** everywhere (heading, file name, Slack, SHIPIT). Older user phrasing like “release notes” still means this same job.

## Goal

For a given **Fix Version** (deployment date, e.g. `2026.3.08.12`):

1. Pull all Jira tickets on that Fix Version
2. Verify every included ticket has only merged PRs
3. Classify Analyze vs Customize and extract client/report details
4. Generate a **pre-deployment** Word deployment notes doc (team fills testing + deployment IDs later)
5. Generate the client-facing **Release Notes** Word doc in the same run (grouped by client; ticket keys are links)
6. Save both locally **and** upload both to SharePoint: `deployment bot release notes` / month folder (`YYYY-MM`) / `Deployment Notes <VERSION>.docx` and `Release Notes <VERSION>.docx`
7. Create the SHIPIT **Change Request** for that Fix Version, include both document links, apply explicitly requested reporter/assignee names, and move it to **Review Ready**
8. Tell the user the PR check passed (each included ticket, merged) plus both file locations and the SHIPIT URL. Do not send Slack yet.
9. When asked later, notify Slack in `#insights-customize-squad` (CC Sushma, Sai Anirudh Karre, Zeke Brustkern, and Eoin George) and `#customize-bi-buddies` (CC Sushma only). The message includes both documents and the ticket.

## When to run

User says things like:
- "Deployment Bot: generate deployment notes for 2026.3.08.12"
- "Generate release notes for 2026.3.08.12"
- "Create pre-deploy deployment notes for Fix Version …"
- "Automate release notes from Jira"

Any of those phrases means **check PRs, generate the Word file, upload it, and create the SHIPIT ticket**. The user does not need to mention SharePoint or Jira.

Create the SHIPIT Change Request as part of that generate run. A later prompt is only needed when they want Slack, or when they already have notes and ask only for the ticket:

- "Create the Jira ticket for 2026.3.09.16"
- "Create the SHIPIT change request"
- "Create jira ticket for this deployment"

Notify Slack **only** when the user later says things like:
- "Notify Slack"
- "Send the Slack message"
- "Post in the squad channels"

Do not post Slack because notes and the ticket finished. If they ask for notes **and** Slack in one prompt, still do generate → upload → SHIPIT first, then Slack only because Slack was part of that ask.

## Prerequisites

1. **Atlassian MCP** connected (`user-atlassian`)
2. Cloud ID: `5c639b1d-82c0-4932-96af-65d4921fcf57` (site `abcfinancial.atlassian.net`)
3. **Slack MCP** connected (`user-slack`) — Glofox workspace. Needed only when the user asks to notify Slack.
4. Python with `python-docx` (`py -3 -m pip install python-docx`)
5. Read [config.json](config.json) for defaults (team names, output dir)

## Scope split (quality rule)

### Agent fills from Jira (always)

- Version / Deployment Date (from Fix Version name)
- Centered header defaults from config (team, senior manager, SVP, environment) — confirm with user if changed
- **Deployment Owner** left blank (filled by the team per deployment)
- Document title **Deployment notes**
- **Deployment Summary** — the only summary section: brief description plus the four category counts (New Reports, Customizations, Looker Exits, Optimizations) from Jira labels
- **Reports / Dashboards Delivered** — one merged list with client, report name, and change description
- Affected Clients list
- Deployment Details table (one row per affected client)
- Ticket Details table: Ticket, clickable Ticket Link, Test, Status
- Testing Evidence heading only (no placeholder text)
- Tickets Excluded table (empty unless user explicitly asks to list excluded tickets)

### Team fills later (leave blank / TBD — do NOT invent)

- Deployment Owner
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
Deployment notes progress:
- [ ] 1. Confirm Fix Version + mode (pre-deploy default)
- [ ] 2. Fetch Jira tickets
- [ ] 3. Validate every ticket belongs to the configured Glofox projects (AN/PIC)
- [ ] 4. List fetched ticket keys and verify all attached PRs are merged
- [ ] 5. Normalize ticket rows (type/client/report)
- [ ] 6. Generate both Word docs via script (deployment notes and client-facing release notes)
- [ ] 7. Spot-check against sample quality
- [ ] 8. Save both locally AND upload both to SharePoint (`deployment bot release notes` / `YYYY-MM`) before telling the user you are done
- [ ] 9. Create SHIPIT Change Request (unless the user said not to), apply requested reporter/assignee, then move it to Review Ready
- [ ] 10. Tell the user the PR check passed for each included ticket, plus notes location and SHIPIT URL. Do not send Slack yet.
- [ ] 11. Notify Slack only when the user later explicitly asked — both live channels; never post otherwise
```

### Step 1 — Confirm inputs

Ask only if missing:
- **Fix Version** string (required), e.g. `2026.3.08.12`
- Optional override: Development Team
- Mode: `pre` (default) vs `post` (only if user provides deploy/test extras)

Do **not** default a Deployment Owner — leave that field blank unless the user explicitly provides a name.

### Step 2 — Fetch tickets

Use Atlassian MCP `searchJiraIssuesUsingJql`:

```
cloudId: 5c639b1d-82c0-4932-96af-65d4921fcf57
jql: fixVersion = "<VERSION>" ORDER BY key ASC
fields: summary, description, issuetype, status, labels, components, parent, project, fixVersions, assignee, customfield_10500
maxResults: 100
responseContentFormat: markdown
```

Paginate with `nextPageToken` if needed. If zero issues, stop and tell the user.

Exclude epics/parents that are only containers **only if** they have no useful deployable summary and user confirms; default = **include every issue on the Fix Version**.

Before checking PRs, read `config.json` → `jira_project_scope`. For the active `glofox` product, identify each fetched issue by `fields.project.key` (falling back to the issue-key prefix):

- `AN` → Glofox Analytics → `Analyze`
- `PIC` → Insights Customize → `Custom`

Stop and report the unsupported project keys if any included ticket belongs to another Jira project. Do not silently include it, classify it from its summary, or assume it belongs to Ignite. Ignite support is added later as a separate product entry with its approved Jira project keys.

### Step 3 — Enforce merged-PR gate

1. List all included Jira ticket keys fetched for the Fix Version.
2. Read the Jira development field named in `config.json` → `pull_request_gate.jira_development_field` (currently `customfield_10500`) on every included issue. It contains the GitHub PR count and aggregate state.
3. Run the deterministic check before the document builder:

```bash
py -3 scripts/check_pr_merge_status.py --jira-json <jira_VERSION.json> --config config.json
```

The canonical `build_from_jira_json.py` runs the same check internally, so generation cannot accidentally bypass it.

Pass only when every included ticket has at least one attached PR and all attached PRs are `MERGED`. A missing field means no verifiable attached PR and is a blocker. If blocked:

- Stop the entire combined workflow before writing JSON/DOCX, SharePoint upload, SHIPIT creation, or Slack notification.
- Tell the user each blocking ticket key and whether it has no attached PR or has a non-merged PR state.
- Do not treat Jira ticket status (for example Ready for Release or Done) as proof that a PR merged.
- Do not infer merge state from comments, descriptions, branches, or ticket labels.
- On a later request, refetch Jira and run the gate again.

If the user explicitly removed a ticket from this deployment, remove it from the saved Jira JSON before this check; the gate applies to the remaining included tickets.

### Step 4 — Normalize each ticket

| Field | Rule |
|---|---|
| Type | From `config.json` → active `jira_project_scope`: project `AN` → `Analyze`; project `PIC` → `Custom`. Other projects stop the workflow. |
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

### Step 5 — Generate document (always via script)

1. Save the raw Jira search result (the object with `issues[]`) to a JSON file, e.g. `jira_<VERSION>.json`.
2. If the user asked to remove tickets, delete those issues from that JSON's `issues[]` **before** running (that is the only allowed manual step). Do not touch anything else.
3. Run the canonical builder — it writes the deployment notes `.docx` and, beside it, `Release Notes <VERSION>.docx`:

```bash
py -3 scripts/build_from_jira_json.py --jira-json <jira_VERSION.json> --fix-version <VERSION> --config config.json --output-json "<output_dir>/Deployment Notes <VERSION>.pre.json" --output-docx "<output_dir>/Deployment Notes <VERSION>.docx"
```

Use both resulting `.docx` files **exactly as produced**. Never edit their text by hand. Scripts:
[scripts/build_from_jira_json.py](scripts/build_from_jira_json.py),
[scripts/normalize_tickets.py](scripts/normalize_tickets.py),
[scripts/generate_release_notes.py](scripts/generate_release_notes.py),
[scripts/generate_client_release_notes.py](scripts/generate_client_release_notes.py),
[scripts/upload_to_sharepoint.py](scripts/upload_to_sharepoint.py),
[scripts/build_shipit_change_request.py](scripts/build_shipit_change_request.py).

### Step 6 — Quality spot-check

Before handing to user:
- Document heading is `Deployment notes` on the deployment file
- The separate client-facing file heading is `Release Notes`
- Header labels are `Deployment Date` and `Deployment Owner`
- `Deployment Summary` is the only summary section and its sentence says “This deployment…”
- Ticket count in Ticket Details matches Jira fetch
- Deployment Summary contains the description sentence + count table with all four categories (zeros included), Total equal to the ticket count
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
- Filename: `Deployment Notes <VERSION>.docx`
- Client-facing file: `Release Notes <VERSION>.docx`, title `Release Notes`, one section per client, ticket keys are hyperlinks, References ends with `Fix version`, and there is no format-reference line

### Step 7 — Deliver and upload to SharePoint (same prompt — always)

This step is part of generate, not a follow-up. Finish it before the reply.

1. Keep both local `.docx` paths from Step 5.
2. Upload is **required for both files**. Do not leave either file only in Downloads. Do not ask the user to upload. Skip only if they said not to upload.
3. Read `config.json` → `sharepoint`. Layout is always:
   existing team library / `deployment bot release notes` / `YYYY-MM` / `Deployment Notes <VERSION>.docx` and `Release Notes <VERSION>.docx`
   Month folder comes from the Fix Version (`2026.3.09.16` → `2026-09`). Create the root folder and the month folder if they do not exist. Do not upload into `test deployment bot`. Keep using the existing SharePoint folder `deployment bot release notes`; only the document name and heading changed.
   `upload_method` decides the route:
   - `browser` (current): team library is **not** synced to File Explorer, so upload through the SharePoint web UI with the Playwright MCP browser.
   - `sync`: library is synced; `local_sync_path` holds the local folder.
4. Stage each file — Playwright can only read files under the repo root. Run this once per file:

```bash
py -3 scripts/upload_to_sharepoint.py --docx "<output_dir>/Deployment Notes <VERSION>.docx" --config config.json --fix-version <VERSION>
py -3 scripts/upload_to_sharepoint.py --docx "<output_dir>/Release Notes <VERSION>.docx" --config config.json --fix-version <VERSION>
```

With `upload_method: browser` this copies the `.docx` into `sharepoint.staging_dir` and prints the staged path plus `root_folder` and `month_folder`. With `sync` it copies into the synced library folder and you are done.

5. Browser upload steps (Playwright MCP), starting from `sharepoint.folder_url`:
   - Ensure folder `deployment bot release notes` exists (Create or upload → Folder). Open it.
   - Ensure the month folder (`YYYY-MM`) exists inside it. Open it.
   - Click **Create or upload → Files upload**, then `browser_file_upload` with each staged path.
   - Confirm both files via `browser_find` on the version string; SharePoint shows `Uploaded <file> to <month folder>`.
   - If the page lands on a Microsoft sign-in screen, ask the user to sign in to that browser window — never enter their password. A signed-in Playwright session does **not** need a new login on every run; only when that session expires.
6. Return both local paths, the SharePoint folder URL, and both confirmed file names.
7. Remind the user what they still fill post-deploy.

### Step 8 — Create SHIPIT Change Request (same generate run)

Do this after SharePoint upload unless the user explicitly said not to create the ticket. Also do it on a ticket-only prompt. Approved shape: [SHIPIT-17191](https://abcfinancial.atlassian.net/browse/SHIPIT-17191) (live) and [SHIPIT-17289](https://abcfinancial.atlassian.net/browse/SHIPIT-17289) (test).

1. Use the same Fix Version JSON as the deployment notes (fetch it first if this is a ticket-only request).
2. Reporter and assignee behavior:
   - Default: reporter is the Atlassian user authenticated in Cursor; assignee stays blank.
   - If the user explicitly supplies a reporter name and/or assignee name, call `lookupJiraAccountId` separately for each supplied name.
   - Require one unambiguous active Jira account per supplied name. If there are zero or multiple plausible matches, ask the user to clarify before creating the ticket.
   - Reporter and assignee may be different people and neither needs to be the authenticated user.
   - Do not silently copy the work-ticket assignee or infer either person.

3. Build the payload with the script — do **not** free-write field text. Add the resolved values only when supplied:

```bash
py -3 scripts/build_shipit_change_request.py --jira-json <jira_VERSION.json> --fix-version <VERSION> --config config.json

# Optional explicit people:
py -3 scripts/build_shipit_change_request.py ... \
  --reporter-name "<NAME>" --reporter-account-id "<ACCOUNT_ID>" \
  --assignee-name "<NAME>" --assignee-account-id "<ACCOUNT_ID>"
```

Add `--test-ticket` only when the user asked for a test ticket. That prefixes summary and every section with TEST TICKET / DO NOT ACTION.

4. Create the issue with Atlassian MCP `createJiraIssue`:
   - `cloudId` from config
   - `projectKey`: `SHIPIT`
   - `issueTypeName`: `Change Request`
   - `summary` and `description` from the script JSON
   - `contentFormat`: `markdown`
   - `additional_fields`: the script JSON object as-is
   - Set `assignee_account_id` from the script payload only when an explicit assignee was resolved; otherwise omit it so assignee stays Unassigned.
   - The script adds `additional_fields.reporter = {"accountId": "..."}` only when an explicit reporter was resolved; otherwise the authenticated Atlassian user remains reporter.
   - **Do not set Request Type.** Leave it blank. The API cannot stamp Manual Change.
   - Do not try to blank reporter or assignee.

5. For each work ticket key in `link.inward_keys`, call `createIssueLink`:
   - `type`: `Discovery - Connected`
   - `inwardIssue`: the PIC/AN key
   - `outwardIssue`: the new SHIPIT key

6. Move the new ticket to **Review Ready** (status id `14545` in `config.json` → `shipit.create_in_status`):
   - Call `getTransitionsForJiraIssue` for the new SHIPIT key
   - Apply `transitionJiraIssue` using the transition whose destination status name is `Review Ready`
   - If create-time `transition` is supported and you already know that transition id, you may pass it on `createJiraIssue` instead
   - If Review Ready is not in the transition list, tell the user the ticket was created and the API did not expose that transition. Do not guess a transition id. Do not use Begin Change, Canceled, approve, complete, or close.

7. Fetch the created ticket's `reporter`, `assignee`, and `status`. Verify explicit people were applied and status is Review Ready. Do not approve, complete, or close the ticket.

8. In the user-facing reply after notes + ticket, include all of:
   - **PR check passed** and each included ticket key with merged PRs
   - SharePoint file names for deployment notes and release notes, and the folder
   - SHIPIT URL, status **Review Ready**, reporter, and assignee (or Unassigned)
   - That Slack has **not** been sent, and they should ask when they want the squad message posted

Do not copy dummy TRZCX keys from older tickets. Verification is one line per work ticket plus the standard smoke test.

### Step 9 — Slack notify (only when the user later asks)

Read `config.json` → `slack`. Post with Slack MCP `slack_send_message` (`unfurl_app_links: true`). The post is sent as **whoever is signed into Slack in Cursor**, not as a bot and not as the deployment owner.

**Do not send on generate, upload, or SHIPIT.** Wait for a later prompt such as “Notify Slack” or “Send the Slack message”. These two channels are live. Training and format checks are not a send.

Channels (always both, when sending):

| Channel | ID | CC |
|---|---|---|
| `#insights-customize-squad` | `C08HB93PEVD` | Sushma, Sai Anirudh Karre, Zeke Brustkern, Eoin George (`<@U08LDAQ7SDV> <@U0BSG4ABZC0> <@U083R8TP1J9> <@U01H0UL5JGP>`) |
| `#customize-bi-buddies` | `C08KM1USMM1` | Sushma only (`<@U08LDAQ7SDV>`) |

CC rule: **Sushma only in `#customize-bi-buddies`.** **Sushma, Sai, Zeke, and Eoin in `#insights-customize-squad`.** Do **not** CC Trent. Do not swap these.

Message body (same wording in both channels except the CC line):

```
Hello Team,

Our upcoming deployment is scheduled for {weekday}, {month} {day}, {year}.
Deployment notes, release notes, and the deployment ticket are below for reference:

Deployment notes download: [Deployment Notes {VERSION}.docx]({sharepoint_download_url})
Release notes download: [Release Notes {VERSION}.docx]({release_notes_download_url})
SharePoint folder: [Open {YYYY-MM}]({sharepoint_folder_url})
Service Desk: [{SHIPIT-key}](https://abcfinancial.atlassian.net/browse/{SHIPIT-key})

Thanks!
```

Append a CC line per channel:

- `#insights-customize-squad`: `CC: <@U08LDAQ7SDV> <@U0BSG4ABZC0> <@U083R8TP1J9> <@U01H0UL5JGP>`
- `#customize-bi-buddies`: `CC: <@U08LDAQ7SDV>`

Date comes from the Fix Version (`2026.3.09.16` → Wednesday, September 16, 2026). Include both document downloads and the folder link:

- `sharepoint_download_url`: direct `Deployment Notes <VERSION>.docx` URL with `?download=1`
- `release_notes_download_url`: direct `Release Notes <VERSION>.docx` URL with `?download=1` (`sharepoint_release_notes_download_url` on the SHIPIT payload)
- `sharepoint_folder_url`: SharePoint `Forms/AllItems.aspx` view whose `id` points to the exact `deployment bot release notes / YYYY-MM` folder

Do not reuse the download URL for the folder link. Confirm the uploaded file exists before sending. SHIPIT key is the ticket created (or the live ticket the user named). All links must be markdown links, not plain URLs.

Do not post to DMs for live notify. Do not use `slack_send_message_draft` unless the user asks for a draft. Return both message permalinks after sending.

## How each section is produced (reference only — the scripts do this)

These are implemented in the scripts. They are documented here so you can verify output, **not** so you can generate it yourself.

- **Title**: `Deployment notes`
- **Header**: `Deployment Date` and `Deployment Owner` (not Release Date / Release Owner).
- **Deployment Summary**: `size_sentence()` writes the description + counts sentence (e.g. "This deployment delivers 5 new reports, 1 customization, and 1 Looker exit for Glofox Analyze, Jazzercise, and Lift."), and `count_categories()` produces the `category_counts` rendered as the count table under the same heading. Zero-count categories are omitted from the sentence but still shown in the table. There is no separate Custom Clients Summary or Standard & Custom Summary.
- **Reports / Dashboards Delivered**: one bullet per ticket—`{Client} - {Report name} - {change description}`. The change description comes from the concise ticket summary; do not paste long Jira user-story boilerplate.
- **Affected Clients**: the distinct client names in the deployment — `Glofox Analyze` when there are AN tickets, plus each custom client.
- **Deployment Details**: one row per affected client; manual deployment fields blank pre-deploy.
- **Ticket Details**: one row per ticket with Ticket, clickable Ticket Link, Test, Status; Test and Status blank pre-deploy.

The scripts never invent features not present on tickets, and neither should you.

## Failure modes

- Atlassian Unauthorized → ask user to reconnect Atlassian MCP
- Slack Unauthorized → ask user to reconnect Slack MCP; do not post anywhere else as a workaround
- Fix Version not found / 0 issues → verify exact version string in Jira
- Jira project outside configured AN/PIC Glofox scope → stop and report the project key; do not treat it as Ignite without an approved mapping
- Ambiguous client on PIC → list ticket keys and ask once
- Missing PR or non-merged PR → pause before all output and list blocking ticket keys/states
- Reporter/assignee name has no unique active Jira match → ask the user to clarify; do not create the SHIPIT ticket with a guessed account
- SHIPIT Review Ready transition missing from `getTransitionsForJiraIssue` → tell the user; leave the ticket in its created status rather than guessing a transition

## References

- Document sections & JSON schema: [document-structure.md](document-structure.md)
- Sample template: [templates/Release Notes SAMPLE.docx](templates/Release%20Notes%20SAMPLE.docx)
- Defaults: [config.json](config.json)
