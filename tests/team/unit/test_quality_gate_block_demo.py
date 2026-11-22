"""
Demonstration of Quality Gate Enforcement.
Intentionally causes a mandatory condition failure to prove GitHub Actions CI
blocks pull request merging when quality standards are not met.
"""


def test_mandatory_quality_condition_violation():
    """Simulates a critical regression that triggers CI quality gate failure."""
    assert False, "CRITICAL DEFECT: Quality Gate Block Triggered - Merging Disallowed"
