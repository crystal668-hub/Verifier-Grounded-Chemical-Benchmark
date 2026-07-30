# VGB 13 道题任务提示词与得分规则

本文按《[VGB 13-task 原始模型输出](./2026-07-28-vgb-13-task-raw-model-responses.md)》中的题目顺序，整理 v0.4.2 正式 task pack 的任务提示词与 verifier 得分规则。

## 统一计分约定

- 开放生成题先检查答案格式、候选有效性、结构域和分子身份；任一必要门失败时，候选得 0 分。环境、工具或超时错误属于评测失败，不应当作候选 0 分。
- 有硬性质约束的题目先计算硬约束；硬约束不满足时得 0 分，只有通过后才计算主性质分。
- 下文的线性分数均截断到 `[0, 1]`。11 道开放生成题均只有一个主性质，因此主性质分就是任务分。
- 最小化/最大化性质在满分锚点与零分锚点之间线性插值；达到或优于满分锚点为 1，达到或劣于零分锚点为 0。
- target 性质在目标点得 1 分，按目标两侧给定宽度线性衰减至 0。
- property calculation 题先对同一 comparison group 内字段取最低分，再对各 group 分数做算术平均。

## 1. `rdkit_logp_target_011`

track: RDKit

### 任务提示词

    Propose one valid single-component molecule and provide it as a SMILES string.

    The molecule must satisfy these requirements:
    - The SMILES must describe exactly one component; dot-separated multi-component SMILES are not accepted.
    - Allowed elements: H, C, O, N, S, F, Cl.
    - After adding any implicit hydrogens, the total atom count including hydrogens must be at most 40.
    - After adding any implicit hydrogens, oxygen atoms must make up at least 10% of all atoms.
    - Make the logP value as close as possible to 3.0.

    Your final answer must appear on its own line exactly in this format:
    FINAL ANSWER: <SMILES>

### 得分规则

- 结构门：单组分有效 SMILES；仅允许 H、C、O、N、S、F、Cl；含隐式氢总原子数不超过 40；氧原子比例至少 10%。不满足时得 0 分。
- 性质：RDKit `Crippen.MolLogP`。
- 目标：`logP = 3.0`，左右衰减宽度均为 `3.0`。
- 公式：`score = max(0, 1 - |logP - 3.0| / 3.0)`。

## 2. `rdkit_sa_logp_target_012`

track: RDKit

### 任务提示词

    Propose one valid single-component organic molecule and provide it as a SMILES string.

    The molecule must satisfy these requirements:
    - Allowed elements: H, C, O, N, S, F, Cl.
    - It must contain at least one carbon atom.
    - After adding all implicit hydrogens, the total atom count must be at most 40.
    - Its synthetic accessibility score must be strictly below 5.0.
    - Subject to those requirements, make logP as close as possible to 3.0.

    Your final answer must appear on its own line exactly in this format:
    FINAL ANSWER: <SMILES>

### 得分规则

- 结构门：单组分有效 SMILES；仅允许 H、C、O、N、S、F、Cl；至少一个碳；含隐式氢总原子数不超过 40。
- 硬约束：`SA score < 5.0`；等于 5.0 也不通过，失败得 0 分。
- 主性质：RDKit LogP；`score = max(0, 1 - |logP - 3.0| / 3.0)`。

## 3. `rdkit_chain_end_to_end_max_013`

track: RDKit

### 任务提示词

    Propose one valid single-component neutral molecule and provide it as a SMILES string.

    The molecule must satisfy these requirements:
    - Allowed elements: H, C, N, O, S, F, Cl.
    - It must match the SMARTS pattern `[C;X4;!R]-[C;X4;!R]-[C;X4;!R]-[C;X4;!R]-[C;X4;!R]-[C;X4;!R]`, representing one continuous non-ring, saturated, single-bonded six-carbon chain.
    - It must contain exactly six carbon atoms; no other carbon atoms or carbon skeletons are allowed.
    - After adding all implicit hydrogens, the total atom count must be at most 40.
    - A terminal atom means a non-hydrogen atom with exactly one non-hydrogen neighbor. The fixed conformer workflow generates conformers with RDKit, optimizes them with the Universal Force Field (UFF), and ranks the converged conformers by UFF energy. In the lowest-energy converged UFF conformer, maximize the largest Euclidean distance between any pair of terminal atom nuclei. Hydrogens are not terminal-atom candidates for this distance.

    Your final answer must appear on its own line exactly in this format:
    FINAL ANSWER: <SMILES>

### 得分规则

