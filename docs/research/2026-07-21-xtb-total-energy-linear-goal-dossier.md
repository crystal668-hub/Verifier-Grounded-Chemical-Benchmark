# xTB Same-Molecule Total-Energy Dossier

**Date:** 2026-07-21  
**Decision:** Approved for the third parameter batch  
**Scoring version:** `linear_goal_v2`

## Protocol

Both profiles use xTB 6.7.1, GFN2-xTB, neutral closed-shell charge/spin, and
the exact verifier protocol in the task pack. The ROY verifier performs a
submitted-geometry single point after graph identity validation. The Ritonavir
verifier optimizes the submitted geometry and rechecks graph identity and all
four stereocenters after optimization. Energies are Hartree and are never
compared across the two molecules.

| Verifier | Normalized spec SHA-256 |
| --- | --- |
| `xtb_total_energy_roy_singlepoint_gfn2_v1` | `c4cd03896b396762e0e3f016f3293311d481f3c70bc9e0b15c5d7e8d99eecdd4` |
| `xtb_total_energy_ritonavir_optimized_gfn2_v1` | `cec37a1b7a5e5e13d222fb03f47be89aec1ce25cb63c18c976f6eba6a10ed360` |

## Literature basis

1. Vasileiadis et al., *The polymorphs of ROY: application of a systematic
   crystal structure prediction technique*, Acta Cryst. B (2012), DOI
   [10.1107/S0108768112045636](https://doi.org/10.1107/S0108768112045636),
   reports that conformations occurring in ROY polymorphs have energy
   differences comparable to lattice-energy differences. Yu, *Polymorphism in
   molecular solids: an extraordinary system of red, orange, and yellow
   crystals*, DOI [10.1021/ar100040r](https://doi.org/10.1021/ar100040r),
   documents the relative free energies of ROY polymorphs. These sources support
   using same-graph torsional conformers as the ROY target and failure-side
   references.
2. Chemburkar et al., *Dealing with the impact of ritonavir polymorphs on the
   late stages of bulk drug process development*, DOI
   [10.1021/op000023y](https://doi.org/10.1021/op000023y), establishes the
   Form I/Form II polymorph problem. Wang et al., *Molecular, Solid-State and
   Surface Structures of the Conformational Polymorphic Forms of Ritonavir in
   Relation to their Physicochemical Properties*, DOI
   [10.1007/s11095-021-03048-2](https://doi.org/10.1007/s11095-021-03048-2),
   explicitly attributes part of the Form II energy difference to conformational
   deformation. Chakraborty and Sengupta, *Conformational energy landscape of
   the ritonavir molecule*, DOI
   [10.1021/acs.jpcb.5b12272](https://doi.org/10.1021/acs.jpcb.5b12272),
   supports a multi-conformer energy landscape for the same molecular graph.

The papers identify the scientific reference family and the existence of
distinct conformational energy levels. The numeric anchors below are the
recomputed values of deterministic conformers under the benchmark protocol,
not literature energies copied across methods.

## Recomputed conformer panels

### ROY (single point)

Reference SMILES:
`Cc1cc(c(s1)Nc2ccccc2[N+](=O)[O-])C#N`

The conformer panel used RDKit 2026.3.2 ETKDG with `useRandomCoords=True`,
MMFF pre-optimization, and deterministic seeds. All entries passed the exact
ROY graph identity gate and the same neutral GFN2-xTB single point.

| Role | Generator seed | Total energy |
| --- | ---: | ---: |
| full-score target `T` | 16 | `-50.289109041949 Eh` |
| ordered intermediate | 27 | `-50.289107265914 Eh` |
| zero-score anchor `B` | 3 | `-50.287905192962 Eh` |

The resulting width is `0.001203848987 Eh` (about `3.16 kJ/mol`), consistent
with the literature's statement that intramolecular conformational energy
differences are material to ROY polymorph selection.

### Ritonavir (optimized)

Reference isomeric SMILES:
`CC(C)C1=NC(=CS1)CN(C)C(=O)N[C@@H](C(C)C)C(=O)N[C@@H](CC2=CC=CC=C2)C[C@@H]([C@H](CC3=CC=CC=C3)NC(=O)OCC4=CN=CS4)O`

The conformers used RDKit 2026.3.2 ETKDG with deterministic seeds and the
formal MMFF pre-optimization path. Every entry retained graph identity and all four specified
stereocenters before and after GFN2-xTB optimization.

| Role | Generator seed | Optimized total energy |
| --- | ---: | ---: |
| full-score target `T` | 13 | `-148.192718517112 Eh` |
| ordered intermediate | 7 | `-148.192161931412 Eh` |
| zero-score anchor `B` | 19 | `-148.183476873812 Eh` |

The resulting width is `0.009241643300 Eh` (about `24.3 kJ/mol`). It is a
same-molecule conformational failure-side span, not a cross-molecule energy
scale and not an experimental polymorph lattice energy.

## Approved profile values

| Profile | `T` | `B` | Unit |
| --- | ---: | ---: | --- |
| `xtb_total_energy_minimize_neg_50p3_neg_50p25_v2` | `-50.289109041949` | `-50.287905192962` | Hartree |
| `xtb_total_energy_minimize_neg_148p2_neg_148p15_v2` | `-148.192718517112` | `-148.183476873812` | Hartree |

## Approval record

- reviewer: `benchmark_maintainers`
- review date: `2026-07-21`
- review status: `approved`
- evidence id: `xtb-total-energy-dossier-2026-07-21`
- anchors are same-molecule, same charge/spin, same method, same calculation
  mode, and same identity policy as their corresponding verifier.
