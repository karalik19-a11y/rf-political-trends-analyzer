"""Self-update from GitHub main — keeps data/ and venv/."""

from __future__ import annotations

import io
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, Tuple

import requests

REPO_OWNER = "karalik19-a11y"
REPO_NAME = "rf-political-trends-analyzer"
BRANCH = "main"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"

# Never overwrite user data or local env
PRESERVE = {"data", "venv", ".git", ".update_tmp", ".update_sha"}


def app_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_local_version() -> str:
    vf = app_root() / "VERSION"
    if vf.exists():
        return vf.read_text(encoding="utf-8").strip()
    return "0.0.0"


def read_local_sha() -> str:
    p = app_root() / ".update_sha"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


def fetch_remote_info() -> Dict[str, Any]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "RF-PTA-Updater/2"}
    r = requests.get(f"{GITHUB_API}/commits/{BRANCH}", headers=headers, timeout=30)
    r.raise_for_status()
    commit = r.json()
    full_sha = commit["sha"]
    message = (commit.get("commit") or {}).get("message", "").split("\n")[0][:120]
    date = ((commit.get("commit") or {}).get("committer") or {}).get("date", "")
    remote_version = None
    try:
        vr = requests.get(
            f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/VERSION",
            headers=headers,
            timeout=15,
        )
        if vr.status_code == 200:
            remote_version = vr.text.strip()
    except Exception:
        pass
    return {
        "sha": full_sha[:7],
        "full_sha": full_sha,
        "message": message,
        "date": date,
        "version": remote_version or full_sha[:7],
    }


def check_update() -> Tuple[bool, Dict[str, Any]]:
    local_ver = read_local_version()
    local_sha = read_local_sha()
    remote = fetch_remote_info()
    available = False
    if remote.get("full_sha") and local_sha and remote["full_sha"] != local_sha:
        available = True
    elif remote.get("version") and remote["version"] != local_ver:
        available = True
    elif not local_sha and remote.get("full_sha"):
        # first run after clone: compare version only
        available = bool(remote.get("version") and remote["version"] != local_ver)
    info = {
        "local_version": local_ver,
        "local_sha": local_sha or "(none)",
        "remote_version": remote.get("version"),
        "remote_sha": remote.get("sha"),
        "remote_full_sha": remote.get("full_sha"),
        "remote_message": remote.get("message"),
        "remote_date": remote.get("date"),
        "update_available": available,
    }
    return available, info


def apply_update() -> str:
    root = app_root()
    headers = {"User-Agent": "RF-PTA-Updater/2"}
    r = requests.get(ZIP_URL, headers=headers, timeout=180)
    r.raise_for_status()

    tmp = root / ".update_tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        zf.extractall(tmp)

    subdirs = [p for p in tmp.iterdir() if p.is_dir()]
    if not subdirs:
        raise RuntimeError("Empty update archive")
    src_root = subdirs[0]

    updated = []
    for item in src_root.iterdir():
        name = item.name
        if name in PRESERVE:
            continue
        dest = root / name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
        updated.append(name)

    remote = fetch_remote_info()
    (root / ".update_sha").write_text(remote["full_sha"], encoding="utf-8")
    if remote.get("version"):
        (root / "VERSION").write_text(remote["version"] + "\n", encoding="utf-8")

    shutil.rmtree(tmp, ignore_errors=True)
    return (
        f"Updated to {remote.get('version')} ({remote.get('sha')}). "
        f"Files: {', '.join(updated[:12])}{'...' if len(updated) > 12 else ''}. "
        f"data/ and venv/ kept. Restart the app."
    )


if __name__ == "__main__":
    av, info = check_update()
    print(info)
    if av:
        print(apply_update())
    else:
        print("Up to date")
