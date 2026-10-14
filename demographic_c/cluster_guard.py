"""Component C — DPDP Act 2023 k-Anonymity Cluster Guard.

Enforces privacy-preserving data minimization by checking whether an
aggregate demographic cohort meets the minimum account threshold (k >= 50).

In accordance with the Digital Personal Data Protection (DPDP) Act 2023 principles
and institutional viva demonstration invariants:
    - Demographic outputs are AGGREGATE-ONLY (never individual census profiling).
    - Clusters with account_count < MIN_CLUSTER_SIZE are flagged with
      ``below_threshold = True``.
    - In the analyst UI and RAG query layer, sub-threshold clusters are visibly
      grayed out with a privacy badge — NEVER silently dropped or padded with
      synthetic accounts.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AnonymityAssessment:
    """Assessment result for an audience demographic cohort."""

    account_count: int
    min_cluster_size: int
    below_threshold: bool
    status_label: str
    privacy_notice: str


class ClusterGuard:
    """Enforces k-anonymity privacy thresholds on demographic clusters."""

    DEFAULT_MIN_CLUSTER_SIZE: int = 50
    DEFAULT_DEMO_MIN_CLUSTER_SIZE: int = 15

    def __init__(
        self,
        min_cluster_size: int | None = None,
        use_demo_threshold: bool = False,
    ) -> None:
        """Initialize the cluster guard.

        Args:
            min_cluster_size: Explicit minimum cluster size. If None, reads from
                environment variables (MIN_CLUSTER_SIZE or DEMO_MIN_CLUSTER_SIZE).
            use_demo_threshold: If True and min_cluster_size is None, uses
                DEMO_MIN_CLUSTER_SIZE (default 15) for offline viva seed demonstrations.
        """
        if min_cluster_size is not None:
            self._threshold = max(1, int(min_cluster_size))
        elif use_demo_threshold:
            raw_demo = os.getenv("DEMO_MIN_CLUSTER_SIZE", str(self.DEFAULT_DEMO_MIN_CLUSTER_SIZE))
            self._threshold = max(1, int(raw_demo))
        else:
            raw_env = os.getenv("MIN_CLUSTER_SIZE", str(self.DEFAULT_MIN_CLUSTER_SIZE))
            self._threshold = max(1, int(raw_env))

    @property
    def threshold(self) -> int:
        """Current k-anonymity threshold (minimum account count)."""
        return self._threshold

    def is_below_threshold(self, account_count: int) -> bool:
        """Check if an account cohort size violates the k-anonymity minimum.

        Args:
            account_count: Number of distinct accounts in the cluster.

        Returns:
            True if account_count < threshold (insufficient anonymity),
            False otherwise.
        """
        return account_count < self._threshold

    def assess(self, account_count: int) -> AnonymityAssessment:
        """Perform a formal privacy assessment for an account cohort.

        Args:
            account_count: Number of distinct accounts in the cluster.

        Returns:
            AnonymityAssessment dataclass with full diagnostic metadata.
        """
        below = self.is_below_threshold(account_count)
        if below:
            status = "SUPPRESSED_SUB_THRESHOLD"
            notice = (
                f"Cluster sample size (n={account_count}) is below the DPDP k-anonymity "
                f"threshold (k={self._threshold}). Aggregate details are tagged with "
                "below_threshold=True and restricted to high-level summary only."
            )
        else:
            status = "COMPLIANT_ANONYMIZED"
            notice = (
                f"Cluster sample size (n={account_count}) satisfies the k-anonymity "
                f"guard (k >= {self._threshold}). Aggregated distributions are valid for "
                "analytical intelligence and reporting."
            )

        return AnonymityAssessment(
            account_count=account_count,
            min_cluster_size=self._threshold,
            below_threshold=below,
            status_label=status,
            privacy_notice=notice,
        )
