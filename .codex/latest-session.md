The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: Integrating NPS metrics into difficulty scoring

## User desires
Add Clone Hero-style notes-per-second metrics to the scan cache and expose an optional setting that weights song difficulty/score by the computed Avg/Peak NPS values. Surface the NPS numbers in song tooltips.

## Specifics of user desires
Parse `.chart` files to compute average and peak NPS using Clone Hero's chord-based method, cache the values during scans, and re-use them from SQLite on subsequent runs. Provide a "Weight Difficulty by NPS" toggle that modifies the score formula (`base + avg*2 + peak*0.5`) for tiering/sorting when enabled, without changing existing behaviour when disabled. Update tooltips to display Avg/Peak NPS alongside other metadata.

## Actions taken
- Added NPS fields to the `Song` dataclass and updated `effective_score` to apply the weighting formula when requested.
- Extended `ScanWorker` to parse `.chart` files (`compute_chart_nps`), persist `nps_avg`/`nps_peak` in the cache, and hydrate cached songs with the stored values.
- Introduced the GUI setting/checkbox for weighting by NPS, adjusted library sorting, tier auto-arrange logic, and tooltips to respect the toggle, and surfaced Avg/Peak NPS in tooltips.
- Ran `python -m compileall ch_career_mode` to ensure the updated modules compile.

## Helpful hints about conversation & relevant code paths:
- NPS parsing lives in `ch_career_mode/scanner.py::compute_chart_nps`, and cache schema updates store the metrics.
- The weighting toggle and tooltip formatting are handled inside `ch_career_mode/gui.py` (see `_compose_song_tooltip`, `_refresh_tier_tooltips`, and `_weight_by_nps_enabled`).

With this context in mind, I have a follow up query:
