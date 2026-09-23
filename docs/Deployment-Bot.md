# Deployment Bot — Functional & Operational Documentation

**Product:** Deployment Bot (Cursor Agent Skill)
**Team:** Customize BI / Fitness BI
**Scope:** Pre-deployment release documentation and communication for Fitness BI and Customize BI production deployments
**Status:** In use (deployment notes, SharePoint upload, SHIPIT change request, Slack notification)
**Skill location:** `.cursor/skills/deployment-bot/`

---

## 1. Purpose

Every Fitness BI / Customize BI production deployment requires the same four pre-deployment artefacts:

1. A deployment notes document in the approved team format
2. That document stored in the team SharePoint library
3. A SHIPIT Change Request in Jira for the deployment
4. A notification to the squad Slack channels

Deployment Bot produces all four from a single input — the Jira **Fix Version** — so the developer reviews output instead of assembling it by hand.

---

## 2. Capabilities

| # | Capability | Trigger | Output |
|---|---|---|---|
| 1 | Generate deployment notes | "Generate deployment notes for `<VERSION>`" | `Deployment Notes <VERSION>.docx` |
| 2 | Upload to SharePoint | Automatic with capability 1 | File in `deployment bot release notes / YYYY-MM` |
| 3 | Create SHIPIT Change Request | Automatic with capability 1 | SHIPIT ticket in Review Ready, linked to the work tickets |
| 4 | Notify Slack | "Notify Slack" (later prompt) | Message in both squad channels |

**Job boundaries**

- Lineage is fixed: **PR merge check → deployment notes → SharePoint → SHIPIT ticket**. Then stop.
- Generate, SharePoint upload, and SHIPIT are **one job**. The bot never stops after producing the `.docx`.
- A merged-PR check is a hard prerequisite. Any missing or non-merged PR pauses the entire combined workflow before output.
- After notes and the ticket exist, the bot **explicitly reports** that each included ticket’s PR is merged, plus the SharePoint location and SHIPIT URL.
- Slack is a **separate later job**. It runs only when a Slack notification is explicitly requested. Finishing notes and SHIPIT is not a send.
- Skip upload only if the user says not to upload. Skip SHIPIT only if the user says not to create the ticket.

---

## 3. Inputs and derived values

The only required input is the **Fix Version**, in the format `YYYY.Q.MM.DD`.

| Segment | Meaning | Example (`2026.3.09.16`) |
|---|---|---|
| 1 | Year | 2026 |
| 2 | Quarter / release cycle | 3 |
| 3 | Month | 09 |
| 4 | Day | 16 |

Derived automatically:

| Derived value | Source | Example |
|---|---|---|
| Deployment date | Jira `fixVersions[].releaseDate`, else the version string | 16-September-2026 |
| SharePoint month folder | Year and month of the version | `2026-09` |
| Document file name | Version | `Deployment Notes 2026.3.09.16.docx` |
| Slack deployment date | Version | Wednesday, September 16, 2026 |

---

## 4. Processing logic

### 4.1 Ticket retrieval

Tickets are read from Jira through the Atlassian MCP using
`fixVersion = "<VERSION>" ORDER BY key ASC`. All issues on the Fix Version are included by default.

### 4.2 Classification

The active product is configured in `config.json` → `jira_project_scope`. For Glofox, every fetched ticket is identified by Jira project key before processing:

| Jira board/project | Key | Type | Client |
|---|---|---|---|
| Glofox Analytics | `AN` | Analyze | `Glofox Analyze` |
| Insights Customize | `PIC` | Custom | Parsed from the summary prefix (for example `Jetts - …` → Jetts) |

The report column carries only the report, dashboard, semantic model, or dataset name. Analyze tickets with no named asset are recorded as `All Reports`.

Any other project stops the workflow and is reported to the user. It is not silently treated as Glofox or Ignite. Future Ignite support is added as a separate product configuration with its approved Jira project keys and type mappings.

### 4.3 Pull-request merge gate

Each Jira search includes development field `customfield_10500`. Before the canonical builder writes JSON or DOCX, `check_pr_merge_status.py` verifies that:

- every included ticket has at least one attached PR; and
- all attached PRs are in Jira's `MERGED` aggregate state.

Missing PR data, open PRs, declined PRs, or a mixed state block generation. The bot lists each blocking ticket and stops before document creation, SharePoint upload, SHIPIT creation, or Slack notification. Jira workflow status alone is not accepted as proof of merge.

### 4.4 Release sizing

Release size is reported in four categories, driven by Jira **labels**:

| Category | Example labels |
|---|---|
| New Reports | `NewRequirement`, `New_Report` |
| Customizations | `Report_Enhancement`, `Enhancement`, `Customize` |
| Looker Exits | `Looker-Exit` |
| Optimizations | `Optimize`, `Performance` |

