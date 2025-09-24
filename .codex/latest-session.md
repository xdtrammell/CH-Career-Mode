The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: Parallelizing the library scanner for faster multi-core performance

## User desires
Improve Clone Hero library scanning performance on large collections without changing existing metadata, caching, or song ordering behavior.

## Specifics of user desires
Introduce parallel processing so multiple song folders are scanned simultaneously while keeping SQLite writes safe, maintaining GUI responsiveness, and preserving current scoring, ordering, and caching semantics.

## Actions taken
- Added a thread pool in `ch_career_mode/scanner.py` to distribute folder scans across CPU cores while retaining the existing ScanWorker/QThread structure.
- Created a helper to process individual song folders that mirrors the original metadata, MD5, and NPS parsing logic.
- Batched SQLite writes on the main thread, preserved duplicate filtering order, and kept periodic GUI progress updates intact.
- Ran `python -m compileall ch_career_mode` to confirm the module compiles.

## Helpful hints about conversation & relevant code paths:
- Parallel scanning logic lives in `ch_career_mode/scanner.py`, especially the new `_scan_song_folder` helper and updated `ScanWorker.run` implementation.
- Thread pool size defaults to `min(8, os.cpu_count())` and results are re-ordered to match the original traversal before emitting to the GUI.

With this context in mind, I have a follow up query:
