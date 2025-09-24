The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: Extending NPS support to MIDI files

## User desires
Enhance the existing Clone Hero-style notes-per-second integration so MIDI (`.mid`) charts are parsed alongside `.chart` files, letting cached scans and UI tooling report Avg/Peak NPS for either format.

## Specifics of user desires
Refactor the scanner's NPS helper into a dispatcher that calls separate parsers for `.chart` and `.mid` files. Implement the MIDI parser using `mido` to read `ticks_per_beat`, collect tempo changes, locate the guitar track by name, and compute chord-mode Avg/Peak NPS. Ensure the scan cache backfills missing NPS for either extension and that difficulty weighting/tooltips automatically benefit from the broader coverage.

## Actions taken
- Wrapped `compute_chart_nps` in an extension-aware dispatcher and extracted shared tick-to-time math into `_compute_nps_from_ticks` for reuse.
- Added `compute_chart_nps_mid` to load MIDI charts with `mido`, build the tempo map, identify the guitar track (with a fallback to the densest note track), and compute chord-based Avg/Peak NPS.
- Updated cache hydration and fresh scan paths so `.chart` and `.mid` songs both call the dispatcher, repopulating missing NPS rows when needed.
- Ran `python -m compileall ch_career_mode` to confirm the modules compile after the refactor.

## Helpful hints about conversation & relevant code paths:
- The dispatcher, helper, and MIDI parser live in `ch_career_mode/scanner.py` (`compute_chart_nps`, `_compute_nps_from_ticks`, `compute_chart_nps_mid`).
- Cached scans backfill NPS within `ScanWorker.run`; GUI weighting/tooltip code already consumes the cached metrics without additional changes.

With this context in mind, I have a follow up query:
