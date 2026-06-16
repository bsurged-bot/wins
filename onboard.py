"""
onboard.py

Builds a writer's project bible through conversation.
Never writes for the writer. Never suggests prose.
Asks questions, reflects answers back, lets the writer correct.

Every project gets its own folder under projects/<project-name>/
with its own bible_static.md, bible_active.json, change_log.json,
sessions/, and archive/. A projects/registry.json keeps the master list.

Three modes:
  1. New project, no bible       — full onboarding conversation
  2. New project, existing bible — loads and confirms existing bible
  3. No bible wanted             — just opens sparring_partner.py directly

Usage:
    python onboard.py

Outputs (if writer wants a bible), per project:
    projects/<name>/bible_static.md
    projects/<name>/bible_active.json
    projects/<name>/change_log.json

Then hands off to sparring_partner.py automatically.
"""

import os
import json
import subprocess
from datetime import date, datetime
import project_registry as registry

# ─────────────────────────────────────────────
# THE FIVE PRODUCT PRINCIPLES
# These are enforced throughout — not guidelines, rules.
#
# 1. Discussion and citation only — no original prose generated
# 2. Hard pushback on generation attempts — every time
# 3. Short works close the chapter in the bible
# 4. Bible is optional — writer can work without structure
# 5. Skills amplifier — makes writer's thinking faster, never replaces it
# ─────────────────────────────────────────────

ONBOARD_SYSTEM_PROMPT = """You are onboarding a writer into a literary sparring partner app.
Your job is to help them build a project bible through conversation.

YOUR RULES — non-negotiable:

1. You never write prose for the writer. Not a sentence, not a phrase.
   If asked, you redirect with a question about what they want the moment to DO.

2. You may quote other published works with full citation to illustrate
   a craft point. That is the only text you produce that isn't a question.

3. You ask one question at a time. Never a list of questions.

4. You reflect the writer's own answers back to them in structured form
   and ask if you've heard them correctly. You never interpret beyond what
   they said.

5. When a writer is stuck, you ask what they're afraid of — not what they want.
   Fear usually points at the story faster than desire does.

6. You never use the words: outline, plot, structure, beat, act.
   You ask about feelings, people, moments, and what changes.

7. If a writer wants no bible, you accept that immediately and move on.

YOUR TONE:
Direct. Intellectually honest. Not cheerleading.
You can push back. You can name what's missing.
You cannot fill it in for them.

SCOPE MAPPING (internal — never say these words to the writer):
- "single sitting" or "short"  → 3-question kernel (turn, person, end feeling)
- "few sessions" or "medium"   → 7-question kernel
- "months" or "long"           → full 15-beat kernel, one question at a time

After scope is clear, ask only the questions that scope needs.
Do not ask novel questions of a short story writer."""

# ─────────────────────────────────────────────
# CHANGE LOG
# ─────────────────────────────────────────────

def load_change_log(change_log_path):
    if os.path.exists(change_log_path):
        with open(change_log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_change_log(log, change_log_path):
    with open(change_log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

def log_change(log, field, old_value, new_value, change_log_path, reason=""):
    log.append({
        "date": datetime.now().isoformat(),
        "field": field,
        "old": old_value,
        "new": new_value,
        "reason": reason
    })
    save_change_log(log, change_log_path)
    print(f"  ✓ Change logged: {field}")

# ─────────────────────────────────────────────
# BIBLE BUILDERS
# ─────────────────────────────────────────────

def build_empty_bible_static(kernel):
    """
    Takes the kernel dict built from onboarding conversation.
    Builds a bible_static.md the writer can edit directly.
    Never invents — only uses what the writer said.
    """
    lines = [
        f"# {kernel.get('title', 'Untitled Project')} — Static Bible",
        f"# Created: {date.today().isoformat()}",
        "# This file is yours. Edit directly. The app never writes into it.",
        "",
        "## Story Kernel",
        f"**The feeling at the center:** {kernel.get('feeling', '(not yet defined)')}",
        f"**What the reader feels at the end:** {kernel.get('end_feeling', '(not yet defined)')}",
        "",
        "## Central Figure",
        f"{kernel.get('protagonist', '(not yet defined)')}",
        "",
        "## The Wound (before the story starts)",
        f"{kernel.get('wound', '(not yet defined)')}",
        "",
        "## The Turn (what changes everything)",
        f"{kernel.get('turn', '(not yet defined)')}",
        "",
    ]

    # Only add world section if writer gave something
    if kernel.get('world'):
        lines += [
            "## The World",
            f"{kernel.get('world')}",
            "",
        ]

    # Only add supporting characters if writer named any
    if kernel.get('supporting'):
        lines += [
            "## Supporting Characters",
            f"{kernel.get('supporting')}",
            "",
        ]

    # Scope-specific sections
    scope = kernel.get('scope', 'short')
    if scope in ['novella', 'novel']:
        lines += [
            "## Philosophical or Thematic Anchor",
            f"{kernel.get('theme_anchor', '(not yet defined)')}",
            "",
        ]

    lines += [
        "## Writer's Own Rules for This Project",
        "# Add your rules here — what the sparring partner should hold you to.",
        "",
    ]

    return "\n".join(lines)


def build_empty_bible_active(kernel):
    """
    Builds the active bible JSON — current position, beats, open questions.
    """
    scope = kernel.get('scope', 'short')

    # Beat scaffolds by scope — writer never sees these labels
    if scope == 'short':
        beats = {
            "before": {"status": "open", "note": None},
            "turn": {"status": "defined", "note": kernel.get('turn')},
            "after": {"status": "open", "note": None}
        }
    elif scope == 'novella':
        beats = {
            "setup": {"status": "open", "note": None},
            "catalyst": {"status": "defined", "note": kernel.get('turn')},
            "rising": {"status": "open", "note": None},
            "midpoint": {"status": "open", "note": None},
            "crisis": {"status": "open", "note": None},
            "climax": {"status": "open", "note": None},
            "resolution": {"status": "open", "note": kernel.get('end_feeling')}
        }
    else:  # novel
        beats = {
            "1_opening_image": {"status": "open", "note": None},
            "2_theme_stated": {"status": "open", "note": kernel.get('feeling')},
            "3_setup": {"status": "open", "note": None},
            "4_catalyst": {"status": "defined", "note": kernel.get('turn')},
            "5_debate": {"status": "open", "note": None},
            "6_break_into_2": {"status": "open", "note": None},
            "7_b_story": {"status": "open", "note": None},
            "8_fun_and_games": {"status": "open", "note": None},
            "9_midpoint": {"status": "open", "note": None},
            "10_bad_guys_close_in": {"status": "open", "note": None},
            "11_all_is_lost": {"status": "open", "note": None},
            "12_dark_night_of_soul": {"status": "open", "note": None},
            "13_break_into_3": {"status": "open", "note": None},
            "14_finale": {"status": "open", "note": None},
            "15_final_image": {"status": "open", "note": kernel.get('end_feeling')}
        }

    return {
        "project": kernel.get('title', 'Untitled'),
        "scope": scope,
        "created": date.today().isoformat(),
        "last_updated": date.today().isoformat(),
        "current_position": {
            "focus": "Beginning — project just created"
        },
        "structure": {
            "framework": {
                "short": "3-beat (before / turn / after)",
                "novella": "7-beat",
                "novel": "Save the Cat — Blake Snyder"
            }.get(scope),
            "beats": beats
        },
        "decisions_log": [],
        "open_questions": [],
        "completed_works": []
    }

# ─────────────────────────────────────────────
# ONBOARDING CONVERSATION
# ─────────────────────────────────────────────

def run_onboarding(client):
    """
    Conversational onboarding. One question at a time.
    Returns a kernel dict the bible builders use.
    Never writes prose. Never interprets beyond what the writer said.
    """
    from anthropic import Anthropic

    print("\n─── NEW PROJECT ONBOARDING ─────────────────\n")
    print("I'll ask you some questions about your project.")
    print("Answer as much or as little as you want.")
    print("Type /skip to skip any question.")
    print("Type /done when you have enough to start.\n")

    kernel = {}
    conversation = []

    def ask(question):
        """Send a question, get an answer, save both."""
        print(f"App: {question}\n")
        answer = input("You: ").strip()
        print()
        if answer == "/done":
            return None
        if answer == "/skip":
            return ""
        conversation.append({"role": "user", "content": f"Q: {question}\nA: {answer}"})
        return answer

    # ── Scope first — maps silently to scaffold ──
    scope_answer = ask(
        "How long do you want to sit with this story — "
        "a single sitting, a few weeks, or something you'll return to over months?"
    )
    if scope_answer is None:
        return kernel, conversation

    scope_lower = scope_answer.lower()
    if any(w in scope_lower for w in ['sitting', 'short', 'quick', 'one', 'day']):
        kernel['scope'] = 'short'
    elif any(w in scope_lower for w in ['week', 'month', 'novella', 'medium']):
        kernel['scope'] = 'novella'
    else:
        kernel['scope'] = 'novel'

    # ── Title (optional) ──
    title = ask("Does it have a name yet — even a working one?")
    if title is None:
        return kernel, conversation
    kernel['title'] = title if title else 'Untitled'

    # ── The kernel questions — same for all scopes ──
    feeling = ask(
        "What's the feeling at the center of this? "
        "Not what happens — what does it feel like?"
    )
    if feeling is None:
        return kernel, conversation
    kernel['feeling'] = feeling

    protagonist = ask(
        "Who is this about? Before you name them — who are they?"
    )
    if protagonist is None:
        return kernel, conversation
    kernel['protagonist'] = protagonist

    turn = ask(
        "What happens that makes this story necessary? "
        "The moment everything changes."
    )
    if turn is None:
        return kernel, conversation
    kernel['turn'] = turn

    end_feeling = ask(
        "When someone finishes reading — what do you want them to feel? "
        "Not think. Feel."
    )
    if end_feeling is None:
        return kernel, conversation
    kernel['end_feeling'] = end_feeling

    # ── Extended questions for novella / novel only ──
    if kernel['scope'] in ['novella', 'novel']:

        wound = ask(
            "What happened to this person before your story starts? "
            "The thing that shaped them."
        )
        if wound is None:
            return kernel, conversation
        kernel['wound'] = wound

        world = ask(
            "Where and when does this live? "
            "What does the world around them feel like?"
        )
        if world is None:
            return kernel, conversation
        kernel['world'] = world

        supporting = ask(
            "Is there anyone else essential to this story? "
            "Describe them before naming them."
        )
        if supporting is None:
            return kernel, conversation
        kernel['supporting'] = supporting

    # ── Novel only ──
    if kernel['scope'] == 'novel':

        theme_anchor = ask(
            "Is there a text, a line, an idea outside your story "
            "that this story is in conversation with?"
        )
        if theme_anchor is None:
            return kernel, conversation
        kernel['theme_anchor'] = theme_anchor

    # ── Reflect back ──
    print("\n─── HERE'S WHAT I HEARD ────────────────────\n")
    print(f"  Scope:        {kernel.get('scope', '—')}")
    print(f"  Title:        {kernel.get('title', '—')}")
    print(f"  Feeling:      {kernel.get('feeling', '—')}")
    print(f"  Protagonist:  {kernel.get('protagonist', '—')}")
    print(f"  The turn:     {kernel.get('turn', '—')}")
    print(f"  End feeling:  {kernel.get('end_feeling', '—')}")
    if kernel.get('wound'):
        print(f"  Wound:        {kernel.get('wound')}")
    if kernel.get('world'):
        print(f"  World:        {kernel.get('world')}")
    if kernel.get('supporting'):
        print(f"  Others:       {kernel.get('supporting')}")
    if kernel.get('theme_anchor'):
        print(f"  Anchor:       {kernel.get('theme_anchor')}")

    print()
    confirm = input("Does this feel like your story? (yes / no / correct it): ").strip().lower()
    print()

    if confirm.startswith('n') or confirm.startswith('c'):
        print("Tell me what I got wrong.\n")
        correction = input("You: ").strip()
        print()
        # Log the correction as an open question for the sparring partner
        kernel['onboarding_correction'] = correction
        conversation.append({
            "role": "user",
            "content": f"Correction to onboarding summary: {correction}"
        })

    return kernel, conversation


# ─────────────────────────────────────────────
# CLOSE A CHAPTER (short works)
# ─────────────────────────────────────────────

def close_chapter(bible_active, title):
    """
    Marks a completed short work in the bible.
    Principle 3: short works close the chapter.
    """
    bible_active["completed_works"].append({
        "title": title,
        "completed": date.today().isoformat()
    })
    bible_active["last_updated"] = date.today().isoformat()

    # Mark all beats as complete for short scope
    if bible_active.get("structure", {}).get("beats"):
        for beat in bible_active["structure"]["beats"].values():
            if beat["status"] != "defined":
                beat["status"] = "closed"

    print(f"\n✓ '{title}' closed. Chapter complete.\n")
    return bible_active


# ─────────────────────────────────────────────
# EDIT BIBLE FIELD
# ─────────────────────────────────────────────

def edit_bible_field(change_log, bible_active_path, change_log_path):
    """
    Interactive bible editor with change logging.
    Writer edits, gives reason, change is logged.
    """
    print("\n─── EDIT BIBLE ─────────────────────────────\n")

    if not os.path.exists(bible_active_path):
        print("No active bible found. Run onboarding first.\n")
        return

    with open(bible_active_path, "r", encoding="utf-8") as f:
        active = json.load(f)

    print("What field are you changing? (e.g. protagonist name, scope, turn)\n")
    field = input("Field: ").strip()
    old_value = input("Old value: ").strip()
    new_value = input("New value: ").strip()
    reason = input("Why? (optional but recommended): ").strip()

    log_change(change_log, field, old_value, new_value, change_log_path, reason)

    # Update last_updated
    active["last_updated"] = date.today().isoformat()
    with open(bible_active_path, "w", encoding="utf-8") as f:
        json.dump(active, f, indent=2, ensure_ascii=False)

    print(f"\nChange logged. Edit bible_static.md or bible_active.json directly to apply.\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    # The onboarding conversation itself never calls the API — it's just
    # questions and reflection. The key is only needed once you hand off
    # to sparring_partner.py. So we don't block here; DRY_RUN=true works
    # all the way through without any key or account.
    dry_run = os.environ.get("DRY_RUN") == "true"
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not dry_run and not api_key:
        print("Note: no ANTHROPIC_API_KEY set yet.")
        print("Onboarding (options 1, 2, 4, 5) works fine without one.")
        print("Sparring with Claude (option 3, or after option 1) needs either:")
        print("  export ANTHROPIC_API_KEY=your_key_here")
        print("  — or —")
        print("  export DRY_RUN=true   (test the plumbing, no account needed)\n")

    client = None  # only constructed inside sparring_partner.py when actually needed

    print("\n═══ PROJECT SETUP ══════════════════════════\n")
    print("What would you like to do?\n")
    print("  1 — Start a new project (build a bible through conversation)")
    print("  2 — Start a new project (no bible, just talk)")
    print("  3 — Load existing bible and start sparring")
    print("  4 — Edit an existing bible field")
    print("  5 — Close a completed short work\n")

    choice = input("Choice (1-5): ").strip()
    print()

    # Option 2 has no project folder at all — no-bible mode is project-less by design.
    if choice == "2":
        print("No bible. Just conversation.\n")
        print("The sparring partner won't hold any project context —")
        print("you'll carry it yourself, or paste it in as you go.\n")
        go = input("Start now? (yes/no): ").strip().lower()
        if go.startswith('y'):
            os.environ["NO_BIBLE"] = "true"
            subprocess.run(["python3", "sparring_partner.py"])
        return

    # Every other option needs a project — ask which one, every time.
    # Giving a name (new or existing) creates its own sessions/archive folders.
    existing = registry.print_project_list()
    display_name = input(
        "Project name (existing or new — this creates its own sessions/archive folders): "
    ).strip()
    print()

    if not display_name:
        print("No project name given. Exiting.\n")
        return

    folder_name = registry.resolve_project_name(display_name)
    paths = registry.ensure_project_folders(folder_name)
    print(f"✓ Project folder ready    (projects/{folder_name}/)\n")

    change_log = load_change_log(paths["change_log"])

    # ── Option 1: Full onboarding ──
    if choice == "1":
        kernel, conversation = run_onboarding(client)

        if not kernel:
            print("Onboarding exited early. Nothing saved.\n")
            return

        # Build and save bible files into this project's folder
        static_content = build_empty_bible_static(kernel)
        active_content = build_empty_bible_active(kernel)

        with open(paths["bible_static"], "w", encoding="utf-8") as f:
            f.write(static_content)

        with open(paths["bible_active"], "w", encoding="utf-8") as f:
            json.dump(active_content, f, indent=2, ensure_ascii=False)

        # Log creation
        log_change(change_log, "project", None, kernel.get('title', 'Untitled'),
                   paths["change_log"], "Project created via onboarding")

        # Register in the master list with the scope we just learned
        registry.register_project(display_name, folder_name, scope=kernel.get('scope'))

        print(f"✓ bible_static.md created     (projects/{folder_name}/bible_static.md)")
        print(f"✓ bible_active.json created   (projects/{folder_name}/bible_active.json)")
        print(f"✓ change_log.json updated     (projects/{folder_name}/change_log.json)\n")
        print("Open bible_static.md and read it through.")
        print("Edit anything that isn't right. It's yours.\n")

        go = input("Ready to start sparring? (yes/no): ").strip().lower()
        if go.startswith('y'):
            subprocess.run(["python3", "sparring_partner.py", display_name])

    # ── Option 3: Existing bible ──
    elif choice == "3":
        if not os.path.exists(paths["bible_static"]):
            print(f"No bible_static.md found yet for '{display_name}'.\n")
            print("Run option 1 to create one for this project.\n")
            return

        with open(paths["bible_static"], "r", encoding="utf-8") as f:
            content = f.read()

        print(f"✓ Found bible_static.md ({len(content)} characters)")

        if os.path.exists(paths["bible_active"]):
            with open(paths["bible_active"], "r", encoding="utf-8") as f:
                active = json.load(f)
            print(f"✓ Found bible_active.json")
            print(f"  Project: {active.get('project', '—')}")
            print(f"  Last updated: {active.get('last_updated', '—')}")
            print(f"  Current focus: {active.get('current_position', {}).get('focus', '—')}\n")

        registry.register_project(display_name, folder_name)

        go = input("Start sparring? (yes/no): ").strip().lower()
        if go.startswith('y'):
            subprocess.run(["python3", "sparring_partner.py", display_name])

    # ── Option 4: Edit bible field ──
    elif choice == "4":
        edit_bible_field(change_log, paths["bible_active"], paths["change_log"])

    # ── Option 5: Close a short work ──
    elif choice == "5":
        if not os.path.exists(paths["bible_active"]):
            print("No active bible found for this project.\n")
            return

        with open(paths["bible_active"], "r", encoding="utf-8") as f:
            active = json.load(f)

        title = input("Title of the completed work: ").strip()
        active = close_chapter(active, title)

        with open(paths["bible_active"], "w", encoding="utf-8") as f:
            json.dump(active, f, indent=2, ensure_ascii=False)

        log_change(change_log, "completed_works", None, title, paths["change_log"], "Short work closed")
        print("Bible updated. Chapter closed.\n")

    else:
        print("Unrecognised choice. Run again.\n")


if __name__ == "__main__":
    main()
