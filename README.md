# Clone Hero Career Mode Builder

A modern tool for creating **career-style setlists** for [Clone Hero](https://clonehero.net/).  
This project automatically scans your song library, groups tracks into difficulty-based tiers, 
and exports native `.setlist` files compatible with Clone Hero. It aims to replicate the 
progression experience of Guitar Hero and Rock Band, while offering flexible customization.

---

## ✨ Features

- **Auto-scanning**: Recursively scans your Clone Hero `Songs/` folder and caches metadata.
- **Difficulty scoring**: Calculates song difficulty using `diff_guitar` and track length.
- **Tier builder**: Generates multi-tier setlists (e.g., 6–20 tiers) with ascending difficulty.
- **Genre grouping**: Optional toggle to group songs in each tier by genre family.
- **Artist cap**: Limit how many tracks per artist can appear in a tier.
- **Min difficulty filter**: Exclude trivial charts (diff 1–2) from tiers.
- **Meme filter**: Toggle to exclude meme-tagged genres from auto-arrange.
- **Official chart adjustment**: Option to lower Harmonix/Neversoft charts by 1 difficulty step.
- **Drag-and-drop GUI**: Rearrange tiers and songs manually with a modern Qt interface.
- **Export setlists**: Creates native `.setlist` files for Clone Hero (binary MD5 format).

---

## 📦 Installation

### Running from Source (Python 3.10+)

1. Clone this repo:
   ```bash
   git clone https://github.com/yourusername/CH-Career-Mode.git
   cd CH-Career-Mode
   ```

2. Create and activate a virtual environment:
   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. Run the app:
   ```powershell
   python -m ch_career_mode
   ```

### Windows EXE (no Python required)

Prebuilt executables are available under **Releases**.  
Just download the `.exe` and run it.

---

## 🚀 Usage

1. Launch the program.  
2. Select your Clone Hero `Songs` folder.  
3. Click **Scan** to load your library.  
4. Use **Auto-Arrange** to generate career tiers.  
   - Enable/disable toggles for genre grouping, meme filter, min difficulty, etc.  
5. Drag and drop songs if desired.  
6. Click **Export Setlist** to save `.setlist` files.  
   - Export all tiers separately or as one combined career setlist.  

---

## ⚙️ Settings

- **Tiers / Songs per Tier** – Controls structure of the setlist.  
- **Group songs in tiers by genre** – Keeps each tier genre-cohesive.  
- **Min difficulty** – Exclude easy beginner tracks.  
- **Max tracks by artist per tier** – Prevents tiers dominated by one band.  
- **Exclude meme songs** – Skips meme-tagged content.  
- **Lower official chart difficulty** – Treat Harmonix/Neversoft charts as 1 step easier.  

All preferences persist between runs via QSettings.

---

## 🛠 Development

This project is organized into modules with separation of concerns:

- `core.py` – Data models, constants, difficulty scoring.  
- `scanner.py` – Library scanning, song.ini parsing, cache (SQLite).  
- `tiering.py` – Auto-arrange logic, genre grouping, constraints.  
- `exporter.py` – Clone Hero `.setlist` binary writer/reader.  
- `gui.py` – PySide6 Qt interface and widgets.  
- `__main__.py` – Entrypoint to launch the app.  

Build a standalone executable with PyInstaller:
```powershell
pyinstaller --noconsole --onefile app_entry.py
```

---

## 📈 Roadmap

- Web-based version (hosted) for easier sharing.  
- More advanced difficulty models (note density, BPM).  
- Smarter genre-family weighting across tiers.  
- Theme customization for venues / set names.  

---

## 🤝 Contributing

Pull requests and feature suggestions are welcome!  
Open an issue if you find bugs or have ideas.

---

## 📜 License

MIT License © 2025 YourName
