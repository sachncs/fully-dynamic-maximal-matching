"""Explicit counters for update work and phase-level accounting.

The paper's amortised-time analysis is not directly executable in Python.
This module implements explicit counters that record the work performed
during updates, rebuilds, and rematching scans so that experiments can
empirically measure costs without claiming theorem correctness.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UpdateAccountant:
    """Counters for auditing the cost of dynamic updates.

    Attributes are self-explanatory; all counters start at zero.
    """

    total_updates: int = 0
    total_insertions: int = 0
    total_deletions: int = 0
    phase_rebuilds: int = 0
    subphase_rebuilds: int = 0
    rematch_u_scans: int = 0
    rematch_b_scans: int = 0
    rematch_a_scans: int = 0
    greedy_rebuilds: int = 0
    stale_cleanups: int = 0
    phase_update_work: int = field(default=0, repr=False)

    def record_insertion(self) -> None:
        self.total_updates += 1
        self.total_insertions += 1
        self.phase_update_work += 1

    def record_deletion(self) -> None:
        self.total_updates += 1
        self.total_deletions += 1
        self.phase_update_work += 1

    def record_phase_rebuild(self, work_estimate: int = 0) -> None:
        self.phase_rebuilds += 1
        self.phase_update_work = work_estimate

    def record_subphase_rebuild(self, work_estimate: int = 0) -> None:
        self.subphase_rebuilds += 1
        self.phase_update_work += work_estimate

    def record_rematch_u_scan(self, scanned: int = 1) -> None:
        self.rematch_u_scans += scanned
        self.phase_update_work += scanned

    def record_rematch_b_scan(self, scanned: int = 1) -> None:
        self.rematch_b_scans += scanned
        self.phase_update_work += scanned

    def record_rematch_a_scan(self, scanned: int = 1) -> None:
        self.rematch_a_scans += scanned
        self.phase_update_work += scanned

    def record_greedy_rebuild(self, work: int = 0) -> None:
        self.greedy_rebuilds += 1
        self.phase_update_work += work

    def record_stale_cleanup(self, count: int = 1) -> None:
        self.stale_cleanups += count
        self.phase_update_work += count

    def snapshot(self) -> dict[str, int]:
        """Return a read-only snapshot of all counters."""
        return {
            "total_updates": self.total_updates,
            "total_insertions": self.total_insertions,
            "total_deletions": self.total_deletions,
            "phase_rebuilds": self.phase_rebuilds,
            "subphase_rebuilds": self.subphase_rebuilds,
            "rematch_u_scans": self.rematch_u_scans,
            "rematch_b_scans": self.rematch_b_scans,
            "rematch_a_scans": self.rematch_a_scans,
            "greedy_rebuilds": self.greedy_rebuilds,
            "stale_cleanups": self.stale_cleanups,
        }
