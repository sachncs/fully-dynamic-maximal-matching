# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive module-, class-, and method-level docstrings across the
  entire `fdmm` package, including Google-style parameter, return,
  side-effect, complexity, and example sections.
- Algorithm background sections (paper section references, mathematical
  framing, inline pseudocode-style commentary) for the heavy paths in
  `fdmm.z_system`, `fdmm.edge_coloring`, and `fdmm.dynamic_matching`.
- Inline comments explaining the parity-tagged BFS in
  `edge_switch_inside_B` and the three-case Vizing recolouring argument
  in `color_single_edge`.
- Public re-exports from `fdmm.__init__` of the previously semi-private
  helpers: `edge_switch_inside_B`, `promote_u_vertex`, `recolour_for_edge`,
  `find_edge_of_color`, `color_single_edge`, `alternating_path`,
  `flip_path`, `missing_colors`, `backtrack_color`, `abb_edge_color`,
  `vizing_edge_color`, `build_z_system`, `build_multi_level_system`.
  The `run_benchmark_worker` helper (formerly `_run_benchmark_worker`)
  is now re-exported from `fdmm.parallel`.
- Public methods on `DynamicMaximalMatching`:
  `augment_m1_at_subphase_boundary`, `try_augment_m1`,
  `flip_augmenting_path` (formerly `_augment_m1_at_subphase_boundary`,
  `_try_augment_m1`, `_flip_augmenting_path`).
- Type-alias re-exports (`Edge`, `Matching`, `Vertex`, `canonical_edge`)
  on the package root for callers that prefer importing from `fdmm` directly.
- Updated user-facing docs: README API table, `docs/index.md`,
  `docs/architecture.md` now reflect the full public surface.

### Changed
- `fdmm/__init__.py` module docstring rewritten as a package overview
  (operating modes, supporting modules, paper reference). The
  pre-existing duplicate trailing docstring at the end of the file has
  been removed.
- Renamed the following `_name` helpers to public `name`:
  - `_edge_switch_inside_B` → `edge_switch_inside_B`
  - `_promote_u_vertex` → `promote_u_vertex`
  - `_recolour_for_edge` → `recolour_for_edge`
  - `_find_edge_of_color` → `find_edge_of_color`
  - `_augment_m1_at_subphase_boundary` → `augment_m1_at_subphase_boundary`
  - `_try_augment_m1` → `try_augment_m1`
  - `_flip_augmenting_path` → `flip_augmenting_path`
  - `_run_benchmark_worker` → `run_benchmark_worker`
- Applied `ruff format` to bring the four previously non-conforming
  files (`dynamic_matching.py`, `edge_coloring.py`, `visualise.py`,
  `z_system.py`) back inside the 88-column budget.

### Fixed
- Removed an invalid trailing-docstring duplication in `fdmm/__init__.py`.
- Cleaned up `SyntaxWarning: invalid escape sequence` warnings for
  LaTeX-style sequences (e.g. `\deg`, `\Lambda`, `\Theta`) by ensuring
  every docstring containing such sequences uses a raw-string prefix.

### Atomic commits in this release

| Commit  | Date (UTC+05:30)         | Subject |
|---------|--------------------------|---------|
| `4b9120c` | 2026-07-11 18:07:34 +05:30 | docs: comprehensive module/class/method docstrings and inline comments |
| `6c13bbd` | 2026-07-11 18:08:21 +05:30 | refactor: promote semi-private helpers to public API |
| `b415e13` | 2026-07-11 18:08:33 +05:30 | style: apply ruff format to the four files that no longer conform |
| `7bcca23` | 2026-07-11 18:09:25 +05:30 | docs: refresh user-facing references to the public API surface |

## [0.4.1] - 2026-05-18

### Fixed

- Bug fixes and stability improvements

## [0.4.0] - 2026-05-18

### Added

- Multi-level mode with recursive k-level z-subgraph system
- Comprehensive test coverage including stress tests
- Simulation utilities for random update sequences and replay
- Explicit update-work counters (UpdateAccountant)
- Invariant checking module (invariants.py)

### Changed

- Improved rematch logic for U, B, and A vertex types

## [0.3.0] - 2026-05-18

### Added

- MIT LICENSE file
- CHANGELOG.md
- Expose `__version__` in package root

### Fixed

- CI: fix mypy path (`fdmm/` → `src/fdmm/`)

### Changed

- Updated pyproject.toml with authors and urls

## [0.2.0] - 2026-05-18

### Added

- Initial multi-level mode
- Extended test coverage

## [0.1.0] - 2026-05-18

### Added

- Initial release with basic mode
- z-subgraph system construction and invariants
- Vizing edge colouring
- Dynamic graph data structure
- Greedy maximal matching
- Command-line interface
