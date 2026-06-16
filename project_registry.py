"""
project_registry.py

Shared by onboard.py and sparring_partner.py.

Every project lives in its own folder under /projects/<project-name>/
with its own bible_static.md, bible_active.json, change_log.json,
sessions/, and archive/. Nothing is shared between projects.

A single projects/registry.json keeps a master list — name, created date,
last opened, scope — so you can see all your projects at a glance.

This file does NOT call the Anthropic API and has no dependency on it.
"""

import os
import json
from datetime import date

PROJECTS_ROOT = "projects"
REGISTRY_PATH = os.path.join(PROJECTS_ROOT, "registry.json")


def _safe_folder_name(name):
    """
    Turns a project name into a safe folder name.
    'My Novel!' -> 'my-novel'
    Keeps it readable rather than hashing it.
    """
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in name)
    safe = safe.strip().lower().replace(" ", "-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe or "untitled-project"


def load_registry():
    """Load the master project list. Returns [] if none exists yet."""
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_registry(registry):
    os.makedirs(PROJECTS_ROOT, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def list_projects():
    """Returns the registry list for display. Each entry is a dict."""
    return load_registry()


def project_paths(folder_name):
    """
    Given a project's folder name, returns a dict of all paths
    that scripts need. Does not create anything — see ensure_project_folders.
    """
    base = os.path.join(PROJECTS_ROOT, folder_name)
    return {
        "base": base,
        "bible_static": os.path.join(base, "bible_static.md"),
        "bible_active": os.path.join(base, "bible_active.json"),
        "change_log": os.path.join(base, "change_log.json"),
        "sessions_dir": os.path.join(base, "sessions"),
        "archive_dir": os.path.join(base, "archive"),
    }


def ensure_project_folders(folder_name):
    """
    Creates the project's base folder, sessions/, and archive/
    if they don't already exist. Safe to call every time — does
    nothing if everything's already there.
    """
    paths = project_paths(folder_name)
    os.makedirs(paths["sessions_dir"], exist_ok=True)
    os.makedirs(paths["archive_dir"], exist_ok=True)
    return paths


def register_project(display_name, folder_name, scope=None):
    """
    Adds a project to the master registry, or updates last_opened
    if it already exists. Called every time a project is created or opened.
    """
    registry = load_registry()

    existing = next((p for p in registry if p["folder_name"] == folder_name), None)
    today = date.today().isoformat()

    if existing:
        existing["last_opened"] = today
        if scope:
            existing["scope"] = scope
    else:
        registry.append({
            "display_name": display_name,
            "folder_name": folder_name,
            "scope": scope,
            "created": today,
            "last_opened": today,
        })

    save_registry(registry)


def resolve_project_name(display_name):
    """
    Takes whatever the writer typed as a project name and returns
    the safe folder name to use on disk. If a project with this
    display name already exists in the registry, reuse its exact
    folder name rather than re-deriving it.
    """
    registry = load_registry()
    existing = next(
        (p for p in registry if p["display_name"].lower() == display_name.lower()),
        None
    )
    if existing:
        return existing["folder_name"]
    return _safe_folder_name(display_name)


def print_project_list():
    """Pretty-prints the master list for the writer to choose from."""
    registry = load_registry()
    if not registry:
        print("No projects yet.\n")
        return registry

    print("\n─── YOUR PROJECTS ──────────────────────────\n")
    for i, p in enumerate(registry, 1):
        scope = p.get("scope") or "—"
        print(f"  {i}. {p['display_name']}  (scope: {scope}, last opened: {p['last_opened']})")
    print()
    return registry