- 结构门：单组分、中性、允许元素范围内；恰好含 6 个碳并匹配指定六碳非环饱和链 SMARTS；含氢总原子数不超过 40。
- 协议：ETKDGv3，随机种子 `61453`，20 个 conformer，`pruneRmsThresh = 0.5`；UFF 最多优化 200 次；取最低能量的已收敛 conformer，枚举重原子图中只有一个重原子邻居的全部末端重原子，并测量其中最大的原子对距离。氢不参与。
- 满分锚点 `21.68 A`，零分锚点 `6.36 A`。
- 公式：`d <= 6.36` 为 0，`d >= 21.68` 为 1，中间为 `(d - 6.36) / 15.32`。

## 4. `rdkit_caffeine_similarity_max_014`

track: RDKit

### 任务提示词

    Propose one valid single-component molecule and provide it as a SMILES string.

    The molecule must satisfy these requirements:
    - logP must be between -0.5 and 1.5 inclusive.
    - Synthetic accessibility score must be no greater than 2.79798245679401.
    - QED must be between 0.65 and 0.75 inclusive.
    - Subject to those requirements, maximize molecular similarity to caffeine.

    Your final answer must appear on its own line exactly in this format:
    FINAL ANSWER: <SMILES>

### 得分规则

- 结构门：单组分有效 SMILES。
- 三个硬约束必须同时满足：`-0.5 <= logP <= 1.5`、`SA <= 2.79798245679401`、`0.65 <= QED <= 0.75`；任一失败得 0 分。
- 参考 caffeine：`Cn1c(=O)c2c(ncn2C)n(C)c1=O`。
- 相似度：RDKit Morgan bit fingerprint，radius 2、2048 bits、不含 chirality、使用 bond types；计算 Tanimoto similarity。
- 公式：`score = caffeine_morgan_tanimoto`。

## 5. `xtb_formula_dipole_min_014`

track: xTB

### 任务提示词

    Propose one connected molecule with formula C12H16N3O8 as an XYZ geometry.

    The molecule must satisfy these requirements:
    - The XYZ must contain all hydrogens explicitly.
    - Use a neutral doublet electronic state.
    - Minimize the dipole moment after geometry optimization.

    Your final answer must appear exactly in this format:
    FINAL ANSWER:
    ```xyz
    <XYZ content>
    ```

### 得分规则

- 结构门：XYZ、坐标和连通性有效，无原子重叠；分子式严格为 `C12H16N3O8`，所有氢显式。
- 协议：中性 doublet，`charge = 0`、`UHF = 1`；GFN2-xTB 几何优化后读取总偶极矩。
- 满分锚点 `3.042 D`，零分锚点 `9.328 D`。
- 公式：`mu <= 3.042` 为 1，`mu >= 9.328` 为 0，中间为 `(9.328 - mu) / 6.286`。

## 6. `xtb_two_fluorine_gap_min_015`

track: xTB

### 任务提示词

    Propose one connected closed-shell molecule as an XYZ geometry.

    The molecule must satisfy these requirements:
    - The XYZ must contain all hydrogens explicitly.
    - Allowed elements: H, C, O, N, S, F, Cl.
    - The total atom count, including hydrogens, must be at most 40.
    - The molecule must contain exactly 2 fluorine atoms and at most 10 carbon atoms.
    - The XYZ comment line must have the exact form charge=<integer>.
    - Minimize the HOMO-LUMO gap after geometry optimization.

    Your final answer must appear exactly in this format:
    FINAL ANSWER:
    ```xyz
    <XYZ content>
    ```

### 得分规则

- 结构门：一个连通闭壳层分子；所有氢显式；仅允许 H、C、O、N、S、F、Cl；总原子数不超过 40；恰好 2 个 F；C 不超过 10。
- 电荷从 XYZ comment 的严格 `charge=<integer>` 读取；`UHF = 0`，验证电子奇偶性符合闭壳层。
- 协议：GFN2-xTB 几何优化后读取 orbital-energy HOMO-LUMO gap。
- 满分锚点 `1.242666887976 eV`，零分锚点 `12.358052453139 eV`；两点间线性插值，gap 越小越好。

## 7. `xtb_c10_f2_gap_min_016`

track: xTB

### 任务提示词

    Propose one connected closed-shell molecule as an XYZ geometry.

    The molecule must satisfy these requirements:
    - The XYZ must contain all hydrogens explicitly.
    - Allowed elements: H, C, O, N, S, F, Cl.
    - The total atom count, including hydrogens, must be at most 40.
    - The molecule must contain exactly 10 carbon atoms and exactly 2 fluorine atoms.
    - The XYZ comment line must have the exact form charge=<integer>.
    - Minimize the HOMO-LUMO gap after geometry optimization.

    Your final answer must appear exactly in this format:
    FINAL ANSWER:
    ```xyz
    <XYZ content>
    ```

