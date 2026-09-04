from __future__ import annotations

import pytest

from verifier_grounded_benchmark.evaluation.property_calculation.scoring.atom_identity import (
    score_atom_identity,
)
from verifier_grounded_benchmark.task.schema.common import validate_profiles


@pytest.mark.parametrize(
    ("answer", "partial_score", "expected"),
    [
        ("11 O", 0.5, 1.0),
        ("O", 0.5, 0.5),
        ("12 O", 0.5, 0.5),
        ("11 N", 0.5, 0.0),
        ("oxygen", 0.5, 0.0),
        ("3 N", 0.0, 1.0),
        ("N", 0.0, 0.0),
        ("2 N", 0.0, 0.0),
    ],
)
def test_atom_identity_scores_index_and_element(
    answer: str, partial_score: float, expected: float
) -> None:
    assert score_atom_identity(
        {"value": answer},
        {"value": "11 O" if partial_score else "3 N"},
        {
            "normalization": "atom_identity",
            "element_partial_score": partial_score,
        },
    ) == pytest.approx(expected)


@pytest.mark.parametrize("partial_score", [True, -0.1, 1.0])
def test_atom_identity_profile_rejects_invalid_partial_score(
    partial_score: object,
) -> None:
    with pytest.raises(ValueError, match="element_partial_score"):
        validate_profiles(
            {
                "atom": {
                    "property": "most_negative_mulliken_atom",
                    "type": "atom_identity",
                    "normalization": "atom_identity",
                    "element_partial_score": partial_score,
                    "provenance": {
                        "target_source": "expert_gold_answer",
                        "decay_source": "reviewed_atom_identity_policy",
                    },
                }
            }
        )
