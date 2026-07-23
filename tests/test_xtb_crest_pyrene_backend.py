from __future__ import annotations

from pathlib import Path

import pytest

from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb import (
    crest_pyrene,
)
from verifier_grounded_benchmark.evaluation.open_generation.verifiers.xtb.backend import (
    XTBRunResult,
)


PYRENE = "c1cc2ccc3cccc4ccc(c1)c2c34"
VALID = "Nc1cc2ccc3cccc4cc(C(=O)O)c(c1[N+](=O)[O-])c2c34"
SPEC = {
    "verifier_id": "xtb_pyrene_crest_energy_v1",
    "verifier_image": "verifier-grounded:dev",
    "property_name": "total_energy",
    "identity": {"reference_smiles": PYRENE, "formula": "C17H10N2O4"},
    "backend": {
        "random_seed": 61453,
        "charge": 0,
        "uhf": 0,
        "crest_timeout_seconds": 30,
        "xtb_timeout_seconds": 30,
        "xtb_version": "6.7.1",
    },
}
TASK = {"task_id": "xtb_pyrene_substituent_energy_min_020"}
CONSTRAINT = {"property": "total_energy"}


class FakeCrestRunner:
    def __init__(self, transform=None) -> None:
        self.calls = 0
        self.transform = transform or (lambda xyz: xyz)

    def search(
        self,
        initial_xyz: str,
        workdir: Path,
        timeout_seconds: float,
        *,
        spec: dict,
    ) -> crest_pyrene.CrestSearchResult:
        self.calls += 1
        transformed = self.transform(initial_xyz)
        return crest_pyrene.CrestSearchResult(
            (initial_xyz, transformed), (1.5, 0.0), "3.0.2"
        )


class FakeXTBRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(
        self, mode: str, xyz_path: Path, timeout_seconds: float, *, spec: dict
    ) -> XTBRunResult:
        self.calls += 1
        assert mode == "singlepoint"
        return XTBRunResult(
            stdout="| TOTAL ENERGY -123.456789 Eh\nnormal termination of xtb\n",
            stderr="",
            returncode=0,
        )


def test_pyrene_graph_delta_accepts_exact_three_substituents() -> None:
    mol = crest_pyrene.Chem.MolFromSmiles(VALID)

    properties = crest_pyrene.validate_pyrene_identity(mol, SPEC["identity"])

    assert properties["formula"] == "C17H10N2O4"
    assert properties["scaffold_match"] is True
    assert properties["substitution_site_indices"] == [0, 1, 3]
    assert properties["substituent_counts"] == {
        "nitro": 1,
        "amino": 1,
        "carboxyl": 1,
    }


@pytest.mark.parametrize(
    "smiles",
    [
        PYRENE,
        "Nc1cc2ccc3cccc4ccc(c1[N+](=O)[O-])c2c34",
        "Nc1cc2ccc3cccc4cc(C(=O)[O-])c(c1[N+](=O)[O-])c2c34",
        "CNC1=CC2=CC=C3C=CC=C4C=C(C(O)=O)C(=C1[N+]([O-])=O)C2=C34",
    ],
)
def test_pyrene_graph_delta_rejects_wrong_identity(smiles: str) -> None:
    mol = crest_pyrene.Chem.MolFromSmiles(smiles)

    with pytest.raises(crest_pyrene.PyreneIdentityError):
        crest_pyrene.validate_pyrene_identity(mol, SPEC["identity"])


def test_pyrene_crest_protocol_selects_lowest_and_runs_one_singlepoint() -> None:
    crest = FakeCrestRunner()
    xtb = FakeXTBRunner()

    result = crest_pyrene.evaluate_pyrene_energy_constraint(
        {"smiles": VALID},
        TASK,
        CONSTRAINT,
        SPEC,
        crest_runner=crest,
        xtb_runner=xtb,
    )

    assert result["outcome"] == "verified"
    assert crest.calls == 1
    assert xtb.calls == 1
    assert result["properties"]["crest_version"] == "3.0.2"
    assert result["properties"]["crest_conformer_count"] == 2
    assert result["properties"]["crest_min_relative_energy"] == 0.0
    assert result["properties"]["total_energy"] == -123.456789
    assert result["properties"]["pre_search_identity_match"] is True
    assert result["properties"]["post_crest_identity_match"] is True


def test_pyrene_crest_protocol_rejects_post_search_graph_change() -> None:
    changed_xyz = "5\nmethane\nC 0 0 0\nH .6 .6 .6\nH -.6 -.6 .6\nH -.6 .6 -.6\nH .6 -.6 -.6\n"
    crest = FakeCrestRunner(transform=lambda _: changed_xyz)

    result = crest_pyrene.evaluate_pyrene_energy_constraint(
        {"smiles": VALID},
        TASK,
        CONSTRAINT,
        SPEC,
        crest_runner=crest,
        xtb_runner=FakeXTBRunner(),
    )

    assert result["outcome"] == "candidate_rejected"
    assert result["failure_type"] == "structure_identity_error"


def test_parse_crest_xyz_ensemble_preserves_relative_energies() -> None:
    text = (
        "2\n-0.125\nH 0 0 0\nH 0 0 .7\n"
        "2\n0.500\nH 0 0 0\nH 0 0 .8\n"
    )

    conformers, energies = crest_pyrene.parse_xyz_ensemble(text)

    assert len(conformers) == 2
    assert energies == [-0.125, 0.5]
