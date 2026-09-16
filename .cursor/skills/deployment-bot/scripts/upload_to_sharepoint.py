"""Put generated release notes where the SharePoint upload can pick them up.

Two modes, chosen by sharepoint.upload_method in config.json:

- `sync`: copy straight into the OneDrive-synced library folder, creating
  sharepoint.folder_name when missing. Needs sharepoint.local_sync_path.
- `browser`: stage a copy inside the repo (sharepoint.staging_dir) because the
  Playwright browser can only read files under the repo root. The agent then
  uploads that staged file through the SharePoint web UI.

  py -3 scripts/upload_to_sharepoint.py --docx "<path>.docx" --config config.json
  py -3 scripts/upload_to_sharepoint.py --docx "<path>.docx" --config config.json --stage-only
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def month_folder_from_version(fix_version: str) -> str:
    """YYYY.Q.MM.DD → YYYY-MM (e.g. 2026.3.09.16 → 2026-09)."""
    parts = (fix_version or "").strip().split(".")
    if len(parts) < 3:
        raise ValueError(f"Unexpected fix version format: {fix_version}")
    year, month = parts[0], int(parts[2])
    if not (1 <= month <= 12):
        raise ValueError(f"Unexpected month in fix version: {fix_version}")
    return f"{year}-{month:02d}"


def relative_upload_folders(sharepoint: dict, fix_version: str) -> tuple[str, str]:
    root_folder = (sharepoint.get("folder_name") or "deployment bot release notes").strip()
    return root_folder, month_folder_from_version(fix_version)


def destination_dir(sharepoint: dict, fix_version: str) -> Path:
    sync = (sharepoint.get("local_sync_path") or "").strip()
    if not sync:
        raise ValueError(
            "sharepoint.local_sync_path is empty. Paste the team SharePoint "
            "folder URL (or the synced OneDrive path) into config.json first."
        )
    root_folder, month_folder = relative_upload_folders(sharepoint, fix_version)
    return Path(sync) / root_folder / month_folder


def upload_docx(
    docx_path: Path,
    sharepoint: dict,
    *,
    fix_version: str,
    require_enabled: bool = True,
) -> Path:
    if require_enabled and not sharepoint.get("enabled"):
        raise ValueError(
            "sharepoint.enabled is false. Set it true after the team folder path is confirmed."
        )
    src = Path(docx_path)
    if not src.is_file():
        raise FileNotFoundError(f"Release notes file not found: {src}")
    dest_dir = destination_dir(sharepoint, fix_version)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    return dest


def stage_for_browser(docx_path: Path, sharepoint: dict, repo_root: Path) -> Path:
    """Copy the .docx inside the repo so the Playwright browser can upload it."""
    src = Path(docx_path)
    if not src.is_file():
        raise FileNotFoundError(f"Release notes file not found: {src}")
    staging = repo_root / (sharepoint.get("staging_dir") or ".playwright-mcp")
    staging.mkdir(parents=True, exist_ok=True)
    dest = staging / src.name
    shutil.copy2(src, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Upload or stage release notes for SharePoint.")
    parser.add_argument("--docx", required=True, help="Path to generated .docx")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument(
        "--fix-version",
        required=True,
        help="Fix Version (YYYY.Q.MM.DD) used to pick the month subfolder.",
    )
    parser.add_argument(
        "--stage-only",
        action="store_true",
        help="Stage into the repo for browser upload instead of copying to a synced folder.",
    )
    parser.add_argument(
        "--allow-disabled",
        action="store_true",
        help="Copy even when sharepoint.enabled is false (used for first-path tests).",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    sharepoint = config.get("sharepoint") or {}
    repo_root = Path(__file__).resolve().parents[4]

    try:
        root_folder, month_folder = relative_upload_folders(sharepoint, args.fix_version)
        if args.stage_only or sharepoint.get("upload_method") == "browser":
            dest = stage_for_browser(Path(args.docx), sharepoint, repo_root)
        else:
            dest = upload_docx(
                Path(args.docx),
                sharepoint,
                fix_version=args.fix_version,
                require_enabled=not args.allow_disabled,
            )
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(dest)
    print(f"root_folder={root_folder}")
    print(f"month_folder={month_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
