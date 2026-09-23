"""Check GitHub for updates and apply in-place without full reinstall."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

REPO_OWNER = "karalik19-a11y"
REPO_NAME = "rf-political-trends-analyzer"
BRANCH = "main"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"

# Keep user data when updating
PRESERVE_NAMES = {"data", "exports", "venv", ".git"}


def app_root() -> Path:
    """Project root (parent of src/)."""
    return Path(__file__).resolve().parent.parent


def read_local_version() -> str:
    vf = app_root() / "VERSION"
    if vf.exists():
        return vf.read_text(encoding="utf-8").strip()
    return "0.0.0"


def fetch_remote_info() -> Dict[str, Any]:
    """Latest commit on main + optional VERSION file content."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "RF-PTA-Updater"}
    commit_url = f"{GITHUB_API}/commits/{BRANCH}"
    r = requests.get(commit_url, headers=headers, timeout=30)
    r.raise_for_status()
    commit = r.json()
    sha = commit["sha"][:7]
    message = (commit.get("commit") or {}).get("message", "")
    date = ((commit.get("commit") or {}).get("committer") or {}).get("date", "")

    remote_version = None
    try:
        ver_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/VERSION"
        vr = requests.get(ver_url, headers=headers, timeout=15)
        if vr.status_code == 200:
            remote_version = vr.text.strip()
    except Exception:
        pass

    return {
        "sha": sha,
        "full_sha": commit["sha"],
        "message": message.split("\n")[0][:120],
        "date": date,
        "version": remote_version or sha,
    }


def check_update() -> Tuple[bool, Dict[str, Any]]:
    """
    Returns (update_available, info).
    Compares local VERSION and optional local commit marker.
    """
    local_ver = read_local_version()
    remote = fetch_remote_info()
    marker = app_root() / ".update_sha"
    local_sha = marker.read_text(encoding="utf-8").strip() if marker.exists() else ""

    # Update if version string differs OR commit sha differs
    available = False
    if remote.get("version") and remote["version"] != local_ver:
        available = True
    if local_sha and remote.get("full_sha") and local_sha != remote["full_sha"]:
        available = True
    if not local_sha and remote.get("full_sha"):
        # first check after install — treat as up-to-date unless version file differs
        available = bool(remote.get("version") and remote["version"] != local_ver)

    info = {
        "local_version": local_ver,
        "local_sha": local_sha or "(unknown)",
        "remote_version": remote.get("version"),
        "remote_sha": remote.get("sha"),
        "remote_full_sha": remote.get("full_sha"),
        "remote_message": remote.get("message"),
        "remote_date": remote.get("date"),
        "update_available": available,
    }
    return available, info


def apply_update() -> str:
    """
    Download ZIP of main, replace code files, keep data/exports.
    Returns human-readable status message.
    """
    root = app_root()
    headers = {"User-Agent": "RF-PTA-Updater"}
    r = requests.get(ZIP_URL, headers=headers, timeout=120)
    r.raise_for_status()

    tmp_extract = root / ".update_tmp"
    if tmp_extract.exists():
        shutil.rmtree(tmp_extract, ignore_errors=True)
    tmp_extract.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        zf.extractall(tmp_extract)

    # GitHub ZIP root folder: repo-branch
    subdirs = [p for p in tmp_extract.iterdir() if p.is_dir()]
    if not subdirs:
        raise RuntimeError("Empty update archive")
    src_root = subdirs[0]

    # Copy everything except preserved names
    for item in src_root.iterdir():
        name = item.name
        if name in PRESERVE_NAMES:
            continue
        dest = root / name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Save commit sha marker
    try:
        _, info = check_update()
        # re-fetch after copy — use remote from before
        remote = fetch_remote_info()
        (root / ".update_sha").write_text(remote["full_sha"], encoding="utf-8")
        if remote.get("version"):
            (root / "VERSION").write_text(remote["version"] + "\n", encoding="utf-8")
    except Exception:
        pass

    shutil.rmtree(tmp_extract, ignore_errors=True)
    return (
        "Обновление установлено. Перезапустите дашборд (закройте окно и откройте ярлык снова). "
        "Папки data/ и exports/ сохранены."
    )
