# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Improved edge-switching rule inside B for z-system construction (Step 2)
- Fast ABB-approximation edge colouring with conflict resolution
- Subphase management with M_1 augmentation at subphase boundaries
- Incremental M* maintenance starting from M_1 colour class
- Recursive multi-level rebuild derivation via `build_multi_level_system`
- Visualisation module (`fdmm.visualise`) for z-subgraph system and matching state
- Parallel benchmarking module (`fdmm.parallel`) for comparing modes
- Pre-commit hooks configuration (.pre-commit-config.yaml)
- Coverage threshold (80%) enforced in CI
- CONTRIBUTING.md with full contributor guidelines
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- SECURITY.md with vulnerability reporting policy
- .editorconfig for consistent formatting across editors
- .gitattributes for line ending normalisation
- GitHub Issue templates (bug report, feature request)
- GitHub Pull Request template
- Dependabot configuration for automated dependency updates
- GitHub funding configuration
- docs/getting-started.md — step-by-step getting started guide
- docs/architecture.md — internal architecture documentation
- docs/faq.md — frequently asked questions

### Changed

- Rewrote README.md with comprehensive documentation, badges, and tables
- Updated CHANGELOG.md to follow Keep a Changelog format
- Updated pyproject.toml with repository URLs, keywords, and bugs URL
- Updated CI workflow with formatting check, dependency caching, and coverage threshold
- Improved .gitignore with additional IDE and tool entries
- Edge colouring now uses fast ABB approximation instead of Vizing fallback

### Fixed

- Version string inconsistency between pyproject.toml and __init__.py

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
