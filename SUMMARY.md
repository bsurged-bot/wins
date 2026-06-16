# Project Summary

**Sparring Partner** is a transparent, file-based discussion tool for writers, built on the Anthropic API.

It is not a writing assistant in the generative sense — it never produces prose for the user. Instead it functions as a literary sparring partner: a conversational presence that holds a writer's characters, world, and decisions consistently across sessions, asks the questions a writer hasn't asked yet, and pushes back hard against any request to generate text on the writer's behalf.

**Problem it addresses:** most AI writing tools collapse the distance between thinking about a story and producing one, which can erode a writer's own voice and skill over time. This tool is designed to preserve that distance deliberately — it amplifies a writer's thinking without replacing it.

**How it works technically:** each project is a folder containing a static bible (world, characters, philosophy — rarely changes, cached for cost efficiency), an active bible (current position, decisions, open questions — updated each session with the writer's approval), and a dated session history. There is no database, vector store, or hidden state; everything is plain text or JSON, and every API call can be inspected before it's sent.

**Notable design choices:**
- A hard, non-negotiable system-prompt constraint against generating prose
- Writer approval required before any session content becomes part of the permanent bible
- A dry-run mode that exercises the entire application without requiring an API key or Anthropic account
- Full multi-project isolation, with a master registry for switching between stories
- An import path that converts existing notes or summaries into the bible format, explicitly distinguishing settled decisions from open questions (marked with a `#` prefix in source documents)

Built as a personal tool first; designed to be usable by other writers without modification.
