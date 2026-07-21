# xTB Advanced-Property Linear-Goal Dossier

**Date:** 2026-07-21  
**Decision:** Approved for the second parameter batch  
**Scoring version:** `linear_goal_v2`

## Scope and protocol

This dossier covers tasks 008-016. Literature establishes the scientific
direction and reference chemistry. Every numeric anchor is a fresh or retained
verified value from the frozen benchmark protocol; no experimental, DFT, or
legacy-bound number is copied into a scoring profile.

Common protocol: xTB 6.7.1, explicit hydrogens, the charge and UHF state in the
formal verifier spec, and optimized-geometry properties. Deterministic SMILES
references use RDKit 2026.3.2, ETKDG seed `7`, MMFF pre-optimization, and then
the formal verifier. The task-014 conformer panel uses the existing generator's
UFF path because MMFF does not parameterize the aminyl radical. Task 015/016
XYZ comments use `charge=0`.

| Verifier | Normalized spec SHA-256 |
| --- | --- |
| `xtb_lumo_gfn2_v1` | `a4e6463fd7e2cec8e0ff1631cae7b6b19b5b6ee8c2180f2827558791907c9baa` |
| `xtb_polarizability_gfn2_v1` | `95bb9050d7a8a5576e6b1b8791e541718dadfedcbaa00d008bbaf0e5b926b635` |
| `xtb_solvation_selectivity_alpb_v1` | `7ec20b71278dee47cc70b08de5ae84d2ef15d3de9034fa9ac5c333973e131dc3` |
| `xtb_electrophilicity_gfn1_ipea_v1` | `07a88cc77f005e1f6ab667f6a15f65838297c2922c3cb865ed477dcfc0692d6b` |
| `xtb_fukui_gfn1_v1` | `eb35579b740773567a5e0bb10dc319f07496131397d310aab926253b2a42dd4b` |
| `xtb_hessian_thermo_gfn2_v1` | `dc0093dbf99ff108fcd5ad73628d66cbfa59ec8d1bbb441c357d97117fee9738` |
| `xtb_dipole_doublet_gfn2_v1` | `4af663a72edd69532a58cc22aeb67698f4f6ad1fb31b2415392b072494ff75c1` |
| `xtb_gap_charged_closed_shell_gfn2_v1` | `6af613b763c15e7530e268d9f267a5dc72308dd614e40c737ded129bb26f3d80` |

## Literature basis

1. TCNE is described as highly electron-deficient and strongly electrophilic
   by Fatiadi, *Synthesis* (1987), DOI
   [10.1055/s-1987-28074](https://doi.org/10.1055/s-1987-28074). The review by
   Kivala and Diederich, DOI
   [10.1021/ar8001238](https://doi.org/10.1021/ar8001238), likewise treats
   TCNE-derived systems as strong organic acceptors. These sources support TCNE
   as the low-LUMO and high-electrophilicity target reference.
2. Andrews and Boxer explicitly study nitriles, including 1,3-dicyanobenzene,
   and their molecular polarizability response in DOI
   [10.1021/jp002242r](https://doi.org/10.1021/jp002242r). This supports the
   aromatic dinitrile as the high-polarizability reference within the required
   3-8 D dipole window.
3. Lopes Jesus et al. study erythritol hydration and solute-solvent interaction
   in DOI [10.1021/jp0561221](https://doi.org/10.1021/jp0561221). Garrido et al.
   connect solvation free energies to water/n-hexane partitioning in DOI
   [10.1039/C1CP20110G](https://doi.org/10.1039/C1CP20110G). These sources
   support polyols as water-selective references and aliphatic esters as the
   weak/non-water-selective side.
4. Propiolamide-class electrophiles are identified as reactive covalent
   warheads by Jackson et al., DOI
   [10.1021/acs.jmedchem.6b00788](https://doi.org/10.1021/acs.jmedchem.6b00788).
   Karaj et al. use Fukui functions to confirm and tune electrophilic sites,
   DOI [10.1021/acs.jmedchem.2c00909](https://doi.org/10.1021/acs.jmedchem.2c00909).
   These support propiolamide as the high carbon-site `f+` reference. A contrast
   of zero has direct semantics: the best carbon ties the best non-carbon
   competitor and therefore has no carbon-site advantage.
5. DeTar's gas-phase ether/alcohol thermochemistry study, DOI
   [10.1021/jp990705r](https://doi.org/10.1021/jp990705r), supports the selected
   small ether/alcohol reference family. Literature numbers are not divided by
   heavy-atom count; the benchmark-specific normalized anchors are recomputed.
6. Gryn'ova et al. discuss aminyl radicals, orbital conversion, and calculated
   dipole moments in DOI
   [10.1021/ja404279f](https://doi.org/10.1021/ja404279f). Because task 014 fixes
   one unpublished benchmark aminyl formula, its deterministic conformer panel
   is declared as the frozen benchmark baseline rather than pretending that a
   different literature radical has the same dipole scale.
7. Frontier-orbital effects in benzoquinones and naphthoquinones are established
   by Rozeboom et al., DOI
   [10.1021/jo00324a026](https://doi.org/10.1021/jo00324a026). This supports the
   difluoronaphthoquinone low-gap target; the saturated difluorodecane is the
   wide-gap failure-side reference. Both references satisfy the stricter
   `C10F2`, neutral, closed-shell domain shared by tasks 015 and 016.

## Frozen anchors and controls

| Profile property | `T` reference and value | Ordered intermediate | `B` reference and value |
| --- | --- | --- | --- |
| LUMO minimize | TCNE, `N#CC(=C(C#N)C#N)C#N`: `-10.6883 eV` | m-dicyanobenzene: `-8.2191 eV` | tetrafluoro ether/alcohol, `CC(F)(F)C(F)(F)OCCO`: `-1.9400 eV` |
| polarizability/heavy atom maximize | m-dicyanobenzene: `9.3430346 au/HA`, dipole `3.975 D` | nitrobenzene: `9.085865444444444 au/HA`, dipole `5.499 D` | tetrafluorobutanediol, `OCC(F)(F)C(F)(F)CO`: `6.4845643 au/HA`, dipole `6.048 D` |
| ALPB water-hexane selectivity maximize | tetrafluorobutanediol: `0.3953163242456749 eV` | dimethylamino nitrobenzene: `0.23772563040053657 eV` | ethyl hexanoate, `CCCCCC(=O)OCC`: `-0.17228322475548233 eV` |
| global electrophilicity maximize | TCNE: `3.1359 eV` | m-dicyanobenzene: `1.8537 eV` | tetrafluoro ether/alcohol: `0.4862 eV` |
| max carbon `f+` maximize | propiolamide, `C#CC(N)=O`: `0.276` | methyl acrylate, `COC(=O)C=C`: `0.225` | dimethylamino nitrobenzene: `0.076` |
| carbon `f+` contrast maximize | propiolamide: `0.094` | methyl acrylate: `0.063` | carbon/non-carbon tie boundary: `0.0` |
| entropy 298/heavy atom maximize | methoxyethane, QM9 `gdb9_000041`: `76.094775 J mol-1 K-1/HA` | stable QM9 `gdb9_000035`: `74.1745 J mol-1 K-1/HA` | hexafluoroisopropanol: `40.59789 J mol-1 K-1/HA` |
| fixed-formula dipole minimize | aminyl UFF/ETKDG seed 2: `3.042 D` | seed 4: `5.031 D` | seed 8: `9.328 D` |
| `C10F2` gap minimize | difluoronaphthoquinone, `O=C1C(F)=CC2=CC=CC(F)=C2C1=O`: `1.242666887976 eV` | formal task-015 difluorobenzoquinone: `1.708148523301 eV` | 1,10-difluorodecane, `FCCCCCCCCCCF`: `12.358052453139 eV` |

The expanded property distributions are retained only as feasibility checks.
They did not define any endpoint. Task 014's panel is an explicit frozen
benchmark baseline generated before participant evaluation; it is not a
participant or leaderboard distribution.

## Approved profile values

| Profile | `T` | `B` |
| --- | ---: | ---: |
| `xtb_lumo_energy_minimize_neg_9p0_neg_6p0_v2` | `-10.6883` | `-1.94` |
| `xtb_polarizability_per_heavy_atom_maximize_4p0_12p0_v2` | `9.3430346` | `6.4845643` |
| `xtb_alpb_water_hexane_selectivity_maximize_0p0_0p35_v2` | `0.3953163242456749` | `-0.17228322475548233` |
| `xtb_global_electrophilicity_maximize_0p5_3p8_v2` | `3.1359` | `0.4862` |
| `xtb_max_f_plus_on_carbon_maximize_0p05_0p35_v2` | `0.276` | `0.076` |
| `xtb_f_plus_contrast_maximize_0p0_0p15_v2` | `0.094` | `0.0` |
| `xtb_entropy_298_per_heavy_atom_maximize_50p0_80p0_v2` | `76.094775` | `40.59789` |
| `xtb_dipole_moment_minimize_0p0_20p0_v2` | `3.042` | `9.328` |
| `xtb_homo_lumo_gap_minimize_0p0_10p0_v2` | `1.242666887976` | `12.358052453139` |

## Approval record

- reviewer: `benchmark_maintainers`
- review date: `2026-07-21`
- review status: `approved`
- evidence id: `xtb-advanced-property-dossier-2026-07-21`
- no legacy bound, participant output, or leaderboard outcome was used as an
  endpoint.
