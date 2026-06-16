"""
import_bible.py

Takes a document you already have — a summary like the one you might paste
from another conversation, an old bible in a different shape, loose prose
notes — and converts it into this app's standard bible format.

Lines starting with # are treated as open questions / to-do-later items,
not settled decisions, regardless of where they appear in the document.

Nothing is invented. The app extracts and organizes only what's in the
document you give it. You see the proposed bible before anything is saved,
and can approve, edit, or reject it.

Usage:
    python import_bible.py

You'll be asked for:
    1. Which project to import into (existing or new — same registry as onboard.py)
    2. The document — either pasted directly, or a file path to read from
"""

import os
import json
import sys
from datetime import date
import project_registry as registry

# ─────────────────────────────────────────────
# SYSTEM PROMPT — extraction only, never invention
# ─────────────────────────────────────────────

IMPORT_SYSTEM_PROMPT = """You are converting a writer's existing document into a structured project bible.

The document might be: a summary from a previous conversation, an old bible in
a different format, loose prose notes, or anything else describing their story.

YOUR RULES — non-negotiable:

1. Extract only what is actually in the document. Never invent characters,
   events, or details that aren't there. If something is ambiguous, mark it
   as ambiguous rather than guessing.

2. Any line or passage in the source document that starts with # is a
   to-do-later / open question, NOT a settled decision — no matter how
   confidently it's phrased. File these under open_questions, never under
   decisions_log or the static bible.

3. Preserve the writer's own language wherever possible. Don't smooth their
   phrasing into generic prose — their specific word choices often carry
   meaning (character nicknames, recurring images, etc).

4. Organize into these sections only:
   - story_kernel (the feeling/theme at the center, if stated or inferable)
   - protagonist (who the story is about)
   - supporting_characters (everyone else with enough detail to matter)
   - world (setting, time period, social texture)
   - structure_notes (anything about chapters, books, acts, beats already decided)
   - decisions_log (settled creative choices, as a list of short statements)
   - open_questions (unresolved items, including everything marked with #)

5. If the document doesn't have enough information for a section, write
   "Not enough information in source document" rather than guessing.

6. Output ONLY valid JSON matching this exact shape, nothing else —
   no preamble, no markdown fences, no commentary:

{
  "story_kernel": "...",
  "protagonist": "...",
  "supporting_characters": "...",
  "world": "...",
  "structure_notes": "...",
  "decisions_log": ["...", "..."],
  "open_questions": ["...", "..."]
}"""


# ─────────────────────────────────────────────
# DOCUMENT INPUT
# ─────────────────────────────────────────────

def get_source_document():
    """
    Asks the writer how they want to provide the document:
    pasted directly, or a file path. Returns the raw text.
    """
    print("How do you want to provide the document?\n")
    print("  1 — Paste it directly")
    print("  2 — Give a file path\n")
    choice = input("Choice (1-2): ").strip()
    print()

    if choice == "2":
        path = input("File path: ").strip()
        if not os.path.exists(path):
            print(f"File not found: {path}\n")
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # Pasted text — read until a line that's just /done
    print("Paste your document below. Type /done on its own line when finished.\n")
    lines = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip() == "/done":
            break
        lines.append(line)
    return "\n".join(lines)


# ─────────────────────────────────────────────
# EXTRACTION — calls Claude to structure the document
# ─────────────────────────────────────────────

def fake_extraction(source_text):
    """Dry-run stand-in. No API call, just proves the plumbing works."""
    todo_lines = [l.strip() for l in source_text.split("\n") if l.strip().startswith("#")]
    return {
        "story_kernel": "[DRY RUN] Not extracted — no real API call made.",
        "protagonist": "[DRY RUN] Not extracted.",
        "supporting_characters": "[DRY RUN] Not extracted.",
        "world": "[DRY RUN] Not extracted.",
        "structure_notes": "[DRY RUN] Not extracted.",
        "decisions_log": [f"[DRY RUN] Source document was {len(source_text)} characters long."],
        "open_questions": todo_lines if todo_lines else ["[DRY RUN] No # lines found in source."]
    }


def extract_bible_from_document(client, source_text, dry_run=False):
    """
    Sends the document to Claude with the extraction system prompt.
    Returns a parsed dict matching the standard bible shape.
    Raises if the response isn't valid JSON — caller should handle that.
    """
    if dry_run:
        return fake_extraction(source_text)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=IMPORT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": source_text}]
    )
    raw = response.content[0].text.strip()

    # Strip markdown fences if the model added them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


# ─────────────────────────────────────────────
# DISPLAY AND APPROVAL
# ─────────────────────────────────────────────

def show_proposed_bible(extracted):
    print("\n─── PROPOSED BIBLE ─────────────────────────\n")
    print(f"Story kernel:\n  {extracted.get('story_kernel', '—')}\n")
    print(f"Protagonist:\n  {extracted.get('protagonist', '—')}\n")
    print(f"Supporting characters:\n  {extracted.get('supporting_characters', '—')}\n")
    print(f"World:\n  {extracted.get('world', '—')}\n")
    print(f"Structure notes:\n  {extracted.get('structure_notes', '—')}\n")

    decisions = extracted.get('decisions_log', [])
    print(f"Decisions log ({len(decisions)} items):")
    for d in decisions:
        print(f"  • {d}")

    questions = extracted.get('open_questions', [])
    print(f"\nOpen questions ({len(questions)} items) — includes anything marked with #:")
    for q in questions:
        print(f"  ? {q}")
    print()


