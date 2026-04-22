"""experiments/maze/maze_world.py — MazeWorld helper per v2 §TASK-5.

Pure utility. Holds NO Substrate / Bus / Cluster / Engine reference.
Spec: v2 §TASK-5 → "MazeWorld helper class".

Representation:
    self._openings: Set[frozenset]  — unordered pairs {cellA, cellB} that are
                                      reachable in one step (i.e. no wall).
    self.walls    : Set[Tuple[Cell,Cell]]  — ordered-pair complement for
                                      external consumers.

The recursive backtracker naturally records openings (edges knocked out); walls
are derived lazily for external queries.
"""
from __future__ import annotations

import heapq
import random
from typing import List, Set, Tuple

import numpy as np

Cell = Tuple[int, int]   # (col, row)


class MazeWorld:
    """Procedural rectangular maze with A* oracle."""

    def __init__(self, width: int, height: int, seed: int = 0):
        self.width = int(width)
        self.height = int(height)
        self._seed = int(seed)

        self._openings: Set[frozenset] = self._carve(self.width, self.height, self._seed)

        self.start: Cell = (0, 0)
        self.goal: Cell = (self.width - 1, self.height - 1)

        # Derive the ordered-pair wall set as the complement of openings.
        # Every adjacent in-bounds pair is either an opening or a wall.
        all_edges: Set[frozenset] = set()
        for c in range(self.width):
            for r in range(self.height):
                if c + 1 < self.width:
                    all_edges.add(frozenset({(c, r), (c + 1, r)}))
                if r + 1 < self.height:
                    all_edges.add(frozenset({(c, r), (c, r + 1)}))
        wall_edges = all_edges - self._openings
        self.walls: Set[Tuple[Cell, Cell]] = set()
        for e in wall_edges:
            a, b = tuple(e)
            # Canonicalise: smaller cell first for determinism.
            if a > b:
                a, b = b, a
            self.walls.add((a, b))

    # ── recursive-backtracker carve ──────────────────────────────────────────

    @staticmethod
    def _carve(width: int, height: int, seed: int) -> Set[frozenset]:
        rng = random.Random(seed)
        openings: Set[frozenset] = set()
        visited: Set[Cell] = set()

        def in_bounds(c: int, r: int) -> bool:
            return 0 <= c < width and 0 <= r < height

        # Iterative stack-based DFS.
        stack: List[Cell] = [(0, 0)]
        visited.add((0, 0))
        while stack:
            c, r = stack[-1]
            candidates: List[Cell] = []
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc, nr = c + dc, r + dr
                if in_bounds(nc, nr) and (nc, nr) not in visited:
                    candidates.append((nc, nr))
            if not candidates:
                stack.pop()
                continue
            nxt = rng.choice(candidates)
            openings.add(frozenset({(c, r), nxt}))
            visited.add(nxt)
            stack.append(nxt)
        return openings

    # ── public interface (v2 §TASK-5 signatures) ─────────────────────────────

    def neighbours(self, cell: Cell) -> List[Cell]:
        """Return cells reachable from `cell` in one step (no wall between,
        within bounds). At most 4.
        """
        c, r = cell
        out: List[Cell] = []
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if 0 <= nc < self.width and 0 <= nr < self.height:
                if frozenset({(c, r), (nc, nr)}) in self._openings:
                    out.append((nc, nr))
        return out

    def cell_to_position(self, cell: Cell, dim: int) -> np.ndarray:
        """v[0]=col, v[1]=row, v[2:]=0."""
        v = np.zeros(int(dim), dtype=np.float64)
        v[0] = float(cell[0])
        if dim >= 2:
            v[1] = float(cell[1])
        return v

    def position_to_cell(self, v: np.ndarray) -> Cell:
        """Round v[0], v[1] to nearest valid in-bounds cell."""
        va = np.asarray(v, dtype=np.float64)
        c = int(round(float(va[0])))
        r = int(round(float(va[1]))) if len(va) >= 2 else 0
        c = max(0, min(self.width - 1, c))
        r = max(0, min(self.height - 1, r))
        return (c, r)

    def astar(self) -> List[Cell]:
        """Optimal path from start to goal (inclusive). Manhattan heuristic."""
        def h(cell: Cell) -> int:
            return abs(cell[0] - self.goal[0]) + abs(cell[1] - self.goal[1])

        start = self.start
        goal = self.goal

        # (f, tie, cell)
        open_heap: List[Tuple[int, int, Cell]] = []
        tie = 0
        heapq.heappush(open_heap, (h(start), tie, start))
        came_from: dict = {}
        g_score: dict = {start: 0}

        while open_heap:
            _, _, current = heapq.heappop(open_heap)
            if current == goal:
                # Reconstruct.
                path: List[Cell] = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path
            for nbr in self.neighbours(current):
                tentative = g_score[current] + 1
                if tentative < g_score.get(nbr, float("inf")):
                    came_from[nbr] = current
                    g_score[nbr] = tentative
                    tie += 1
                    heapq.heappush(open_heap, (tentative + h(nbr), tie, nbr))
        return []  # unreachable — shouldn't happen for a perfect maze

    def render_ascii(self) -> str:
        """Multi-line string. # = wall, . = floor, S = start, G = goal.

        Grid is (2W+1) × (2H+1) characters: border + cell + wall interleave.
        """
        w, h = self.width, self.height
        # Initialise full-wall grid.
        grid = [["#"] * (2 * w + 1) for _ in range(2 * h + 1)]

        # Cell centres.
        for c in range(w):
            for r in range(h):
                grid[2 * r + 1][2 * c + 1] = "."

        # Carve openings between cells.
        for edge in self._openings:
            a, b = tuple(edge)
            (ca, ra), (cb, rb) = a, b
            mid_c = ca + cb + 1  # 2*min(c)+1 + (max-min) = ca+cb+1 when they differ by 1 column; same for row
            mid_r = ra + rb + 1
            grid[mid_r][mid_c] = "."

        # Mark start and goal.
        sc, sr = self.start
        gc, gr = self.goal
        grid[2 * sr + 1][2 * sc + 1] = "S"
        grid[2 * gr + 1][2 * gc + 1] = "G"

        # Row 0 is top. To match natural (col, row) reading where row=0 is
        # the top row in most maze conventions, we emit rows in order.
        return "\n".join("".join(row) for row in grid)
