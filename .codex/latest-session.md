The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: Increasing scanner concurrency for faster large-library scans

## User desires
Improve Clone Hero library scanning performance on very large collections without altering metadata, caching, or ordering behavior.

## Specifics of user desires
Boost parallel processing within the scanner so more CPU cores are utilized (around 75% of available cores) while keeping SQLite writes safe, maintaining GUI responsiveness, and preserving existing scoring, ordering, and caching semantics.

## Actions taken
- Added a thread pool in `ch_career_mode/scanner.py` to distribute folder scans across CPU cores while retaining the existing ScanWorker/QThread structure.
- Created a helper to process individual song folders that mirrors the original metadata, MD5, and NPS parsing logic.
- Tuned the scanner to size its thread pool dynamically at ~75% of detected CPU cores, with an opt-in override, while preserving batching, ordering, and UI update behavior.
- Ran `python -m compileall ch_career_mode` to confirm the module compiles.

## Helpful hints about conversation & relevant code paths:
- Parallel scanning logic lives in `ch_career_mode/scanner.py`, especially the `_scan_song_folder` helper and updated `ScanWorker.run` implementation.
- Thread pool size now defaults to roughly 75% of detected CPU cores (minimum 1) unless an override is provided, and results are re-ordered to match the original traversal before emitting to the GUI.

With this context in mind, I have a follow up query:
