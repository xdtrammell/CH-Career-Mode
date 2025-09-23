# Codex Session Notes

## Track your most recent session notes in `.codex/latest-session.md`
If this file does not exist go ahead and create it. (MANDATORY)

During all sessions, keep a record of the discussion happening in a markdown file called `.codex/latest-session.md`.

That markdown file should have the format:

```
The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: <discussion topic>

## User desires
<Brief description of what the user wants, the overall purpose and goal>

## Specifics of user desires
<More detailed version of the above, with details about what the user is looking for>

## Actions taken
<List of steps taken to help the user>

## Helpful hints about conversation & relevant code paths:
<List of hints or codepaths that were particularly informative or helpful during the session>

With this context in mind, I have a follow up query:
```

---

## Session-notes rule (MANDATORY)

- After **every** assistant turn the agent **MUST** update `.codex/latest-session.md` with the standard template.
- Skipping this step is considered a violation of the instructions.
- As we have conversations, the agent must update this file every time they complete a response, with updated details about the conversation/session to that point.
- Ensure `.codex/latest-session.md` remains checked into version control so future sessions start with the correct template in place.