### 得分规则

- 与第 6 题使用同一 GFN2-xTB closed-shell、candidate-charge 优化与 gap 评分协议。
- 结构域差异：必须恰好含 10 个 C 和 2 个 F，而不是“C 至多 10 个”。
- 满分锚点、零分锚点和线性公式与第 6 题相同。

## 8. `xtb_roy_singlepoint_energy_min_017`

track: xTB

### 任务提示词

    Propose a low-energy 3D conformer of the ROY molecule with this reference SMILES:
    Cc1cc(c(s1)Nc2ccccc2[N+](=O)[O-])C#N

    The XYZ must contain all hydrogens explicitly. Minimize the single-point energy of the submitted geometry; do not assume geometry optimization before scoring.

    Your final answer must appear exactly in this format:
    FINAL ANSWER:
    ```xyz
    <XYZ content>
    ```

### 得分规则

- 身份门：XYZ 有效、连通、无重叠，所有氢显式；分子式 `C12H9N3O2S`；分子图与参考 ROY 一致，不要求立体化学。
- 协议：中性闭壳层，`charge = 0`、`UHF = 0`；直接对提交坐标做 GFN2-xTB single-point，不先优化。
- 满分锚点 `-50.302552312418 Eh`，零分锚点 `-50.287905192962 Eh`；两点间线性插值，能量越负越好。

## 9. `xtb_ritonavir_optimized_energy_min_018`

track: xTB

### 任务提示词

    Propose a low-energy 3D conformer of Ritonavir with this isomeric reference SMILES:
    CC(C)C1=NC(=CS1)CN(C)C(=O)N[C@@H](C(C)C)C(=O)N[C@@H](CC2=CC=CC=C2)C[C@@H]([C@H](CC3=CC=CC=C3)NC(=O)OCC4=CN=CS4)O

    The XYZ must contain all hydrogens explicitly. Minimize the energy after geometry optimization while preserving the molecular structure and specified stereochemistry.

    Your final answer must appear exactly in this format:
    FINAL ANSWER:
    ```xyz
    <XYZ content>
    ```

### 得分规则

- 身份门：XYZ 有效、连通、无重叠，所有氢显式；分子式 `C37H48N6O5S2`；分子图和指定立体化学必须与 reference SMILES 一致。
- 协议：中性闭壳层，`charge = 0`、`UHF = 0`；GFN2-xTB 几何优化，并在优化前后检查结构身份和立体化学。
- 满分锚点 `-148.210476869589 Eh`，零分锚点 `-148.183476873812 Eh`；两点间线性插值。

## 10. `xtb_odd_element_counts_gap_max_019`

track: xTB

### 任务提示词

    Propose one neutral closed-shell singlet organic molecule as an XYZ geometry with all hydrogens explicit.

    The molecule must satisfy these requirements:
    - It must be exactly one connected molecule with at most 40 total atoms.
    - Allowed elements: H, C, O, N, S, F, Cl.
    - It must contain at least one carbon atom and at least seven heavy atoms.
    - At least three different non-hydrogen elements must occur.
    - Every non-hydrogen element that occurs must have an odd atom count.
    - Its optimized dipole magnitude must be strictly below 2.0 debye.
    - Subject to those requirements, maximize its optimized orbital-energy HOMO-LUMO gap.

    Your final answer must appear exactly in this format:
    FINAL ANSWER:
    ```xyz
    <XYZ content>
    ```

### 得分规则

- 结构门：一个连通分子，总原子数不超过 40；至少 7 个重原子和 1 个碳；至少 3 种非氢元素；出现的每种非氢元素计数均为奇数；所有氢显式。
- 电子态：中性闭壳层 singlet，`charge = 0`、`UHF = 0`；同一次 GFN2-xTB 优化给出偶极矩和 gap。
- 硬约束：优化后偶极矩严格 `< 2.0 D`；失败得 0 分。
- 满分锚点 `11.9 eV`，零分锚点 `3.6 eV`。
- 公式：gap `<= 3.6` 为 0，gap `>= 11.9` 为 1，中间为 `(gap - 3.6) / 8.3`。

## 11. `xtb_pyrene_substituent_energy_min_020`

track: xTB

### 任务提示词

    Starting from the pyrene framework c1cc2ccc3cccc4ccc(c1)c2c34, propose one neutral molecule with exactly three substitutions at distinct original carbon-hydrogen sites: one nitro group, one amino group, and one carboxyl group.

    The 16-carbon pyrene framework, its bond pattern, and its ring system must remain unchanged, and no other substituents are allowed. Minimize the total electronic energy of the lowest conformer found by the fixed search protocol.

    Your final answer must appear on its own line exactly in this format:
    FINAL ANSWER: <SMILES>

