# Verifier Grounded Benchmark - Registered Tasks

**Version:** 0.10.0 source, post-retirement (2026-10-28)\
**Last Updated:** 2026-10-28

## Summary

The benchmark currently has **4 formal tracks** with a total of **100 registered tasks**.

| Track | Version | Tasks | Type | Tags |
|-------|---------|-------|------|------|
| open_generation_rdkit | 0.10.0 | 10 | Verifier-based | small_molecule, rdkit, descriptor |
| open_generation_xtb | 0.10.0 | 20 | Verifier-based | small_molecule_3d, xtb, xyz, smiles |
| property_calculation_basic | 0.10.0 | 51 | Gold-based | property_calculation, fixed_input, basic, small_molecule |
| property_calculation_advanced | 0.10.0 | 19 | Gold-based | property_calculation, fixed_input, crystal |

---

## Track 1: open_generation_rdkit

**Type:** Open generation (verifier-based)  
**Object Type:** Small molecule (SMILES)  
**Requirements:** RDKit  
**Task Count:** 10

### Task List

1. **rdkit_001_qed_max** (v1) - basic\
   Maximize QED on a bounded 0.0 to 1.0 scale

2. **rdkit_002_logp_window** (v1) - basic\
   Have logP between 1.0 and 3.0

3. **rdkit_003_tpsa_window** (v1) - basic\
   Have TPSA between 35.0 and 75.0 square angstroms

4. **rdkit_004_qed_sa** (v1) - basic [multi_objective]\
   Maximize QED and minimize synthetic accessibility score

5. **rdkit_005_logp_tpsa** (v1) - basic [multi_objective]\
   Have logP between 1.0-3.0 and TPSA between 35.0-75.0

6. **rdkit_006_hba_hbd** (v1) - basic [multi_objective]\
    Have HBA between 2.0-4.0 and HBD between 1.0-2.0

7. **rdkit_007_logp_target** (v1) - advanced [formal_track]\
    Make logP as close as possible to 3.0 with constraints

8. **rdkit_008_sa_logp_target** (v1) - advanced [formal_track]\
    SA < 5.0, optimize logP to 3.0

9. **rdkit_009_chain_end_to_end_max** (v2) - advanced [formal_track]\
    Maximize end-to-end distance in six-carbon chain using UFF

10. **rdkit_010_caffeine_similarity_max** (v1) - advanced [formal_track]\
    Maximize similarity to caffeine with property constraints

---

## Track 2: open_generation_xtb

**Type:** Open generation (verifier-based)  
**Object Type:** Small molecule 3D (XYZ)  
**Requirements:** xTB executable; CREST 2.12 for conformer-search tasks  
**Task Count:** 20

### Task List

1. **xtb_001_gap_window** (v2) - basic [formal_track]\
   HOMO-LUMO gap between 3.5 and 5.5 eV

2. **xtb_002_dipole_window** (v2) - basic [formal_track]\
   Molecular dipole moment between 3.0 and 5.5 Debye

3. **xtb_003_gap_max** (v2) - basic [formal_track]\
   Maximize HOMO-LUMO gap

4. **xtb_004_gap_min** (v2) - basic [formal_track]\
   Minimize HOMO-LUMO gap

5. **xtb_005_dipole_max** (v2) - basic [formal_track]\
   Maximize molecular dipole moment

6. **xtb_006_low_gap_high_dipole_opt** (v2) - basic [formal_track, multi_objective]\
   Minimize gap and maximize dipole

7. **xtb_007_gap_dipole_window** (v2) - basic [formal_track, multi_objective]\
   Gap between 2.5-4.2 eV and dipole between 3.5-6.0 Debye

8. **xtb_008_lumo_min** (v1) - basic [formal_track]\
   Minimize LUMO energy

9. **xtb_009_polarizability_dipole_opt** (v1) - basic [formal_track, multi_objective]\
   Maximize polarizability per heavy atom with dipole constraint

10. **xtb_010_solvation_selectivity_alpb** (v1) - basic [formal_track]\
    Maximize water-over-hexane solvation selectivity

11. **xtb_011_electrophilicity_max** (v1) - basic [formal_track]\
    Maximize global electrophilicity index

12. **xtb_012_fukui_carbon_site** (v1) - basic [formal_track]\
    Maximize strongest carbon-atom f+ local reactivity

13. **xtb_013_hessian_thermo_stability** (v2) - basic [formal_track]\
    Stable minimum with maximum 298.15 K entropy per heavy atom

14. **xtb_014_formula_dipole_min** (v1) - advanced [formal_track]\
    C12H16N3O8 neutral doublet, minimize dipole

15. **xtb_015_two_fluorine_gap_min** (v1) - advanced [formal_track]\
    Exactly 2 F atoms, ≤10 C atoms, minimize gap

16. **xtb_016_c10_f2_gap_min** (v1) - advanced [formal_track]\
    Exactly 10 C and 2 F atoms, minimize gap

17. **xtb_017_roy_singlepoint_energy_min** (v1) - advanced [formal_track]\
    ROY molecule conformer, minimize single-point energy

18. **xtb_018_ritonavir_optimized_energy_min** (v1) - advanced [formal_track]\
    Ritonavir conformer with stereochemistry, minimize optimized energy

19. **xtb_019_odd_element_counts_gap_max** (v1) - advanced [formal_track]\
    All non-H elements odd count, dipole < 2.0, maximize gap

20. **xtb_020_pyrene_substituent_energy_min** (v1) - advanced [formal_track]\
    Pyrene with NO2, NH2, COOH substituents, minimize conformer energy

---

## Track 3: property_calculation_basic

**Type:** Property calculation (gold-based)  
**Object Type:** Various (molecules, complexes, surfaces)  
**Requirements:** Various computational chemistry tools  
**Task Count:** 51

### Task Categories

#### Solvation (4 tasks)
- property_calculation_basic_001_toluene_aqueous_solvation_free_energy
- property_calculation_basic_002_ethanol_aqueous_solvation_free_energy
- property_calculation_basic_003_diethyl_ether_aqueous_solvation_free_energy
- property_calculation_basic_004_anisole_aqueous_solvation_free_energy

#### Redox (5 tasks)
- property_calculation_basic_005_nitrobenzene_reduction_potential
- property_calculation_basic_006_tetracyanoethylene_reduction_potential
- property_calculation_basic_007_dimethylaniline_oxidation_potential
- property_calculation_basic_008_triphenylamine_oxidation_potential
- property_calculation_basic_009_thianthrene_oxidation_potential

#### Noncovalent Interactions (6 tasks)
- property_calculation_basic_010_water_dimer_binding_energy
- property_calculation_basic_011_ammonia_dimer_binding_energy
- property_calculation_basic_012_benzene_t_dimer_binding_energy
- property_calculation_basic_013_adenine_thymine_wc_pair_binding_energy
- property_calculation_basic_014_water_methanol_complex_binding_energy
- property_calculation_basic_015_ethene_ethyne_t_complex_binding_energy

#### Electronic Properties (11 tasks)
- property_calculation_basic_016_thiophene_polarizability
- property_calculation_basic_017_benzene_polarizability
- property_calculation_basic_018_octatetraene_polarizability
- property_calculation_basic_019_dimethyl_sulfoxide_water_dipole_moment
- property_calculation_basic_020_cis_dichloroethene_dipole_moment
- property_calculation_basic_021_acetonitrile_dipole_moment
- property_calculation_basic_022_naphthalene_bridge_bond_order
- property_calculation_basic_023_dimethyl_sulfone_so_bond_order
- property_calculation_basic_024_methyl_nitrate_no_bond_order
- property_calculation_basic_025_phenol_surface_esp_minimum
- property_calculation_basic_027_pyrrole_surface_esp_variance

#### Surface Properties (2 tasks)
- property_calculation_basic_026_nitrobenzene_vdw_surface_area
- (see also ESP tasks above)

#### Crystal Properties (3 tasks)
- property_calculation_basic_028_urea_crystal_density
- property_calculation_basic_029_tnt_crystal_density
- property_calculation_basic_030_picric_acid_crystal_density

