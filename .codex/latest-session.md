The most recent discussion I had with codex was the following. Please use these notes as informative context, so you can catch up and we can re-start the conversation accordingly.

# Topic: Dial back CPU usage of background NPS scanning

## User desires
Reduce CPU contention during background NPS calculations by leaving spare cores idle and keeping the UI responsive.

## Specifics of user desires
Adjust the worker pool sizing so that the scanner uses at most `os.cpu_count() - 2` workers (with a minimum of one), optionally smoothing CPU spikes, while preserving the faster background scan behavior.

## Actions taken
- Updated `ScanWorker`'s background executor configuration to derive its worker count from `os.cpu_count() - 2` while respecting the total number of jobs.
- Recompiled the package with `python -m compileall ch_career_mode` to ensure syntax correctness.
- Committed the changes with a message indicating the spare core reservation for NPS scanning.

## Helpful hints about conversation & relevant code paths:
- `ch_career_mode/scanner.py` houses the worker pool sizing logic for the background NPS phase.
- The executor initialization now stores the detected CPU count and subtracts two when selecting a worker limit.

With this context in mind, I have a follow up query:
