The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: Prevent overlapping library scans during background NPS processing

## User desires
Ensure only one `ScanWorker` runs at a time, disabling the Scan controls while background NPS jobs finish so the cache and UI stay consistent.

## Specifics of user desires
When a scan starts, the Scan button/menu should gray out with a tooltip explaining to wait, additional scan requests should be ignored with a small notice, and the controls re-enable once the worker emits its final `nps_done` signal.

## Actions taken
- Added state tracking in `MainWindow` to prevent launching another scan while one is active and to restore availability when `nps_done` fires.
- Disabled the Scan controls and updated their tooltips during an active scan, displaying an informational dialog if the user tries to start a second scan.
- Re-ran `python -m compileall ch_career_mode` to confirm the application still compiles after the UI updates.

## Helpful hints about conversation & relevant code paths:
- `ch_career_mode/gui.py` manages Scan button state, background NPS progress handling, and user notifications.
- The `_set_scan_controls_enabled` helper centralizes enabling/disabling both the button and any related actions.

With this context in mind, I have a follow up query:
