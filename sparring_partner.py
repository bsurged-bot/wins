"""
sparring_partner.py

A literary sparring partner. Knows your world. Discusses, challenges, asks
questions. Never writes your prose.

Each project lives in its own folder under projects/<project-name>/.
Run this directly and it will ask which project to open, or pass
the project name as a command line argument:

    python sparring_partner.py "My Novel"

Requirements:
    pip install anthropic
    Set environment variable: export ANTHROPIC_API_KEY=your_key_here
    (or export DRY_RUN=true to test without any account)

Per-project file structure (created automatically):
    projects/<name>/bible_static.md   — world, characters, philosophy (cached)
    projects/<name>/bible_active.json — current position, decisions, questions
    projects/<name>/sessions/         — one JSON file per day
    projects/<name>/archive/          — old sessions moved here manually
"""

import os
import sys
import json
from datetime import date
import project_registry as registry

# ─────────────────────────────────────────────
# CONFIGURATION — edit these if needed
# ─────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"   # cheap, fast, good for discussion
MAX_TOKENS = 1024                      # response length ceiling
SHOW_PAYLOAD = False                   # set True to print full API payload before each call

# ─────────────────────────────────────────────
# SYSTEM PROMPT — the soul of the sparring partner
# ─────────────────────────────────────────────

SYSTEM_PROMPT_WITH_BIBLE = """You are a literary sparring partner. You know the writer's project completely.
You hold their established decisions and push back when something drifts.

YOUR ROLE:
- Discuss, question, challenge, reflect back
- Ask the question the writer hasn't asked yet
- Hold character consistency across the conversation
- Flag when something feels anachronistic to the world's logic
- Name structural or emotional gaps — but never fill them
- You may quote published works with full citation to illustrate a craft point

YOUR HARD CONSTRAINT — non-negotiable:
You do not write prose. You do not complete scenes. You do not offer
"here's how that scene could go." If asked, redirect immediately:
ask what the writer wants the moment to *do*, not what they want it to *say*.
This constraint does not bend for any reason. If pushed, hold it.

YOUR VOICE:
Direct. Not warm-fuzzy. Intellectually honest.
You can be Austen-sharp when the writer needs it.
You can be Heyer-generous when they're stuck.
You know the difference between a writer who needs pushing and one who needs permission.

The project bible is appended below. It is your ground truth.
When the writer updates it, you treat the update as authoritative."""

SYSTEM_PROMPT_NO_BIBLE = """You are a literary sparring partner. This writer is working without a project bible.
They carry their story themselves. You hold only what they tell you in this conversation.

YOUR ROLE:
- Discuss, question, challenge, reflect back
- Ask the question the writer hasn't asked yet
- Name gaps — never fill them
- You may quote published works with full citation to illustrate a craft point

YOUR HARD CONSTRAINT — non-negotiable:
You do not write prose. You do not complete scenes. You do not offer
"here's how that scene could go." If asked, redirect immediately:
ask what the writer wants the moment to *do*, not what they want it to *say*.
This constraint does not bend. Hold it every time.

YOUR VOICE:
Direct. Intellectually honest. Not cheerleading.
You can push back. You can name what's missing. You cannot fill it in."""

# ─────────────────────────────────────────────
# FILE LOADING — all paths come from the active project, passed in explicitly
# ─────────────────────────────────────────────

def load_bible_static(bible_static_path):
    """Load the static bible. This is cached by the API — paid for once per session."""
    with open(bible_static_path, "r", encoding="utf-8") as f:
        return f.read()

def load_bible_active(bible_active_path):
    """Load the active bible JSON and format it as readable text."""
    with open(bible_active_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Convert to readable text for the API
    return json.dumps(data, indent=2, ensure_ascii=False)

def get_session_path(sessions_dir):
    """Today's session file. One file per day, inside this project's sessions folder."""
    today = date.today().isoformat()          # e.g. 2026-06-03
    return os.path.join(sessions_dir, f"{today}.json")

def load_session(sessions_dir):
    """Load today's session if it exists. Otherwise start fresh."""
    path = get_session_path(sessions_dir)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fresh session structure
    return {
        "date": date.today().isoformat(),
        "model": MODEL,
        "turns": []
    }

def save_session(session, sessions_dir):
    """Save session after every turn. No data loss if you close the terminal."""
    os.makedirs(sessions_dir, exist_ok=True)   # create folder if it's missing
    path = get_session_path(sessions_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────────
# API CALL — fully transparent
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# DRY RUN — test the plumbing without an API key or account
# ─────────────────────────────────────────────

def fake_response(conversation_turns):
    """
    Stands in for a real API call. No key, no account, no cost.
    Echoes back what was received so you can verify the payload
    is assembled correctly — bible loaded, history intact, etc.
    """
    last_user_turn = conversation_turns[-1]["content"]
    return (
        "[DRY RUN — no real API call made]\n\n"
        f"I received your message: \"{last_user_turn[:200]}\"\n"
        f"Conversation so far: {len(conversation_turns)} turns.\n"
        "This is a placeholder response so you can verify the plumbing "
        "(file loading, payload assembly, session saving) works end to end. "
        "Set DRY_RUN = False and add a real ANTHROPIC_API_KEY to talk to Claude."
    )

# ─────────────────────────────────────────────
# API CALL — fully transparent
# ─────────────────────────────────────────────

def call_api(client, system_with_bible, conversation_turns, dry_run=False):
    """
    Assembles and sends the API payload.
    Set SHOW_PAYLOAD = True at top of file to print exactly what gets sent.
    If dry_run is True, no network call is made — returns a fake response
    so you can test everything else without a key or account.
    """

    # This is everything Claude would receive. Nothing else.
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system_with_bible,
        "messages": conversation_turns
    }

    if SHOW_PAYLOAD:
        print("\n─── FULL API PAYLOAD ───────────────────────")
        print(f"Model: {payload['model']}")
        print(f"System prompt length: {len(payload['system'])} characters")
        print(f"Turns in context: {len(payload['messages'])}")
        for i, turn in enumerate(payload['messages']):
            preview = turn['content'][:80].replace('\n', ' ')
            print(f"  [{i}] {turn['role']}: {preview}...")
        print("─────────────────────────────────────────────\n")

    if dry_run:
        return fake_response(conversation_turns)

    response = client.messages.create(**payload)
    return response.content[0].text

# ─────────────────────────────────────────────
# SUMMARIZE — distill a session into bible-ready candidates
# Writer approves before anything touches the actual bible file.
# ─────────────────────────────────────────────

SUMMARIZE_INSTRUCTION = """Look back at this conversation only — not the bible, not other sessions.

List, in plain text, three short sections:

DECISIONS — concrete creative choices the writer landed on this session.
Each one sentence, written as a settled fact (e.g. "Bijoy dies off-page in Book Two").

OPEN QUESTIONS — things the writer raised but didn't resolve.
Each one sentence, phrased as a question.

POSITION — one sentence on where the writer's actual focus is now
(what scene, chapter, or problem they're sitting with).

Use only what was actually discussed. If a section has nothing, write "None this session."
Do not invent anything. Do not write prose for the story itself — only this summary."""

def summarize_session(client, system_with_bible, conversation_turns, dry_run=False):
    """
    Asks Claude to distill the current session into bible-ready candidates.
    Returns the raw summary text. Does NOT write to any file —
    that only happens after the writer explicitly approves it.
    """
    summarize_turns = conversation_turns + [
        {"role": "user", "content": SUMMARIZE_INSTRUCTION}
    ]
    return call_api(client, system_with_bible, summarize_turns, dry_run=dry_run)


def apply_summary_to_bible(summary_text, bible_active_path):
    """
    Appends approved summary text into this project's bible_active.json
    decisions_log, with a timestamp.
    Writer has already seen and approved this text before this runs.
    """
    if not os.path.exists(bible_active_path):
        print("No bible_active.json found — nothing to update. (Are you in no-bible mode?)\n")
        return

    with open(bible_active_path, "r", encoding="utf-8") as f:
        active = json.load(f)

    active.setdefault("decisions_log", [])
    active.setdefault("open_questions", [])

    # Store the raw approved summary as a dated note rather than
    # trying to silently parse it apart — writer can tidy it later.
    active["decisions_log"].append(
        f"[{date.today().isoformat()}] {summary_text.strip()}"
    )
    active["last_updated"] = date.today().isoformat()

    with open(bible_active_path, "w", encoding="utf-8") as f:
        json.dump(active, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Added to bible_active.json under decisions_log, dated {date.today().isoformat()}\n")


# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────

def main():
    # DRY_RUN can be set as an environment variable: export DRY_RUN=true
    # Lets you test everything — file loading, onboarding, payload assembly,
    # session saving — without an Anthropic account or API key.
    dry_run = os.environ.get("DRY_RUN") == "true"

    client = None
    if not dry_run:
        # Check for API key — only required for real API calls
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
            print("Run: export ANTHROPIC_API_KEY=your_key_here")
            print("\nOr test without any account first:")
            print("Run: export DRY_RUN=true")
            return

        from anthropic import Anthropic   # imported only when actually needed
        client = Anthropic(api_key=api_key)

    # Check if we're running in no-bible mode (set by onboard.py option 2)
    no_bible = os.environ.get("NO_BIBLE") == "true"

    print("\n═══ SPARRING PARTNER ═══════════════════════\n")

    if dry_run:
        print("✓ DRY RUN MODE — no API key needed, no real calls made\n")

    # ── Resolve which project to open ──
    # Skipped entirely in no-bible mode — there's no project folder to use.
    paths = None
    if not no_bible:
        display_name = sys.argv[1] if len(sys.argv) > 1 else None

        if not display_name:
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
        registry.register_project(display_name, folder_name)

        print(f"✓ Project folder ready    (projects/{folder_name}/)")

    if no_bible:
        # Principle 4: bible is optional
        print("✓ No bible mode — you carry the story\n")
        system_with_bible = SYSTEM_PROMPT_NO_BIBLE
        sessions_dir = None  # no project folder, no session persistence either

    else:
        # If this is a brand new project, bible files won't exist yet.
        # Don't crash — tell the writer to run onboard.py first.
        if not os.path.exists(paths["bible_static"]) or not os.path.exists(paths["bible_active"]):
            print(f"\nNo bible found yet for this project.")
            print(f"Run onboard.py first to build one, or choose 'no bible' mode there.\n")
            return

        # Load bible files and tell the writer exactly what was loaded
        bible_static = load_bible_static(paths["bible_static"])
        bible_active = load_bible_active(paths["bible_active"])
        print(f"✓ Static bible loaded     ({len(bible_static)} characters)")
        print(f"✓ Active bible loaded     ({len(bible_active)} characters)")

        # Build the system prompt: base prompt + both bibles
        # This whole block gets cached after the first call — 90% cost saving
        system_with_bible = (
            SYSTEM_PROMPT_WITH_BIBLE
            + "\n\n─── STATIC BIBLE ───────────────────────────\n"
            + bible_static
            + "\n\n─── ACTIVE BIBLE (current position) ────────\n"
            + bible_active
        )
        sessions_dir = paths["sessions_dir"]

    if sessions_dir:
        session = load_session(sessions_dir)
    else:
        session = {"date": date.today().isoformat(), "model": MODEL, "turns": []}

    turn_count = len(session["turns"]) // 2
    if turn_count > 0:
        print(f"✓ Session resumed         ({turn_count} turns from today)")
    else:
        print(f"✓ New session started     ({date.today().isoformat()})")

    print("\nType your message. Commands:")
    print("  /show       — print full API payload on next call")
    print("  /hide       — stop printing payload")
    print("  /status     — show session stats")
    print("  /summarize  — distill this session into bible-ready notes (you approve before saving)")
    print("  /quit       — exit\n")

    # The conversation turns — this is what grows each session
    # Starts from today's saved session
    conversation_turns = list(session["turns"])

    global SHOW_PAYLOAD

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSession saved. Goodbye.")
            break

        if not user_input:
            continue

        # Commands
        if user_input == "/quit":
            print("Session saved. Goodbye.")
            break
        elif user_input == "/show":
            SHOW_PAYLOAD = True
            print("Payload display ON\n")
            continue
        elif user_input == "/hide":
            SHOW_PAYLOAD = False
            print("Payload display OFF\n")
            continue
        elif user_input == "/status":
            turns = len(conversation_turns) // 2
            chars = sum(len(t["content"]) for t in conversation_turns)
            print(f"\nTurns this session: {turns}")
            print(f"Context size: ~{chars} characters (~{chars//4} tokens)")
            if sessions_dir:
                print(f"Session file: {get_session_path(sessions_dir)}\n")
            else:
                print("Session file: none (no-bible mode, not persisted)\n")
            continue
        elif user_input == "/summarize":
            if no_bible:
                print("\nNo bible loaded this session — nothing to save a summary into.")
                print("You can still read the summary below, just won't be filed anywhere.\n")

            print("\nDistilling this session...\n")
            try:
                summary = summarize_session(client, system_with_bible, conversation_turns, dry_run=dry_run)
            except Exception as e:
                print(f"Couldn't summarize: {e}\n")
                continue

            print("─── SESSION SUMMARY ────────────────────────")
            print(summary)
            print("─────────────────────────────────────────────\n")

            if no_bible:
                continue

            approve = input("Save this into bible_active.json? (yes/no): ").strip().lower()
            if approve.startswith("y"):
                apply_summary_to_bible(summary, paths["bible_active"])
            else:
                print("Not saved. Nothing changed.\n")
            continue

        # Add user turn to conversation
        conversation_turns.append({"role": "user", "content": user_input})

        # Call the API
        print("\nSparring partner: ", end="", flush=True)
        try:
            response = call_api(client, system_with_bible, conversation_turns, dry_run=dry_run)
        except Exception as e:
            print(f"\nAPI ERROR: {e}")
            conversation_turns.pop()   # remove the user turn we just added
            continue

        print(response)
        print()

        # Add assistant turn
        conversation_turns.append({"role": "assistant", "content": response})

        # Save immediately — every single turn (skipped entirely in no-bible mode)
        session["turns"] = conversation_turns
        if sessions_dir:
            save_session(session, sessions_dir)

if __name__ == "__main__":
    main()
