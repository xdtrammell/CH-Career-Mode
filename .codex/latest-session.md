The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: Fixing MIDI NPS computation

## User desires
Ensure the MIDI NPS parser yields real Avg/Peak values by tolerating malformed bytes, choosing the correct guitar track, and counting shifted-lane gems.

## Specifics of user desires
Update `compute_chart_nps_mid` so it opens files with `clip=True`, builds tempo data while recording track metadata, prioritises guitar-labelled tracks ("PART GUITAR", "T1 GEMS", "NOTES"), falls back to the longest note track, and normalises note lanes via modulo 12 before computing Clone Hero-style chord NPS.

## Actions taken
- Reworked the MIDI parsing loop to collect tempo changes alongside track names, note counts, and lengths for better selection heuristics.
- Added priority keyword matching with a longest-track fallback and modulo-12 note normalisation before deduplicating chord ticks.
- Loaded MIDI files with `clip=True` and reused `_compute_nps_from_ticks` to output Avg/Peak NPS, then recompiled the package with `python -m compileall ch_career_mode`.

## Helpful hints about conversation & relevant code paths:
- All adjustments live in `ch_career_mode/scanner.py`, inside `compute_chart_nps_mid` and the shared `_compute_nps_from_ticks` helper.
- Scan worker logic already reuses `compute_chart_nps`, so improvements automatically flow into cache refreshes and UI consumers.

With this context in mind, I have a follow up query:
