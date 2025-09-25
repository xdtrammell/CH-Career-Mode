"""PyInstaller-specific entry point that keeps background workers headless."""

import multiprocessing

from ch_career_mode.__main__ import main


if __name__ == "__main__":
    # Required when freezing on Windows so multiprocessing workers don't spawn
    # additional Qt windows; normal `python -m ch_career_mode` execution uses
    # the package entry point directly.
    multiprocessing.freeze_support()
    main()
