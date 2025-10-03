# Codex Development Log Instructions

## Purpose
The `.codex/latest-session.md` file is used as an **ongoing development log**, preserving the full history of sessions, actions, and reasoning behind decisions. This enables traceability over time, so contributors (and automated systems) can understand why changes were made.

## File Location
- Path: `.codex/latest-session.md`
- Must be checked into version control.

## Logging Format
Each new session **appends** to the end of `.codex/latest-session.md` using the following structure:

```
# Session <number> — <date/time>

## Topic
<Discussion topic for this session>

## User Desires
<Brief description of what the user wanted, the overall purpose and goal>

## Specifics of User Desires
<Expanded version with relevant details and context>

## Actions Taken
<List of steps taken during this session>

## Helpful Hints
<Key code paths, insights, or debugging notes that were informative>

---
```

## Rules
1. **Do not overwrite** the `.codex/latest-session.md` file. Always **append new entries**.
2. Each session should increment the session number sequentially.
3. Include a timestamp (`YYYY-MM-DD HH:MM`) in the header.
4. Separate sessions with a horizontal rule (`---`).
5. Each section (`Topic`, `User Desires`, etc.) must contain at least one full sentence.
6. Avoid vague placeholders like “fixed stuff” — describe clearly enough that a future maintainer could retrace the work.
7. If a session continues work from a previous session, explicitly reference the prior session number in the `Topic` or `Actions Taken`.
8. When mentioning code changes, always include the file and function/class name (e.g., `gui.py — MainWindow._sync_tier_height`).    
9. Before writing a new session, always scan `.codex/latest-session.md` from top to bottom and detect the highest existing session number.  
10. The new session number must be exactly one greater than the highest found, regardless of ordering in the file.  
11. Never insert new sessions between existing ones — always append at the very end of the file.
12. All sessions must form a strictly increasing sequence (Session 1, Session 2, Session 3, …). If a mismatch is detected, assume the largest number is the latest and continue from there.

## Example
```
# Session 12 — 2025-09-25 05:20

## Topic
Optimize NPS calculations for large libraries.

## User Desires
Improve scanning performance across ~20,000 songs.

## Specifics of User Desires
The user noticed that notes-per-second (NPS) calculations slowed down scanning. They want optimization strategies without breaking current tiering logic.

## Actions Taken
- Profiled scanner.py performance.
- Suggested caching strategy for repeated NPS calculations.
- Added notes on thread management to avoid concurrent workers.

## Helpful Hints
- SQLite lock issues can occur when multiple scan workers are alive.
- Progress dialogs must wait for `finished` signals before re-enabling.

---
```
This log will serve as **documentation of development decisions**. Other programs or maintainers can:
- Parse the log for structured summaries of actions.
- Reconstruct the rationale behind design changes.
- Track how features evolved over time.