# ─────────────────────────────────────────────
# WRITE TO PROJECT FILES
# ─────────────────────────────────────────────

def write_bible_files(extracted, paths, source_label):
    """
    Writes the approved extraction into this project's bible_static.md
    and bible_active.json. Only called after writer approval.
    """
    static_lines = [
        f"# Imported Bible",
        f"# Source: {source_label}",
        f"# Imported: {date.today().isoformat()}",
        "# This file is yours. Edit directly. The app never writes into it again.",
        "",
        "## Story Kernel",
        extracted.get('story_kernel', '(not found in source)'),
        "",
        "## Protagonist",
        extracted.get('protagonist', '(not found in source)'),
        "",
        "## Supporting Characters",
        extracted.get('supporting_characters', '(not found in source)'),
        "",
        "## World",
        extracted.get('world', '(not found in source)'),
        "",
        "## Structure Notes",
        extracted.get('structure_notes', '(not found in source)'),
        "",
    ]

    static_existing = ""
    if os.path.exists(paths["bible_static"]):
        with open(paths["bible_static"], "r", encoding="utf-8") as f:
            static_existing = f.read()

    with open(paths["bible_static"], "w", encoding="utf-8") as f:
        if static_existing.strip():
            f.write(static_existing.rstrip() + "\n\n---\n\n")
        f.write("\n".join(static_lines))

    # Active bible — merge into existing if present, else create fresh
    if os.path.exists(paths["bible_active"]):
        with open(paths["bible_active"], "r", encoding="utf-8") as f:
            active = json.load(f)
    else:
        active = {
            "project": source_label,
            "created": date.today().isoformat(),
            "current_position": {"focus": "Imported from existing document"},
            "decisions_log": [],
            "open_questions": [],
            "completed_works": []
        }

    active.setdefault("decisions_log", [])
    active.setdefault("open_questions", [])

    for d in extracted.get('decisions_log', []):
        active["decisions_log"].append(f"[imported {date.today().isoformat()}] {d}")

    for q in extracted.get('open_questions', []):
        active["open_questions"].append(f"[imported {date.today().isoformat()}] {q}")

    active["last_updated"] = date.today().isoformat()

    with open(paths["bible_active"], "w", encoding="utf-8") as f:
        json.dump(active, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    dry_run = os.environ.get("DRY_RUN") == "true"
    client = None

    if not dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set.")
            print("Run: export ANTHROPIC_API_KEY=your_key_here")
            print("Or: export DRY_RUN=true   (test without an account)")
            return
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

    print("\n═══ IMPORT EXISTING DOCUMENT ═══════════════\n")
    if dry_run:
        print("✓ DRY RUN MODE — no API key needed, no real extraction performed\n")

    # ── Which project ──
    registry.print_project_list()
    display_name = input(
        "Project name to import into (existing or new): "
    ).strip()
    print()
    if not display_name:
        print("No project name given. Exiting.\n")
        return

    folder_name = registry.resolve_project_name(display_name)
    paths = registry.ensure_project_folders(folder_name)
    registry.register_project(display_name, folder_name)
    print(f"✓ Project folder ready    (projects/{folder_name}/)\n")

    if os.path.exists(paths["bible_static"]):
        print("Note: this project already has a bible_static.md.")
        print("Imported content will be appended below the existing content, clearly separated.\n")

    # ── Get the document ──
    source_text = get_source_document()
    if not source_text or not source_text.strip():
        print("No document provided. Exiting.\n")
        return

    print(f"\n✓ Document received ({len(source_text)} characters)\n")
    print("Extracting structure...\n")

    # ── Extract ──
    try:
        extracted = extract_bible_from_document(client, source_text, dry_run=dry_run)
    except json.JSONDecodeError:
        print("Couldn't parse the extraction as valid JSON. Nothing was saved.")
        print("Try again, or simplify the source document.\n")
        return
    except Exception as e:
        print(f"Extraction failed: {e}\n")
        return

    # ── Show and approve ──
    show_proposed_bible(extracted)

    approve = input("Save this into the project bible? (yes/no/edit): ").strip().lower()
    print()

    if approve.startswith("e"):
        print("Editing isn't built into this prompt yet — easiest path:")
        print("approve as-is, then open bible_static.md / bible_active.json")
        print("directly afterward and fix anything that's off. It's your file.\n")
        approve = input("Save now so you have something to edit? (yes/no): ").strip().lower()

    if not approve.startswith("y"):
        print("Not saved. Nothing changed.\n")
        return

    write_bible_files(extracted, paths, display_name)

    print(f"✓ bible_static.md updated     (projects/{folder_name}/bible_static.md)")
    print(f"✓ bible_active.json updated   (projects/{folder_name}/bible_active.json)\n")
    print("Open both files and read them through — imported content is clearly")
    print("marked with date and source so you always know what came from where.\n")


if __name__ == "__main__":
    main()
