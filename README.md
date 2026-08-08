# NoteBot

Comic little release-notes buddy for the Customize BI / Fitness BI team.

**NoteBot** is a Cursor Agent Skill that builds **pre-deployment release notes** from Jira Fix Versions and writes a Word doc matching the team template.

**Repo:** [glofoxinc/fitness-bi-release-notes](https://github.com/glofoxinc/fitness-bi-release-notes)  
**Skill path:** `.cursor/skills/notebot/`

## What NoteBot does

1. Reads all Jira tickets on a Fix Version (deployment date, e.g. `2026.3.08.12`)
2. Classifies **Analyze** (`AN`) vs **Custom** (`PIC`) and extracts client / report names
3. Generates a Word release notes doc (Cambria; body 12 / headings 14)
4. Leaves blank for the team to fill after deploy: Deployment IDs, Test by, Screenshots, Sanity answers

SharePoint auto-upload is planned; for now upload the generated `.docx` manually to the team Release Notes folder.

## Prerequisites (each teammate)

1. **Cursor**
2. **Atlassian MCP** connected in Cursor (Jira access to `abcfinancial.atlassian.net`)
3. **Python 3** + `python-docx`:

```powershell
py -3 -m pip install python-docx
```

4. Open **this repo** in Cursor (so NoteBot is picked up)

## How to use

In Cursor chat:

```text
NoteBot: generate release notes for Fix Version 2026.3.08.12
```

Or simply:

```text
Generate release notes for Fix Version 2026.3.08.12
```

## Repo layout

```text
.cursor/skills/notebot/
  SKILL.md                 # NoteBot playbook
  config.json              # Defaults (team names, Jira cloud id, output dir)
  document-structure.md    # Doc sections + JSON schema
  scripts/
    normalize_tickets.py
    generate_release_notes.py
    build_from_jira_json.py
  templates/
    Release Notes SAMPLE.docx
```

## Team notes

- Leave **Release Owner** blank unless the user provides a name for that deployment
- Do **not** invent Deployment IDs, testers, or screenshots in pre-deploy mode
- Custom client names are parsed from PIC ticket summaries
- Update `config.json` defaults if leadership names change

## License

Internal use for Glofox / ABC Fitness teams.