Each ticket is counted exactly once, so the category total equals the ticket count. Where a ticket carries labels from more than one category, the priority order in `config.json` decides, with Looker Exit taking precedence. If no label maps to a category, the build prints a warning naming the ticket, and the correct label should be added in Jira rather than editing the document.

### 4.5 Deterministic generation

The Word document is produced only by the scripts in `.cursor/skills/deployment-bot/scripts/`. The agent does not reword, reformat, or hand-edit generated content. If output needs to change, the script is changed — never the document.

---

## 5. Deployment notes document structure

| # | Section | Content |
|---|---|---|
| 1 | Title | Deployment notes |
| 2 | Header block | Version, Deployment Date, Development Team, Senior Manager, SVP, Environment; Deployment Owner left blank |
| 3 | Deployment Summary | “This deployment…” sentence plus the four category counts and total |
| 4 | Reports / Dashboards Delivered | One line per ticket: client, report, change description |
| 5 | Affected Clients | Distinct client names in the release |
| 6 | Deployment Details | One row per client; owner, status and deployment ID blank |
| 7 | Ticket Details | Ticket, clickable Jira link, Test, Status |
| 8 | Testing Evidence | Heading only |
| 9 | Tickets Excluded from Deployment | Empty unless exclusions are explicitly requested |

### Fields completed by the team after deployment

- Deployment Owner
- Deployment Owner, Status, Deployment ID & Time
- Test and Status in Ticket Details
- Testing evidence

The bot never invents these values.

### Removing a ticket

A request to remove a ticket from the deployment omits it from all included sections and leaves the exclusions table empty. The ticket is listed under **Tickets Excluded from Deployment** only when that is explicitly requested.

---

## 6. SharePoint storage

| Item | Value |
|---|---|
| Library | Customize team Release Notes library |
| Root folder | `deployment bot release notes` |
| Sub-folder | `YYYY-MM`, derived from the Fix Version |
| File name | `Deployment Notes <VERSION>.docx` |

The library is not synced to File Explorer, so the upload is performed through the SharePoint web interface using the Playwright browser. Root and month folders are created when missing.

---

## 7. SHIPIT Change Request

| Attribute | Value |
|---|---|
| Project | SHIPIT |
| Issue type | Change Request |
| Reporter | Authenticated Atlassian user by default; explicit user-supplied name overrides it |
| Assignee | Blank by default; explicit user-supplied name sets the deployment owner |
| Request Type | Left blank — cannot be set through the API |
| Change type / risk | Normal / Medium |
| Approver group | Insights Customize Approvers |
| Deployment window | 10:30–12:30 IST |
| Linked tickets | Each PIC / AN ticket on the Fix Version, using `Discovery - Connected` |
| Status after create | Review Ready |

The change request also carries the SharePoint link to the deployment notes. It is created in the same generate run as the Word document (unless the user said not to create the ticket). After create, the bot moves the ticket to **Review Ready**. It does not approve, complete, or close the ticket.

Reporter and assignee can be different people and neither must be the developer running the agent. For explicit names, the bot resolves each person with Jira account lookup, requires one unambiguous active match, passes the reporter account in `additional_fields.reporter`, and passes the assignee through `assignee_account_id`. It then verifies both fields on the created ticket.

---

## 8. Slack notification

Sent only on a later explicit request, after notes and the SHIPIT ticket already exist. Never sent automatically when generation finishes. Posted to both channels:

| Channel | Type | CC |
|---|---|---|
| `#insights-customize-squad` | Public | Sushma, Sai Anirudh Karre, Zeke Brustkern, Eoin George |
| `#customize-bi-buddies` | Private | Sushma |

Message format:

```
Hello Team,

Our upcoming deployment is scheduled for <weekday>, <month> <day>, <year>.
Deployment notes and the deployment ticket are below for reference:

Deployment notes download: <Deployment Notes VERSION.docx direct-download link>
SharePoint folder: <exact deployment bot release notes / YYYY-MM folder link>
Service Desk: <SHIPIT key link>

Thanks!
CC: <mentions per channel>
```

**Sender identity:** the message is posted by the Slack account signed in to Cursor, not by a bot account and not automatically by the deployment owner. If a single "Deployment Bot" sender name is required, a dedicated Slack app with a bot token would need to be created and installed by a workspace administrator.

---

## 9. Prerequisites for each user

| Requirement | Purpose |
|---|---|
| Cursor | Runs the agent |
| Access to this repository | Provides the Deployment Bot skill |
| Jira access to `abcfinancial.atlassian.net` | AN, PIC and SHIPIT projects |
| SharePoint access to the Customize Release Notes library | Document storage |
| Slack membership of both squad channels | Notification step |
| Node.js | Required for the Playwright MCP |
| Python 3 with `python-docx` | Word document generation |

MCP servers are configured per user in Cursor and are **not** distributed with the repository:

| MCP | Used for | Required |
|---|---|---|
| Atlassian | Ticket retrieval and SHIPIT creation | Yes |
| Playwright | SharePoint upload through the browser | Yes, for upload |
| Slack | Squad notifications | Only for the Slack step |

---

## 10. Onboarding a new user

1. Clone the repository and open that folder in Cursor. The skill loads only when this repository is open.
2. Install the Python dependency:

   ```powershell
   py -3 -m pip install python-docx
   ```

3. In **Settings → MCP**, add and connect Atlassian, Playwright, and Slack using the user's own corporate accounts. For Slack, select the **Glofox** workspace.
4. Run the first deployment notes generation. If a Microsoft sign-in page appears in the Playwright browser, sign in there. Passwords are never entered into the chat.

No retraining is required; the playbook is stored in the repository.

---

## 11. Standard usage

**Deployment notes, SharePoint upload, and SHIPIT ticket**

```text
Generate deployment notes for Fix Version 2026.3.09.23
```

That run checks PRs, writes and uploads the Word file, creates the SHIPIT ticket in Review Ready, and reports that each included PR is merged. Slack is not sent yet.

**Change request only** (if notes already exist)

```text
Create the Jira ticket for this deployment
```

**Change request with people overrides**

```text
Create the Jira ticket with Reporter Jane Smith and Assignee John Doe
```

**Slack notification**

```text
Notify Slack for this deployment
```

**Combined (notes + ticket still do not send Slack)**

```text
Generate deployment notes for 2026.3.09.23 and create the Jira ticket
```

**Excluding a ticket**

```text
Generate deployment notes for 2026.3.09.23, remove AN-5468 from deployment
```

---

## 12. Repository layout

```text
.cursor/skills/deployment-bot/
  SKILL.md                        # Agent playbook
  config.json                     # Defaults: team, Jira, SharePoint, SHIPIT, Slack
  document-structure.md           # Document sections and JSON schema
  scripts/
    build_from_jira_json.py       # Canonical build entry point
    check_pr_merge_status.py      # Hard gate for attached/merged ticket PRs
    normalize_tickets.py          # Classification and field extraction
    generate_release_notes.py     # Word document rendering
    upload_to_sharepoint.py       # Upload staging and routing
    build_shipit_change_request.py# Change request payload
  templates/
    Release Notes SAMPLE.docx
tests/
  test_release_notes.py           # Automated checks
docs/
  Deployment-Bot.md               # This document
```

Canonical build command:

```bash
py -3 scripts/build_from_jira_json.py --jira-json <jira_VERSION.json> --fix-version <VERSION> --config config.json --output-json "<output_dir>/Deployment Notes <VERSION>.pre.json" --output-docx "<output_dir>/Deployment Notes <VERSION>.docx"
```

Test suite:

```bash
py -3 -m unittest tests.test_release_notes
```

---

## 13. Configuration and maintenance

All defaults are held in `.cursor/skills/deployment-bot/config.json`.

| Change | Location |
|---|---|
| Leadership names, team name, environment | `defaults` |
| New Jira labels for category counts | `summary_categories.labels` |
| Active product and allowed Jira projects | `jira_project_scope` |
| PR merge requirements / Jira development field | `pull_request_gate` |
| SharePoint library, folder names, upload method | `sharepoint` |
| SHIPIT approvers, window, risk settings | `shipit` |
| Slack channels, mentions, message template | `slack` |

Document layout changes are made in the scripts and `document-structure.md`, with the test suite re-run afterwards.

---

## 14. Troubleshooting

| Symptom | Action |
|---|---|
| Jira returns unauthorized | Reconnect the Atlassian MCP in Cursor |
| Fix Version returns no issues | Confirm the exact version string in Jira |
| Generation pauses on PR verification | Attach a PR to each blocking ticket, merge all attached PRs, then rerun |
| Reporter or assignee is ambiguous | Supply a more specific Jira display name or email |
| Unsupported Jira project is found | Add only approved project mappings; do not assume it is Ignite |
| Custom client shows as Unknown | Correct the PIC summary prefix, or supply the client name |
| Category warning during build | Add the correct label in Jira and regenerate |
| SharePoint shows a Microsoft sign-in page | Sign in within the Playwright browser window |
| Word file cannot be written | Close the document if open, and confirm the output folder is available |
| Slack unauthorized | Reconnect the Slack MCP; do not post elsewhere as a workaround |

---

## 15. Operating principles

- Generated content is produced by scripts only; documents are never hand-edited.
- Fields owned by the team after deployment are left blank rather than estimated.
- SHIPIT is created with the generate run unless the user says not to create the ticket.
- Slack is never taken implicitly; wait for a later “Notify Slack” prompt.
- Jira and Slack actions are attributed to the signed-in user, which should be understood before running the agent on someone else's behalf.