### 得分规则

- 身份门：中性、单组分有效 SMILES；保持 16-carbon pyrene 骨架、键型和环系；恰好在三个原始 C-H 位点分别加入一个 nitro、amino 和 carboxyl，不允许其他取代。
- 协议：随机种子 `61453`，CREST 2.12 `-mquick`、单线程 conformer search；取 CREST ensemble 最低构象，再做 GFN2-xTB single-point total energy。
- 满分锚点 `-63.56975 Eh`，零分锚点 `-63.5669 Eh`；两点间线性插值，能量越负越好。

## 12. `property_calc_free_energy_001`

track: property calculation

### 任务提示词

    Given the following two molecular crystal structures, calculate the absolute difference between their free energies at 300 K. Report the result in kJ/mol.

    Crystal ETDIAM01:
    ```cif
    <ETDIAM01 CIF content>
    ```

    Crystal ETDIAM18:
    ```cif
    <ETDIAM18 CIF content>
    ```

    Your final answer must appear on its own line exactly in this format:
    FINAL ANSWER: {"answer":<number>,"unit":"kJ/mol"}

固定输入是提示词内完整嵌入的 ETDIAM01 和 ETDIAM18 P1 CIF。为避免在本清单中重复约 90 行坐标，完整逐字 CIF 见正式 [`property_calculation/tasks.yaml`](../../src/verifier_grounded_benchmark/task/packs/property_calculation/tasks.yaml)。

### 得分规则

- 提交值必须是有限数值且单位严格为 `kJ/mol`；单位不匹配得 0 分。
- gold：`0.258031679 kJ/mol`；左右 tolerance 均为 `0.258031679 kJ/mol`。
- 公式：`score = max(0, 1 - |answer - 0.258031679| / 0.258031679)`。
- 本题只有一个 comparison group，因此任务分等于该字段分。

## 13. `property_calc_crystal_phase_002`

track: property calculation

### 任务提示词

    Given the following alpha and beta crystal structures, calculate the absolute difference between their potential energies in eV. Also identify which labeled structure is the ambient-pressure phase and which is the high-pressure phase.

    Crystal alpha:
    ```cif
    <alpha CIF content>
    ```

    Crystal beta:
    ```cif
    <beta CIF content>
    ```

    Your final answer must appear on its own line exactly in this format:
    FINAL ANSWER: {"answers":[{"property":"potential_energy_difference","value":<number>,"unit":"eV"},{"property":"ambient_pressure_phase","value":"<alpha-or-beta>"},{"property":"high_pressure_phase","value":"<alpha-or-beta>"}]}

固定输入是提示词内完整嵌入的 alpha 和 beta P1 CIF。两段共约 260 行，完整逐字内容见正式 [`property_calculation/tasks.yaml`](../../src/verifier_grounded_benchmark/task/packs/property_calculation/tasks.yaml)。

### 得分规则

- `potential_energy_difference`：gold 为 `0.079 eV`，单位必须严格为 `eV`，左右 tolerance 均为 `0.079 eV`；`energy_score = max(0, 1 - |answer - 0.079| / 0.079)`。
- `ambient_pressure_phase` 必须与 gold 字符串 `alpha` 完全一致；`high_pressure_phase` 必须与 `beta` 完全一致。
- 两个 phase 字段同属 `pressure_phase_assignment` group，组分取二者最低值；必须同时答对才有 `phase_score = 1`，否则为 0。
- 最终分：`score = (energy_score + phase_score) / 2`。因此能量答案错误但两个 phase 正确时仍可得 `0.5`。

## 规范来源

- RDKit 任务和 scoring profiles：[`rdkit/tasks.yaml`](../../src/verifier_grounded_benchmark/task/packs/rdkit/tasks.yaml)
- RDKit verifier protocols：[`rdkit/verifier_specs.yaml`](../../src/verifier_grounded_benchmark/task/packs/rdkit/verifier_specs.yaml)
- xTB 任务和 scoring profiles：[`xtb/tasks.yaml`](../../src/verifier_grounded_benchmark/task/packs/xtb/tasks.yaml)
- xTB verifier protocols：[`xtb/verifier_specs.yaml`](../../src/verifier_grounded_benchmark/task/packs/xtb/verifier_specs.yaml)
- Property Calculation 任务和 gold：[`property_calculation/tasks.yaml`](../../src/verifier_grounded_benchmark/task/packs/property_calculation/tasks.yaml)
- 分段线性评分实现：[`linear_goal.py`](../../src/verifier_grounded_benchmark/evaluation/common/scoring/linear_goal.py)
