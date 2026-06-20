# Frequently Asked Questions

## General

### What is FDMM?

FDMM is a Python implementation of the algorithm from "A Faster Deterministic Algorithm for Fully Dynamic Maximal Matching" (Chuzhoy, Khanna, Song — STOC 2026, arXiv:2605.00797v1). It maintains a maximal matching in an undirected graph under online edge insertions and deletions.

### What is a maximal matching?

A maximal matching is a set of edges such that no edge can be added without sharing a vertex with an existing edge. It is a **maximal** (not maximum) matching — it cannot be extended, but it may not be the largest possible.

### What is the difference between basic and multi-level mode?

| Mode | Amortised Update Time | Complexity |
|------|----------------------|------------|
| Basic | Õ(n<sup>2/3</sup>) | Single-level z-system |
| Multi-level | n<sup>1/2+o(1)</sup> | k-level recursive system (k = Θ(log n)) |

Multi-level mode is asymptotically faster but has higher constant overhead. Use basic mode for small graphs or when simplicity is preferred.

### Is this a faithful reproduction of the paper?

Partially. Some components are exact, some are approximate, and some are unknown. See the [Fidelity Report](../README.md#fidelity-report) in the README and the detailed [Audit Report](audit_report.md).

## Usage

### When should I rebuild the z-system?

The algorithm handles rebuilds automatically based on phase length. You do not need to trigger rebuilds manually.

### How do I check if the matching is maximal?

```python
algo.is_maximal()  # Returns True if the matching is maximal
```

This performs a brute-force check and is O(n + m).

### What do the statistics counters mean?

See the [Interpreting Update Counters](../README.md#interpreting-update-counters) section in the README.

### Can I use this with weighted graphs?

No. FDMM maintains an unweighted maximal matching. The algorithm does not consider edge weights.

### What about parallel/concurrent access?

FDMM is not thread-safe. If you need concurrent access, use a lock or run separate instances.

## Development

### How do I run the tests?

```bash
pytest tests/ -v
```

### How do I check types?

```bash
mypy src/fdmm/
```

### How do I lint the code?

```bash
ruff check src/fdmm/ tests/ scripts/
```

### How do I format the code?

```bash
ruff format src/ tests/ scripts/
```

### How do I add a new invariant check?

1. Add the check function to `src/fdmm/invariants.py`
2. Add a call in `ZSubgraphSystem.check_all_invariants()` (in `z_system.py`)
3. Add tests in `tests/test_fdmm.py`

### How do I add a new command-line option?

Edit `src/fdmm/cli.py` and add an argument to the `argparse` parser. Update `scripts/demo.py` if the option should also be available there.

## Troubleshooting

### Tests fail with import errors

Ensure you've installed the package in editable mode:

```bash
pip install -e ".[dev]"
```

### mypy reports errors

The project uses strict mypy. Ensure you're using Python 3.10+ and have the latest mypy:

```bash
pip install --upgrade mypy
mypy src/fdmm/
```

### Performance is slower than expected

For small graphs (n < 100), constant factors dominate. The asymptotic bounds are only meaningful for large n. Use `python benchmarks/bench_fdmm.py` to measure throughput.
