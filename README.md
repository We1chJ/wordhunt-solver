# Word Hunt Solver

A Mac tool that captures your iPhone Mirroring screen, OCRs the 4×4 letter grid, solves for every valid word, and auto-plays them by dragging the mouse through each path automatically.

![Word Hunt Solver in action](ss.png)

Requires macOS Sequoia+ with iPhone Mirroring.

---

## Setup

```bash
git clone https://github.com/We1chJ/wordhunt-solver.git
cd wordhunt-solver
pip install -r requirements.txt
pip install pyobjc-framework-Quartz pyobjc-framework-AppKit
python main.py
```

Grant **Screen Recording** permission to your terminal (System Settings → Privacy & Security → Screen Recording) so `mss` can capture the iPhone Mirroring window.

---

## Usage

| Action | How |
|---|---|
| Capture + solve | Click **Start** |
| Auto-play all words | Click **▶ Play All**, then switch to iPhone Mirroring |
| Stop | Press **Esc** |
| Browse words | **◀ / ▶** or arrow keys |

---

## Stack

`PaddleOCR` · `OpenCV` · `mss` · `tkinter` · `pyobjc (Quartz / AppKit)`

---

## Notes

- `wordbank.txt` doesn't cover every word Word Hunt accepts — some valid in-game words will be missed and the score shown is a lower bound. Wordbank contributions are very welcome.
- Grid coordinates are hardcoded for a standard iPhone Mirroring window (~316×696 pt).
- Auto-play needs **Accessibility** permission to send mouse events to other apps.

---

## Contributing

PRs and issues welcome. Areas that would benefit most: wordbank expansion, dynamic grid calibration, and score-optimized play ordering.