#### Atomic Properties (9 tasks)
- property_calculation_basic_031_allyl_radical_c1_spin_density
- property_calculation_basic_032_benzyl_radical_para_c_spin_density
- property_calculation_basic_033_phenoxy_radical_o_spin_density
- property_calculation_basic_034_indole_c3_fukui_minus
- property_calculation_basic_035_chloronitrobenzene_c_fukui_plus
- property_calculation_basic_036_furfural_carbonyl_c_fukui_plus
- property_calculation_basic_044_caffeine_most_negative_mulliken_atom
- property_calculation_basic_045_trifluoroacetic_acid_hydrogen_charge
- property_calculation_basic_046_methyl_azide_most_negative_mulliken_atom

#### Thermochemistry (7 tasks)
- property_calculation_basic_037_benzene_standard_entropy
- property_calculation_basic_038_acetonitrile_standard_entropy
- property_calculation_basic_039_neopentane_standard_entropy
- property_calculation_basic_040_methane_standard_entropy
- property_calculation_basic_041_ammonia_standard_entropy
- property_calculation_basic_042_carbon_dioxide_standard_entropy
- property_calculation_basic_043_acetic_acid_dimerization_enthalpy

#### Excited States (5 tasks)
- property_calculation_basic_047_formaldehyde_s1_vertical_excitation_energy
- property_calculation_basic_048_acetaldehyde_s1_vertical_excitation_energy
- property_calculation_basic_049_acetone_s1_vertical_excitation_energy
- property_calculation_basic_050_pyrazine_s1_vertical_excitation_energy
- property_calculation_basic_051_formaldehyde_t1_vertical_excitation_energy

---

## Track 4: property_calculation_advanced

**Type:** Property calculation (gold-based)  
**Object Type:** Molecular crystals and advanced properties  
**Requirements:** Advanced computational chemistry tools (DFT, TDDFT)  
**Task Count:** 19

### Task List

1. **property_calculation_advanced_001_free_energy**\
   Crystal pair free energy difference at 300 K

2. **property_calculation_advanced_002_crystal_phase**\
   Determine stable crystal phase

3. **property_calculation_advanced_003_hbond_count**\
   Count hydrogen bonds in crystal structure

4. **property_calculation_advanced_004_crystal_density**\
   Calculate crystal density

5. **property_calculation_advanced_005_cocrystal_ratio**\
   Determine co-crystal stoichiometric ratio

6. **property_calculation_advanced_006_polymorph_free_energy_crossover**\
   Temperature of polymorph crossover

7. **property_calculation_advanced_007_interaction_binding_energy**\
   Intermolecular binding energy in crystal

8. **property_calculation_advanced_008_homo_lumo_gap**\
   HOMO-LUMO gap of crystal

9. **property_calculation_advanced_009_hbond_distances**\
    Hydrogen bond distances

10. **property_calculation_advanced_010_accessible_pore_volume_ratio**\
    Pore volume ratio in MOF/COF

11. **property_calculation_advanced_011_carboxyl_hydrogen_distance**\
    Specific H-bond distance

12. **property_calculation_advanced_012_halogen_bond_energy**\
    Halogen bond interaction energy

13. **property_calculation_advanced_013_bay069_pka**\
    pKa calculation for BAY069

14. **property_calculation_advanced_014_formaldehyde_socme**\
    Spin-orbit coupling matrix element

15. **property_calculation_advanced_015_anthracene_isc_rate**\
    Intersystem crossing rate

16. **property_calculation_advanced_016_biacetyl_phosphorescence_rate**\
    Phosphorescence rate constant

17. **property_calculation_advanced_017_anthracene_ht_contribution**\
    Heavy-atom contribution to ISC

18. **property_calculation_advanced_018_acetophenone_isc_rate**\
    ISC rate for acetophenone

19. **property_calculation_advanced_019_azulene_internal_conversion_rate**\
    Internal conversion rate

---

## Notes

- All tracks are at version 0.10.0
- Tasks marked `[formal_track]` are designated as official benchmark tasks
- Difficulty levels: basic, advanced; see [the standard](design/task-difficulty-levels.md).
- All tasks include detailed prompts, answer schemas, and validation criteria
- Verifier-based tracks use computational verification
- Gold-based tracks use reference answer comparison
