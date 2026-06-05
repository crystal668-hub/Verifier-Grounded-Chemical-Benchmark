# xTB Direct XYZ Verifier Design

## Context

The next verifier track should ask models to output a molecule directly as an
XYZ geometry, then score that geometry with a local xTB-backed verifier. This is
different from the existing RDKit small-molecule track, where models output
SMILES and the verifier computes 2D descriptors. It is also different from the
MatGL and MACE material tracks, where models output periodic CIF structures.

The direct XYZ track is intended to evaluate whether a model can propose a
chemically plausible three-dimensional molecular geometry that is suitable for
quantum-chemistry evaluation. The verifier should not silently generate a 3D
conformer from a SMILES string, because that would move the core geometry
generation work from the model into the verifier.

## Evidence For Direct XYZ Tasks

The design is grounded in existing tools, datasets, and inverse-design studies:

- xTB officially supports XYZ molecular geometry input. Its property printout
  includes orbital energies, HOMO-LUMO gap, total energy, and molecular dipole
  moment; the command-line interface exposes geometry optimization as a standard
  run type.
- QM9 stores 133,885 small organic molecules with computed quantum-chemical
  properties in XYZ-like files, including dipole moment and HOMO/LUMO-related
  properties.
- GEOM contains 37 million energy-annotated conformations for more than 450,000
  molecules, showing that 3D conformer data is a standard object for molecular
  property prediction and generation.
- Language-model work has shown that models can generate molecules, materials,
  and protein binding sites directly from file-format sequences such as XYZ,
  CIF, and PDB.
- Tartarus uses Open Babel, CREST, and GFN2-xTB to compute OPV design
  objectives from optimized structures, including HOMO-LUMO gap and molecular
  dipole moment. Its OPV dataset contains 24,953 SMILES with objectives such as
  dipole moment maximization, HOMO-LUMO gap maximization, LUMO minimization, and
  combined objectives.
- HOMO-LUMO gap maximization and minimization are real inverse-design targets:
  a diamondoid inverse-design study found adamantane derivatives with gaps from
  2.42 to 10.63 eV, compared with 9.45 eV for unsubstituted adamantane.
- Dipole moment maximization has materials-design value. A genetic-algorithm
  study searched conjugated hexamers with simultaneously large polarizability
  and dipole moment for potential organic dielectric materials using approximate
  density-functional tight-binding calculations.

Reference sources:

- xTB geometry input: https://xtb-docs.readthedocs.io/en/latest/geometry.html
- xTB properties: https://xtb-docs.readthedocs.io/en/latest/properties.html
- xTB command-line run types: https://xtb-docs.readthedocs.io/en/latest/commandline.html
- QM9 dataset descriptor: https://www.nature.com/articles/sdata201422
- GEOM dataset descriptor: https://pmc.ncbi.nlm.nih.gov/articles/PMC9023519/
- Direct 3D language-model generation: https://arxiv.org/abs/2305.05708
- Tartarus tasks: https://tartarus.readthedocs.io/en/latest/tasks.html
- Diamondoid HOMO-LUMO gap inverse design: https://pubs.acs.org/doi/10.1021/acs.jctc.6b01074
- Dipole/polarizability GA optimization: https://pubs.acs.org/doi/10.1021/acs.jpca.2c01266

## Scope

This track should be a formal small-molecule 3D track:

```yaml
object_type: small_molecule_3d
formal_track: true
capability_tags:
  - open_generation
  - property_satisfaction
  - three_dimensional_geometry
  - xyz
  - xtb
  - quantum_chemistry
```

The first implementation should stay conservative:

- Use molecular XYZ only, not SDF, CIF, PDB, or periodic structures.
- Use neutral closed-shell molecules only: charge 0, singlet multiplicity.
- Use GFN2-xTB as the fixed xTB method.
- Use optimized geometries for HOMO-LUMO gap and dipole-moment scoring.
- Compute relaxation energy as the input single-point energy minus optimized
  energy.
- Keep vibrational frequencies, ionization potentials, electron affinities,
  partial charges, solvation, and reaction-path tasks out of the first batch.

## Candidate Domain

The model-facing prompt and verifier domain must align. The first batch should
use the following hard candidate domain:

```yaml
domain:
  format: xyz
  charge: 0
  multiplicity: 1
  allowed_elements: [H, C, N, O, F, P, S, Cl, Br]
  atom_count: [3, 80]
  heavy_atom_count: [1, 40]
  coordinate_units: angstrom
  max_absolute_coordinate: 30.0
  min_interatomic_distance: 0.45
  inferred_components: 1
  require_explicit_hydrogens: true
```

The `inferred_components` gate should build a simple covalent-radius graph from
the XYZ coordinates and reject disconnected geometries. This graph is only a
validity gate; xTB remains the source of the scored quantum-chemical
properties.

The direct XYZ track should not try to infer molecular charge, spin, or bond
orders from the final answer. Those extensions should be introduced later with
explicit answer-schema fields.

## Answer Schema

Tasks should use a fenced final-answer block:

````yaml
answer_schema: &xyz_answer_schema
  format: final_answer_block
  final_answer_prefix: "FINAL ANSWER:"
  value_type: xyz
  fence_language: xyz
  cardinality: one
  example: |
    FINAL ANSWER:
    ```xyz
    3
    water
    O 0.000000 0.000000 0.000000
    H 0.758602 0.000000 0.504284
    H -0.758602 0.000000 0.504284
    ```
````

The extractor should return the existing verifier-ready shape:

```python
{
    "task_id": task_id,
    "candidates": [{"xyz": extracted_xyz}],
    "raw_answer": original_response,
    "extracted_answer": extracted_xyz,
}
```

The first line of the XYZ content must be the atom count, the second line is a
free comment line, and all remaining lines must be element symbols followed by
three finite decimal coordinates in Angstrom.

## Verifier Architecture

Use the existing constraint-level routing boundary:

```text
task constraint/property -> verifier_id -> verification_script -> shared backend/tool environment
```

Do not create task-level verifier scripts. Each xTB property should have one
property-level script that calls a shared backend:

```text
verifiers/xtb/xtb_gap.py
verifiers/xtb/xtb_dipole.py
verifiers/xtb/xtb_relaxation_energy.py
verifiers/backends/xtb_properties.py
```

The backend should own:

- XYZ parsing and domain checks.
- Temporary working directories.
- xTB command construction.
- Single-point and optimization runs.
- Property parsing from xTB output.
- Failure mapping into benchmark result rows.
- Version metadata for xTB and the parser.

The verifier scripts should only check that the script property matches
`verifier_spec.property_name`, then call the shared backend.

## Verifier Specs

The first batch should define three verifier specs:

```yaml
verifiers:
  - verifier_id: xtb_gap_gfn2_v1
    name: xTB GFN2 HOMO-LUMO Gap Verifier
    version: 1
    formal_track: true
    verifier_image: verifier-grounded:dev
    verification_script: verifiers/xtb/xtb_gap.py
    timeout_seconds: 240
    property_name: homo_lumo_gap
    resources: &xtb_resources
      cpu: 2
      memory_mb: 2048
    backend: &xtb_backend
      type: local_xtb
      executable: xtb
      method: GFN2-xTB
      charge: 0
      uhf: 0
      optimize_before_property: true
    package_versions: &xtb_package_versions
      xtb: external
      rdkit: "2026.3.2"
    domain: &xtb_xyz_domain
      format: xyz
      charge: 0
      multiplicity: 1
      allowed_elements: [H, C, N, O, F, P, S, Cl, Br]
      atom_count: [3, 80]
      heavy_atom_count: [1, 40]
      coordinate_units: angstrom
      max_absolute_coordinate: 30.0
      min_interatomic_distance: 0.45
      inferred_components: 1
      require_explicit_hydrogens: true
    property:
      source: xTB GFN2-xTB optimized geometry property printout
      units: eV
      notes: HOMO-LUMO orbital-energy gap from fixed xTB output, not an experimental optical gap.
    scoring: &xtb_scoring
      supported_modes:
        - window
        - maximize_bounded
        - minimize_bounded
      bounded_modes:
        good_at_or_baseline: forbidden
      final_score_range: [0.0, 1.0]
    failure_policy: &xtb_failure_policy
      parse_error: missing fenced XYZ block or unparseable XYZ content
      validity_error: atom overlap, disconnected geometry, or invalid coordinate values
      domain_error: outside element, atom-count, charge, spin, or coordinate domain
      verifier_environment_error: xTB executable missing or unusable
      verifier_tool_error: xTB calculation failed, optimization did not converge, or output property was missing
      verifier_timeout: xTB calculation exceeded timeout

  - verifier_id: xtb_dipole_gfn2_v1
    name: xTB GFN2 Dipole Moment Verifier
    version: 1
    formal_track: true
    verifier_image: verifier-grounded:dev
    verification_script: verifiers/xtb/xtb_dipole.py
    timeout_seconds: 240
    property_name: dipole_moment
    resources: *xtb_resources
    backend: *xtb_backend
    package_versions: *xtb_package_versions
    domain: *xtb_xyz_domain
    property:
      source: xTB GFN2-xTB optimized geometry molecular dipole printout
      units: debye
      notes: Total molecular dipole magnitude, orientation-independent.
    scoring: *xtb_scoring
    failure_policy: *xtb_failure_policy

  - verifier_id: xtb_relaxation_energy_gfn2_v1
    name: xTB GFN2 Relaxation Energy Verifier
    version: 1
    formal_track: true
    verifier_image: verifier-grounded:dev
    verification_script: verifiers/xtb/xtb_relaxation_energy.py
    timeout_seconds: 300
    property_name: relaxation_energy
    resources: *xtb_resources
    backend:
      <<: *xtb_backend
      input_singlepoint_before_optimization: true
      optimize_before_property: true
    package_versions: *xtb_package_versions
    domain: *xtb_xyz_domain
    property:
      source: xTB GFN2-xTB input single-point energy minus optimized total energy
      units: eV
      notes: Measures whether the submitted XYZ geometry is already close to a local minimum.
    scoring: *xtb_scoring
    failure_policy: *xtb_failure_policy
```

`relaxation_energy` should be computed as:

```text
relaxation_energy_eV = max(0.0, (E_input_singlepoint_Eh - E_optimized_Eh) * 27.211386245988)
```

The `max(0.0, ...)` clamp prevents small numerical or optimizer artifacts from
creating negative relaxation energies.

## Task Set

Use a mixed set of window and optimization tasks. Window tasks verify targeted
property satisfaction; optimization tasks verify whether a model can push a
chemically meaningful property in a useful direction.

The first batch should include these tasks:

```yaml
tasks:
  - task_id: xtb_gap_window_001
    version: 1
    object_type: small_molecule_3d
    difficulty: basic
    formal_track: true
    capability_tags: [open_generation, property_satisfaction, three_dimensional_geometry, xyz, xtb, homo_lumo_gap]
    constraints:
      - type: window
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        min: 4.0
        max: 6.0
        sigma: 0.75
    scoring:
      aggregation: geometric_mean

  - task_id: xtb_dipole_window_002
    version: 1
    object_type: small_molecule_3d
    difficulty: basic
    formal_track: true
    capability_tags: [open_generation, property_satisfaction, three_dimensional_geometry, xyz, xtb, dipole_moment]
    constraints:
      - type: window
        property: dipole_moment
        verifier_id: xtb_dipole_gfn2_v1
        min: 1.5
        max: 4.0
        sigma: 1.0
    scoring:
      aggregation: geometric_mean

  - task_id: xtb_gap_max_003
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_optimization, three_dimensional_geometry, xyz, xtb, homo_lumo_gap]
    constraints:
      - type: maximize_bounded
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        lower: 0.0
        upper: 12.0
    scoring:
      aggregation: geometric_mean

  - task_id: xtb_gap_min_004
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_optimization, three_dimensional_geometry, xyz, xtb, homo_lumo_gap]
    constraints:
      - type: minimize_bounded
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        lower: 0.0
        upper: 8.0
    scoring:
      aggregation: geometric_mean

  - task_id: xtb_dipole_max_005
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_optimization, three_dimensional_geometry, xyz, xtb, dipole_moment]
    constraints:
      - type: maximize_bounded
        property: dipole_moment
        verifier_id: xtb_dipole_gfn2_v1
        lower: 0.0
        upper: 10.0
    scoring:
      aggregation: geometric_mean

  - task_id: xtb_relaxation_energy_min_006
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, geometry_quality, property_optimization, three_dimensional_geometry, xyz, xtb, relaxation_energy]
    constraints:
      - type: minimize_bounded
        property: relaxation_energy
        verifier_id: xtb_relaxation_energy_gfn2_v1
        lower: 0.0
        upper: 2.0
    scoring:
      aggregation: geometric_mean

  - task_id: xtb_gap_dipole_window_007
    version: 1
    object_type: small_molecule_3d
    difficulty: intermediate
    formal_track: true
    capability_tags: [open_generation, property_satisfaction, multi_objective, three_dimensional_geometry, xyz, xtb, homo_lumo_gap, dipole_moment]
    constraints:
      - type: window
        property: homo_lumo_gap
        verifier_id: xtb_gap_gfn2_v1
        min: 3.0
        max: 5.0
        sigma: 0.75
      - type: window
        property: dipole_moment
        verifier_id: xtb_dipole_gfn2_v1
        min: 2.0
        max: 5.0
        sigma: 1.0
    scoring:
      aggregation: geometric_mean
```

The numeric windows and bounded ranges are intentionally broad seed targets.
During implementation, calibrate them with a small fixed set of sample XYZ
answers so at least one simple sample scores successfully and obviously bad
geometries fail deterministically.

## Prompt Template

Each xTB-XYZ task should use this pattern:

````text
Propose one neutral closed-shell small molecule as an XYZ geometry.

The molecule must satisfy these requirements:
- The XYZ must contain exactly one connected molecule with all hydrogens explicit.
- Allowed elements: H, C, N, O, F, P, S, Cl, Br.
- Atom count must be between 3 and 80 inclusive.
- Heavy atom count must be between 1 and 40 inclusive.
- Coordinates must be in Angstrom and suitable for local xTB optimization.
- <target property requirement>

Your final answer must appear exactly in this format:
FINAL ANSWER:
```xyz
<XYZ content>
```
````

Prompts may mention the scientific property and xTB method, but must not expose
verifier IDs, script paths, parsing regexes, aggregation formulas, or scoring
constants such as `sigma`.

In concrete task cards, replace `<target property requirement>` with the
task-specific property line and `<XYZ content>` with the literal example marker
shown to models.

## Scoring

Reuse the existing scoring modes already used by RDKit and material tasks:

- `window`: score 1.0 inside the window; outside the window apply exponential
  decay based on `sigma`.
- `maximize_bounded`: linearly scale from `lower` to `upper`, clamp to
  `[0.0, 1.0]`.
- `minimize_bounded`: linearly scale from `upper` down to `lower`, clamp to
  `[0.0, 1.0]`.
- multi-objective tasks use `geometric_mean`.

Supported optimization directions:

- `homo_lumo_gap`: maximize and minimize are both valid.
- `dipole_moment`: maximize is valid for the first batch; minimization should
  wait for a future symmetry-control task.
- `relaxation_energy`: minimize only. Maximizing relaxation energy would reward
  bad geometries and should not be included.

## Failure Policy

The verifier should produce deterministic failure rows:

```yaml
failure_policy:
  malformed_final_answer: parse_error
  invalid_xyz: parse_error
  invalid_coordinates: validity_error
  disconnected_geometry: validity_error
  atom_overlap: validity_error
  outside_domain: domain_error
  unsupported_charge_or_spin: domain_error
  missing_xtb: verifier_environment_error
  xtb_nonzero_exit: verifier_tool_error
  xtb_optimization_not_converged: verifier_tool_error
  xtb_missing_property: verifier_tool_error
  timeout: verifier_timeout
```

Mapping details:

- Missing or malformed fenced XYZ block is an extraction `parse_error`.
- Atom-count mismatch, malformed atom lines, or non-finite coordinates are
  verifier-level `parse_error`.
- Overlapping atoms and disconnected molecular geometries are
  `validity_error`.
- Disallowed elements, too many atoms, too few atoms, out-of-bounds coordinates,
  or unsupported charge/spin are `domain_error`.
- Missing xTB executable is `verifier_environment_error`.
- Nonzero xTB exits, unconverged optimizations, or missing properties are
  `verifier_tool_error`.
- Timed-out xTB runs are `verifier_timeout`.

For error rows, preserve `raw_answer` and `extracted_answer` when available.

## Testing Scope

Add focused tests at five levels.

1. Answer extraction tests:
   - `final_answer_block` supports `value_type: xyz`.
   - The last `FINAL ANSWER:` block wins.
   - Missing fenced block returns `parse_error`.
   - Empty XYZ block returns `parse_error`.
   - Structured answer records with `candidates` still bypass extraction.

2. Task and verifier spec tests:
   - `tasks/xtb_xyz/tasks.yaml` is YAML-loadable.
   - Every task uses `answer_schema.format: final_answer_block`.
   - Every xTB constraint has a `verifier_id`.
   - Every referenced verifier spec exists.
   - Every verifier spec has a non-empty `verification_script`.
   - Prompts expose all hard domain gates but do not expose verifier IDs or
     script paths.

3. Backend unit tests with a fake xTB runner:
   - Valid XYZ parses into atoms and coordinates.
   - Atom-count mismatch returns `parse_error`.
   - Disallowed element returns `domain_error`.
   - Overlapping atoms return `validity_error`.
   - Disconnected geometry returns `validity_error`.
   - Fake gap, dipole, and energy outputs parse into properties.
   - `window`, `maximize_bounded`, and `minimize_bounded` constraints score
     through existing `score_constraint`.
   - xTB missing executable, nonzero exit, timeout, and missing property map to
     the documented failure types.

4. Script runner tests:
   - Each property script rejects mismatched `property_name` with
     `verifier_spec_error`.
   - Each property script calls the shared backend and returns the normalized
     result shape.
   - Multi-constraint routing aggregates gap and dipole results.

5. Optional environment smoke test:
   - `scripts/check_xtb_env.py` reports the detected `xtb --version`.
   - If xTB is installed, run a tiny water XYZ through optimization and parse
     gap, dipole, total energy, and optimized energy.
   - CI should not require xTB; the smoke test should be manually runnable or
     skipped when `xtb` is absent.

## Implementation Notes

Keep the backend independent of AtomisticSkills. xTB should be a local executable
backend first, because the direct XYZ task is small-molecule focused and does
not need MCP routing.

The implementation should not use generated 3D coordinates from SMILES. Sample
answers may be hand-authored or copied from known molecules, but the verifier
input contract is always the model's final XYZ block.

The first implementation should parse xTB text output conservatively. If xTB can
provide a stable machine-readable output file in the installed version, prefer
that file over regexes; otherwise keep regexes small, version-tested, and covered
by fixture outputs.

This design intentionally leaves SDF, charge/multiplicity fields, frequency
analysis, vertical IP/EA, solvation, and conformer ensembles for later specs.
