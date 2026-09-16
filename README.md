# Deployment Bot

**Deployment Bot** is a Cursor Agent Skill that builds **pre-deployment release notes** from Jira Fix Versions, writes a Word doc matching the team template, and copies it into the team SharePoint folder.

**Repo:** [glofoxinc/fitness-bi-release-notes](https://github.com/glofoxinc/fitness-bi-release-notes)  
**Skill path:** `.cursor/skills/deployment-bot/`  
**Full documentation:** [docs/Deployment-Bot.md](docs/Deployment-Bot.md)

## What Deployment Bot does

1. Reads all Jira tickets on a Fix Version (deployment date, e.g. `2026.3.08.12`)
2. Classifies **Analyze** (`AN`) vs **Custom** (`PIC`) and extracts client / report names
3. Generates a Word release notes doc (Cambria; body 12 / headings 14)
4. Leaves blank for the team to fill after deploy: Deployment IDs, Test by, Sanity answers; Screenshots is heading-only

SharePoint upload: after generate, the bot creates `deployment bot release notes` / `YYYY-MM` (from the Fix Version) under the team Release Notes library and uploads the `.docx` there.

## Prerequisites (each teammate)

1. **Cursor**
2. **Atlassian MCP** connected in Cursor (Jira access to `abcfinancial.atlassian.net`)
3. **Python 3** + `python-docx`:

```powershell
py -3 -m pip install python-docx
```

4. Open **this repo** in Cursor (so Deployment Bot is picked up)

## How to use

In Cursor chat:

```text
Deployment Bot: generate release notes for Fix Version 2026.3.08.12
```

That one prompt generates the Word file **and** uploads it to `deployment bot release notes` / `YYYY-MM`. You do not need a second prompt for SharePoint.

Create the SHIPIT Change Request only when you ask, for example:

```text
Create the Jira ticket for Fix Version 2026.3.09.16
```

Notify Slack only when you ask (both `#insights-customize-squad` and `#customize-bi-buddies`; Sushma + Trent in the squad channel, Sushma only in Buddies):

```text
Notify Slack for this deployment
```

Do not expect Slack posts from generate-only or generate+Jira prompts.

Or simply:

```text
Generate release notes for Fix Version 2026.3.08.12
```

### Remove a ticket from the document

Fix Version can stay on the ticket in Jira. Tell Deployment Bot in the prompt:

```text
Generate release notes for Fix Version 2026.3.08.12, remove AN-5468 from deployment
```

- Ticket is **omitted** from Key Highlights, Dashboards/Reports, Change Details, etc.
- **Tickets Excluded from Deployment** stays **empty**

Only if you want it listed in that section, say so explicitly:

```text
Remove AN-5468 from deployment and list it under Tickets Excluded from Deployment
```

## Important rules (agent is trained on these)

Deployment Bot follows `.cursor/skills/deployment-bot/SKILL.md` — that file is the agent playbook.

| Rule | Behavior |
|---|---|
| **Release Owner** | Left blank unless you provide a name |
| **Key Highlights** | Client + concise ticket info |
| **Dashboards / Reports & table Report column** | Report / dashboard / model name only (`All Reports` when Analyze has no named asset) |
| **Screenshots** | Heading only — no placeholder text underneath |
| **Remove from deployment** | Drop from main sections only; do **not** auto-add to Tickets Excluded |
| **List under Excluded** | Only when you explicitly ask |

## Repo layout

```text
.cursor/skills/deployment-bot/
  SKILL.md                 # Deployment Bot playbook (agent training)
  config.json              # Defaults (team names, Jira, SharePoint, SHIPIT, Slack)
  document-structure.md    # Doc sections + JSON schema
  scripts/
    normalize_tickets.py
    generate_release_notes.py
    build_from_jira_json.py
    upload_to_sharepoint.py
    build_shipit_change_request.py
  templates/
    Release Notes SAMPLE.docx
```

## Team notes

- Leave **Release Owner** blank unless the user provides a name for that deployment
- Do **not** invent Deployment IDs, testers, or screenshots in pre-deploy mode
- **Screenshots** section is heading-only; paste images after deploy
- Custom client names are parsed from PIC ticket summaries
- Update `config.json` defaults if leadership names change
- Open this repo in Cursor so the project skill (Deployment Bot) is loaded

## License

Internal use for Glofox / ABC Fitness teams.
