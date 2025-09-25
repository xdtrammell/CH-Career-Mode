# Clone Hero Career Mode Builder

Clone Hero Career Mode Builder is a desktop tool that helps you design and export custom **career mode setlists** for [Clone Hero](https://clonehero.net/). It scans your Clone Hero songs library, automatically evaluates difficulty, and arranges songs into tiers that feel authentic to the classic Guitar Hero career progression.

## Features

- 🎵 **Song Library Scanner**
  - Recursively scans your Clone Hero `songs` folder.
  - Extracts metadata (title, artist, charter, genre, length, difficulty).
  - Detects chart files (`.chart`, `.mid`) and verifies guitar parts exist.
  - Computes **Average and Peak Notes Per Second (NPS)** for true difficulty scoring.
  - Caches results in a local SQLite database for faster re-scans.

- 📊 **Smart Difficulty Scoring**
  - Combines in-game difficulty ratings with song length and NPS values.
  - Optionally lowers Harmonix/Neversoft official chart difficulties for balance.
  - Marks and handles very long tracks differently when tiering.

- 🏆 **Automatic Tiering**
  - Auto-assigns songs into configurable tiers (like Guitar Hero setlists).
  - Options for:
    - Number of tiers and songs per tier
    - Genre grouping for balanced tiers
    - Limiting duplicate artists per tier
    - Keeping meme songs out of progression
    - Enforcing minimum difficulty per tier
    - Special “Artist Career Mode” to generate a career for one artist only

- 🎨 **Tier Naming Themes**
  - Built-in presets inspired by Guitar Hero careers (GH1, GH2, etc.).
  - Procedural generator for fresh tier names each run.
  - Custom/manual tier names supported.

- 🖱️ **Drag-and-Drop GUI**
  - Modern Qt-based interface (PySide6).
  - Search, filter, and drag songs between library and tiers.
  - Double-click to remove songs from tiers.
  - Adjustable themes and difficulty settings with instant feedback.

- 📦 **Export to Clone Hero**
  - Exports arranged tiers into valid `.setlist` binary files.
  - Option to export one combined setlist or one `.setlist` per tier.
  - Includes built-in validation of setlist integrity.

- ⚡ **Performance Optimizations**
  - Caches scan results and only updates changed songs.
  - Deduplicates charts by MD5 hash.
  - Runs scanning in a background thread with progress feedback.

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/xdtrammell/CH-Career-Mode.git
cd CH-Career-Mode
pip install -r requirements.txt
```

### Requirements
- Python 3.9+
- [PySide6](https://pypi.org/project/PySide6/)
- [mido](https://pypi.org/project/mido/) (installed automatically if missing)
- Standard library modules (sqlite3, configparser, etc.)

## Usage

### Run from source

```bash
python -m ch_career_mode
```

### Executable build (optional)

You can bundle the project into a standalone `.exe` with **PyInstaller**:

```bash
pyinstaller --clean --noconfirm -w -F CH_Career_Mode_Setlist_Gen.py --name CH_Career_Builder --hidden-import mido
```

The generated executable will launch the GUI directly.

### Inside the App

1. Pick your Clone Hero songs folder.
2. Click **Scan** to build your library.
3. Adjust filters (difficulty, meme songs, genre grouping, etc.).
4. Click **Auto-Arrange** to generate tiers, or drag songs manually.
5. Export your custom career mode as `.setlist` files.

## Configuration

Settings are saved automatically between runs using Qt’s built-in `QSettings`. This includes:
- Last used songs folder
- Tier theme and counts
- Difficulty filters
- Meme/official chart toggles
- Artist mode

Cache data (songs metadata and NPS values) is stored in `.cache/songs.sqlite` in the project or executable directory.

## Contributing

Contributions are welcome! Whether it’s fixing bugs, improving performance, or suggesting new features, feel free to open an issue or PR.

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.
