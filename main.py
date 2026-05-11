"""
Entry point — captures iPhone Mirroring and parses the Word Hunt grid.
"""
import sys
from capture import capture_phone_mirroring
from grid import parse_grid, print_grid


def main():
    print("=== Word Hunt Assistant ===\n")

    print("[1/2] Capturing iPhone Mirroring window...")
    try:
        img, bounds = capture_phone_mirroring()
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    print("\n[2/2] Detecting and parsing grid...")
    letters = parse_grid(img, save_debug=True)

    print("\nDetected grid:")
    print_grid(letters)
    print("\nFlat list (row by row):", [l for row in letters for l in row])


if __name__ == "__main__":
    main()
