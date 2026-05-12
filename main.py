"""
Entry point — captures iPhone Mirroring and parses the Word Hunt grid.

Usage:
    python main.py                    # watch mode: preloads models, waits for iPhone Mirroring
    python main.py debug_capture.png  # test against a saved image
"""
import sys
import time
import cv2
from grid import parse_grid, print_grid, preload_ocr
from solver import solve, print_solutions, preload as preload_words


def run_once(img: "cv2.Mat") -> None:
    letters = parse_grid(img, save_debug=True)
    print("\nDetected grid:")
    print_grid(letters)
    print("\nSolving...")
    solutions = solve(letters)
    print_solutions(solutions)


def watch_mode() -> None:
    from capture import capture_phone_mirroring, get_phone_mirroring_bounds

    print("=== Word Hunt Assistant — Watch Mode ===\n")

    print("[init] Preloading models...")
    preload_words()
    preload_ocr()
    print("[init] All models ready. Waiting for iPhone Mirroring...\n")

    window_was_open = False

    while True:
        bounds = get_phone_mirroring_bounds()

        if bounds is None:
            if window_was_open:
                print("\n[watch] iPhone Mirroring closed. Waiting for next session...")
                window_was_open = False
            time.sleep(1)
            continue

        if not window_was_open:
            print("[watch] iPhone Mirroring detected — capturing in 2s...")
            time.sleep(2)  # let the game grid fully render
            window_was_open = True
            try:
                img, _ = capture_phone_mirroring()
            except RuntimeError as e:
                print(f"[watch] Capture failed: {e}")
                continue

            print()
            run_once(img)
            print("\n[watch] Done. Waiting for window to close for next game...\n")

        time.sleep(1)


def main() -> None:
    if len(sys.argv) > 1:
        path = sys.argv[1]
        img = cv2.imread(path)
        if img is None:
            sys.exit(f"Could not load image: {path}")
        print(f"=== Word Hunt Assistant ===\n")
        print(f"[1/2] Using saved image: {path}")
        preload_words()
        preload_ocr()
        print("\n[2/2] Parsing and solving...")
        run_once(img)
    else:
        watch_mode()


if __name__ == "__main__":
    main()
