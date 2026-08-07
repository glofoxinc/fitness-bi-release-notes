# Fitness BI Release Notes

Cursor Agent Skill that generates Customize BI / Fitness BI **pre-deployment release notes** from Jira Fix Versions and writes a Word document matching the team template.

**Org:** [glofoxinc](https://github.com/glofoxinc)  
**Skill path (in this repo):** `.cursor/skills/fitness-bi-release-notes/`

## What it does

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

4. Open **this repo** in Cursor (so the project skill is picked up)

## How to use

In Cursor chat:

```text
Generate release notes for Fix Version 2026.3.08.12
```

Optional:

```text
Generate pre-deploy release notes for Fix Version 2026.3.08.12
```

The agent follows `.cursor/skills/fitness-bi-release-notes/SKILL.md`.

## Repo layout

```text
.cursor/skills/fitness-bi-release-notes/
  SKILL.md                 # Agent playbook
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

- Do **not** invent Deployment IDs, testers, or screenshots in pre-deploy mode
- Custom client names are parsed from PIC ticket summaries (known clients listed in `normalize_tickets.py`)
- Update `config.json` defaults if Release Owner / leadership names change

## License

Internal use for Glofox / ABC Fitness teams.
