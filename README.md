# Deployment Bot

**Deployment Bot** is a Cursor Agent Skill that builds **pre-deployment deployment notes** from Jira Fix Versions, writes a Word doc matching the team template, and copies it into the team SharePoint folder.

**Repo:** [glofoxinc/fitness-bi-release-notes](https://github.com/glofoxinc/fitness-bi-release-notes)  
**Skill path:** `.cursor/skills/deployment-bot/`  
**Full documentation:** [docs/Deployment-Bot.md](docs/Deployment-Bot.md)

## What Deployment Bot does

1. Reads all Jira tickets on a Fix Version (deployment date, e.g. `2026.3.08.12`)
2. Identifies Glofox Jira projects and accepts only **Glofox Analytics** (`AN`) and **Insights Customize** (`PIC`)
3. Requires every included ticket to have at least one attached PR and all attached PRs merged
4. Classifies **Analyze** (`AN`) vs **Custom** (`PIC`) and extracts client / report names
5. Generates a Word deployment notes doc (Cambria; body 12 / headings 14)
6. Leaves blank for the team to fill after deploy: Deployment IDs, Test by, Sanity answers; Screenshots is heading-only

**Lineage:** check that every included ticket has a merged PR → generate deployment notes → upload to SharePoint → create the SHIPIT ticket in Review Ready. Slack is a later step.

SharePoint upload and the SHIPIT Change Request happen in the same generate run. The bot then tells you the PR check passed (each ticket, merged), where the notes live, and the SHIPIT URL. It does **not** post to Slack until you ask.

If any included ticket has no attached PR or a PR that is not merged, the bot pauses before generating, uploading, or creating SHIPIT, and lists the blocking tickets.

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
Deployment Bot: generate deployment notes for Fix Version 2026.3.08.12
```

That one prompt checks PRs, generates the Word file, uploads it to `deployment bot release notes` / `YYYY-MM`, and creates the SHIPIT Change Request in **Review Ready**. You do not need a second prompt for SharePoint or the ticket.

A ticket-only prompt still works if notes already exist:

```text
Create the Jira ticket for Fix Version 2026.3.09.16
```

Reporter defaults to the Atlassian user connected in Cursor and assignee defaults to blank. You can override either or both:

```text
Create the Jira ticket with Reporter Jane Smith and Assignee John Doe
```

The bot resolves the supplied names to Jira accounts and asks for clarification if a name is ambiguous.

Notify Slack **only** when you later ask (both `#insights-customize-squad` and `#customize-bi-buddies`; Sushma + Sai + Zeke + Eoin in the squad channel, Sushma only in Buddies):

```text
Notify Slack for this deployment
```

Do not expect Slack posts from generate notes / create ticket. After that run the bot should say the PRs are merged and wait for this prompt.

Or simply:

```text
Generate deployment notes for Fix Version 2026.3.08.12
```

### Remove a ticket from the document

Fix Version can stay on the ticket in Jira. Tell Deployment Bot in the prompt:

```text
Generate deployment notes for Fix Version 2026.3.08.12, remove AN-5468 from deployment
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
| **Deployment Owner** | Left blank unless you provide a name |
| **Jira project scope** | Glofox accepts AN and PIC only; unknown projects stop instead of being guessed |
| **PR merge gate** | Every included ticket needs at least one attached PR and all attached PRs merged; after notes + ticket the bot states that result |
| **SHIPIT reporter / assignee** | Defaults remain authenticated reporter + blank assignee; explicit names override them |
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
    check_pr_merge_status.py
    generate_release_notes.py
    build_from_jira_json.py
    upload_to_sharepoint.py
    build_shipit_change_request.py
  templates/
    Release Notes SAMPLE.docx
```

## Team notes

- Leave **Deployment Owner** blank unless the user provides a name for that deployment
- Do **not** invent Deployment IDs, testers, or screenshots in pre-deploy mode
- **Screenshots** section is heading-only; paste images after deploy
- Custom client names are parsed from PIC ticket summaries
- Ignite can be added later as a separate configured product once its Jira project keys are approved
- Update `config.json` defaults if leadership names change
- Open this repo in Cursor so the project skill (Deployment Bot) is loaded

## License

Internal use for Glofox / ABC Fitness teams.
