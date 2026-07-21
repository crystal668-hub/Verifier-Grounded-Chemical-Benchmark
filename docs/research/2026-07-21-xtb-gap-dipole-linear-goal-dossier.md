# xTB Gap and Dipole Linear-Goal Dossier

**Date:** 2026-07-21  
**Decision:** Approved for the first gap/dipole parameter batch  
**Scoring version:** `linear_goal_v2`

## Frozen protocol

All reference values below were recomputed with the formal xTB verifier
protocol rather than copied from a paper:

- xTB 6.7.1, GFN2-xTB, neutral closed shell (`charge=0`, `uhf=0`);
- RDKit 2026.3.2, explicit hydrogens, ETKDG embedding with seed `7`, MMFF
  pre-optimization;
- verifier calculation: `xtb candidate.xyz --gfn 2 --chrg 0 --uhf 0 --opt`;
- reported property: the optimized-geometry xTB HOMO-LUMO gap or total dipole;
- values are in eV for gap and Debye for dipole.

The reference SMILES are only reproducibility handles. The scoring anchors are
the recomputed verifier values, not the literature values. Each structure meets
the corresponding task domain (heavy-atom count, heteroatom count, and element
restrictions).

## Literature basis

1. Bassi et al., *Transparent perfluoropolyethers for vacuum ultraviolet
   applications*, J. Phys. Chem. B (2006), DOI
   [10.1021/jp060205f](https://doi.org/10.1021/jp060205f). The paper relates
   perfluoroalkane/perfluoroether composition to the HOMO-LUMO energy gap and
   treats these materials as wide-gap VUV-transparent references. This supports
   the wide-gap reference direction.
2. Brinkmann and Rienstra-Kiracofe, *Electron affinities of cyano-substituted
   ethylenes*, Mol. Phys. (2001), DOI
   [10.1080/00268970010028818](https://doi.org/10.1080/00268970010028818).
   The reported cyano substitution trend lowers the ethylene HOMO-LUMO gap;
   this supports cyano/acceptor-rich molecules as the failure-side reference
   for a gap-maximize task.
3. Moonen et al., *Donor-Substituted Cyanoethynylethenes: pi-Conjugation and
   Band-Gap Tuning in Strong Charge-Transfer Chromophores*, Chem. Eur. J.
   (2005), DOI [10.1002/chem.200500082](https://doi.org/10.1002/chem.200500082).
   The paper explicitly describes very small HOMO-LUMO gaps in donor-acceptor
   chromophores, supporting the low-gap target direction.
4. Budzinauskas et al., *Impact of the Interfacial Molecular Structure
   Organization on the Charge Transfer State Formation and Exciton
   Delocalization in Merocyanine:PC61BM Blends*, J. Phys. Chem. C (2020), DOI
   [10.1021/acs.jpcc.0c06296](https://doi.org/10.1021/acs.jpcc.0c06296).
   Ground-state merocyanine dipoles of about 15.5--15.8 D are reported. This
   supports a high-dipole push-pull reference above the legacy 8--10 D bounds.
   Wudarczyk et al., DOI [10.1002/anie.201508249](https://doi.org/10.1002/anie.201508249),
   independently reports organic molecules exceeding 10 D.

These sources establish the scientific ordering and the level of an excellent
reference. They do not supply numeric GFN2-xTB anchors.

## Recomputed controls and anchors

| Role | Reference SMILES | Property | Recomputed value |
| --- | --- | --- | ---: |
| wide-gap target / dipole intermediate | `CC(F)(F)C(F)(F)OCCO` | gap | `9.749630028571 eV` |
| gap-max intermediate | `CC(F)(F)C(F)(F)OCCN` | gap | `8.534879201635 eV` |
| low-gap target / gap-max zero anchor / dipole target | `O=[N+]([O-])c1ccc(/C=C/c2ccc(N(C)C)cc2)cc1` | gap | `1.389963462368 eV` |
| low-gap intermediate | `O=C1C(F)=CC(=O)C1F` | gap | `2.086498689903 eV` |
| dipole zero anchor | `CC(=O)Oc1ccc(F)cc1` | dipole | `3.320 D` |
| dipole intermediate | `O=[N+]([O-])c1ccccc1` | dipole | `5.499 D` |
| dipole target | `O=[N+]([O-])c1ccc(/C=C/c2ccc(N(C)C)cc2)cc1` | dipole | `13.374 D` |

The gap-max profile therefore uses `T=9.749630028571 eV` and
`B=1.389963462368 eV`. The gap-min profile uses `T=1.389963462368 eV` and
`B=9.749630028571 eV`. The shared dipole-max profile uses `T=13.374 D` and
`B=3.320 D`. The ordered controls are strictly between the relevant anchors.

## Approval record

- reviewer: `benchmark_maintainers`
- review date: `2026-07-21`
- review status: `approved`
- evidence id: `xtb-gap-dipole-dossier-2026-07-21`
- provenance: same verifier, method, charge/spin, units, and hard domains as
  the formal task pack; no participant outputs or leaderboard distributions
  were used to set the anchors.
