"""
Solves a 4x4 Word Hunt grid by DFS over all 8-neighbor paths,
checking found words against wordbank.txt.
"""

from pathlib import Path

WORDBANK_PATH = Path(__file__).parent / "wordbank.txt"
MIN_WORD_LEN = 3

_words: set[str] | None = None
_prefixes: set[str] | None = None


def preload() -> None:
    """Load wordbank into module-level cache. Safe to call multiple times."""
    global _words, _prefixes
    if _words is not None:
        return
    print("[solver] Loading wordbank...", end=" ", flush=True)
    words: set[str] = set()
    prefixes: set[str] = set()
    for line in WORDBANK_PATH.read_text().splitlines():
        w = line.strip().upper()
        if not w:
            continue
        words.add(w)
        for i in range(1, len(w) + 1):
            prefixes.add(w[:i])
    _words, _prefixes = words, prefixes
    print(f"{len(_words)} words loaded.")


def neighbors(row: int, col: int, rows: int = 4, cols: int = 4) -> list[tuple[int, int]]:
    result = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            r, c = row + dr, col + dc
            if 0 <= r < rows and 0 <= c < cols:
                result.append((r, c))
    return result


def solve(grid: list[list[str]]) -> list[tuple[str, list[tuple[int, int]]]]:
    """
    Return a list of (word, path) for every valid word found in the grid,
    including duplicate words reached via different tile paths.
    Results are sorted longest-first, then alphabetically.
    """
    preload()
    words, prefixes = _words, _prefixes
    found: list[tuple[str, list[tuple[int, int]]]] = []

    rows, cols = len(grid), len(grid[0])

    def dfs(r: int, c: int, current: str, path: list[tuple[int, int]], visited: set[tuple[int, int]]):
        current += grid[r][c]
        path = path + [(r, c)]
        visited = visited | {(r, c)}

        if current not in prefixes:
            return
        if len(current) >= MIN_WORD_LEN and current in words:
            found.append((current, path))

        for nr, nc in neighbors(r, c, rows, cols):
            if (nr, nc) not in visited:
                dfs(nr, nc, current, path, visited)

    for r in range(rows):
        for c in range(cols):
            dfs(r, c, "", [], set())

    return sorted(found, key=lambda x: (-len(x[0]), x[0]))


def print_solutions(solutions: list[tuple[str, list[tuple[int, int]]]]) -> None:
    if not solutions:
        print("No words found.")
        return
    print(f"Found {len(solutions)} results:\n")
    for word, path in solutions:
        coords = " → ".join(f"({r},{c})" for r, c in path)
        print(f"  {word:15s} {coords}")
