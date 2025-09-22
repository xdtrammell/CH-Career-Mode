# Codex Session Notes

## Track your most recent session notes in `S:/CH-Career-Mode/.codex/latest-session.md` (MANDATORY)

During all sessions, keep a record of the discussion happening in a markdown file in `S:/CH-Career-Mode/.codex/latest-session.md`.

That markdown file should have the format:

```
The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: <discussion topic>

## User desires
<Brief description of what the user wants, the overall purpose and goal>

## Specifics of user desires
<More detailed version of the above, with details about specific the user is looking for>

## Actions taken
<List of steps taken to help the user>

## Helpful hints about conversation & relevant code paths:
<List of hints or codepaths that were particularly informative or helpful during the session>

With this context in mind, I have a follow up query:
\```

## Session-notes rule (MANDATORY)

- After **every** assistant turn the agent **MUST** update `S:/CH-Career-Mode/.codex/latest-session.md` with the standard template.

- Skipping this step is considered a violation of the instructions.

As we have conversations, I want you to update this file every time you complete a response, with updated details about the conversation/session to that point.
