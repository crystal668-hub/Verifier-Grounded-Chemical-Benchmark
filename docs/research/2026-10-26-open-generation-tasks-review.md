# Open Generation Tasks Review Report

> 历史分级说明（2026-10-28）：本文的旧难度标签、分布及调整建议已失效，
> 仅保留为历史记录。当前任务统一使用 basic / advanced，具体映射以
> [标准任务难度等级](../design/task-difficulty-levels.md)及正式 tasks.yaml 为准；不要复用本文的旧分级示例。

**Date:** 2026-10-26  
**Reviewer:** Claude (AI Assistant)  
**Scope:** `open_generation_rdkit` and `open_generation_xtb` tracks  
**Total Tasks Reviewed:** 34 (14 RDKit + 20 xTB)

---

## Executive Summary

This report provides a comprehensive review of all tasks in the `open_generation_rdkit` and `open_generation_xtb` tracks from four critical perspectives:

1. **Novelty**: Whether the task represents a meaningful challenge beyond trivial database lookup
2. **Difficulty**: Whether the declared difficulty aligns with the actual chemical and computational challenge
3. **Gaming Potential**: Whether "extreme molecules" or trivial solutions can satisfy constraints without real chemical meaning
4. **Scientific Value**: Whether designing such molecules has practical implications in chemistry

### Key Findings

**Strengths:**
- Strong alignment with verifier-grounded philosophy - tasks require actual property calculation, not database lookup
- Good difficulty progression within each track
- Most tasks have clear chemical relevance (drug design, materials, quantum properties)
- XYZ geometry submission for xTB tasks effectively prevents trivial SMILES-only solutions

**Areas of Concern:**
- Some simple RDKit tasks (001-007) may be gameable with memorized drug-like scaffolds
- Task difficulty calibration needs empirical validation with model panel results
- A few tasks lack strong scientific motivation beyond "optimization for optimization's sake"
- Edge cases around molecular validity and domain boundaries need more explicit guards

---

## Part 1: RDKit Track Review (14 Tasks)

### Overview

The RDKit track focuses on 2D molecular design with fast descriptor-based properties. Tasks range from simple single-property satisfaction to multi-objective optimization and similarity-constrained generation.

---

### Task rdkit_001_qed_max

**Difficulty:** simple  
**Objective:** Maximize QED (drug-likeness) within basic constraints

#### Novelty Assessment: ⭐⭐ (Moderate)

The QED (Quantitative Estimate of Drug-likeness) maximization task is a well-established problem in computational drug discovery. While not groundbreaking, it serves as an excellent baseline task that:
- Tests basic understanding of drug-like chemical space
- Has clear pharmaceutical relevance
- Is commonly used in molecular optimization literature (Brown et al., J. Med. Chem. 2012)

However, the optimal QED molecules are relatively well-known in the literature, reducing pure novelty.

#### Difficulty Assessment: ✅ Appropriate (simple)

For LLMs:
- QED-optimized scaffolds appear extensively in training data (PubChem, ChEMBL)
- The constraint space is permissive (5-60 heavy atoms, MW ≤600, charge ±1)
- High-QED molecules like aspirin analogs are common knowledge

For computational methods:
- Any basic evolutionary algorithm can easily find near-optimal solutions
- The search space is relatively unconstrained

**Verdict:** Correctly labeled as "simple"

#### Gaming Potential: ⚠️ HIGH

**Trivial Solutions:**
- Known drugs with QED > 0.9 are readily available (e.g., acetaminophen QED ≈ 0.91)
- Simple modifications of aspirin, ibuprofen analogs
- Molecules like `COc1ccccc1NC(=O)C` (paracetamol analog) achieve QED > 0.88

**Extreme Molecule Concern:**
The task currently allows very small molecules (5 heavy atoms) which might not be pharmaceutically meaningful. A 5-heavy-atom molecule with high QED could be:
- `Cc1cnccn1` (methylpyrazine-like)
- These are too small for most drug applications

**Recommendation:**
- Increase minimum heavy atom count to 8-10 for pharmaceutical relevance
- Add explicit "no trivial drug name" guard or require QED > 0.92 to push beyond memorized examples

#### Scientific Value: ✅ GOOD

**Practical Relevance:**
- Drug-likeness is a core filter in medicinal chemistry
- Early-stage virtual screening relies heavily on QED
- Teaches fundamental concepts about ADME-friendly chemical space

**Real-world Application:**
- Lead optimization routinely considers QED
- Fragment-to-lead expansion uses similar constraints
- Hit identification prioritizes drug-like chemical matter

**Verdict:** Strong scientific motivation despite being a simple task

---

### Task rdkit_002_sa_min

**Difficulty:** simple  
**Objective:** Minimize synthetic accessibility (SA) score (1-10 scale, lower = easier to synthesize)

#### Novelty Assessment: ⭐⭐⭐ (Good)

Synthetic accessibility optimization is highly relevant and less commonly benchmarked than QED. The SA score (Ertl & Schuffenhauer, 2009) is widely used in practice but:
- Optimal solutions are less memorized than QED
- Requires understanding of synthetic chemistry principles
- Balances structural simplicity with chemical validity

#### Difficulty Assessment: ✅ Appropriate (simple)

The SA score tends to favor:
- Linear aliphatic chains (lowest SA ~1.0)
- Simple aromatic rings
- Molecules with few functional groups

Finding low-SA molecules is straightforward:
- `CCCCCC` (hexane): SA ≈ 1.03
- `c1ccccc1` (benzene): SA ≈ 1.26
- Simple alcohols and amines

**Verdict:** Correctly simple, though easier than QED for knowledgeable systems

#### Gaming Potential: ⚠️ HIGH

**Trivial Solutions:**
Simple aliphatic or aromatic hydrocarbons dominate:
- n-Alkanes: `CCCCCCCCCC` (decane) - SA ≈ 1.0
- Benzene and simple substitutions: `Cc1ccccc1` (toluene) - SA ≈ 1.2

**Extreme Molecule Concern:**
The task explicitly allows heavy atoms 5-60, which permits trivial 5-6 carbon molecules:
- `CCCCC` (pentane): SA ≈ 1.01 - pharmaceutically meaningless
- Very small ring systems

**Recommendation:**
- Require minimum 10 heavy atoms for pharmaceutical context
- Add "at least 2 heteroatoms" to exclude pure hydrocarbons
- Consider combining with a hardSA constraint threshold (e.g., require at least one N, O, or S)

#### Scientific Value: ⭐⭐⭐⭐ EXCELLENT

**Practical Relevance:**
- Synthetic accessibility is a critical bottleneck in drug discovery
- Retrosynthetic planning relies on SA estimates
- Balance between novelty and synthetic feasibility is key in medicinal chemistry

**Real-world Application:**
- Lead optimization must consider synthetic routes
- Fragment libraries prioritize synthesizable compounds
- Cost-effective scale-up requires low SA scores

**Verdict:** High scientific value; the task directly addresses a major pain point in drug design

---

### Task rdkit_003_logp_window

**Difficulty:** simple  
**Objective:** logP between 1.0 and 3.0 (Lipinski-like range)

#### Novelty Assessment: ⭐⭐ (Moderate)

logP window targeting is a standard medicinal chemistry task. The 1.0-3.0 range represents oral bioavailability "sweet spot" (Lipinski's Rule of Five region). However:
- Well-documented in pharmaceutical literature
- Many known drugs fall in this range
- Less novel than multi-objective tasks

#### Difficulty Assessment: ✅ Appropriate (simple)

**For LLMs:**
- Common drug scaffolds (quinolines, benzimidazoles) naturally fall in this range
- logP is well-correlated with training data annotations

**For Algorithms:**
- logP is a smooth, continuous property
- Trivial for graph-based molecular optimization

**Verdict:** Correctly labeled as simple

#### Gaming Potential: ⚠️ MODERATE

**Trivial Solutions:**
Many well-known compounds satisfy this:
- `COc1ccccc1` (anisole): logP ≈ 2.1
- `Cc1ccc(O)cc1` (p-cresol): logP ≈ 1.95
- `c1ccc2c(c1)ccn2C` (N-methylindole): logP ≈ 2.2

**Extreme Molecules:**
The window is actually well-bounded, but edge cases exist:
- Very small molecules with exact logP = 1.0 or 3.0 may lack drug relevance
- 5-heavy-atom molecules are borderline meaningful

**Recommendation:**
- Increase minimum size to 8-10 heavy atoms
- Consider requiring aromatic rings (most drugs have them)
- Add "at least 1 nitrogen" constraint for drug-like context

#### Scientific Value: ✅ GOOD

**Practical Relevance:**
- Oral bioavailability directly depends on logP
- Blood-brain barrier penetration correlates with logP
- Lipophilicity affects metabolism and clearance

**Real-world Application:**
- Lipinski's Rule of Five explicitly includes logP
- Lead optimization routinely adjusts logP to 0.5-3.5 range
- Formulation scientists need specific logP windows

**Verdict:** Strong pharmaceutical relevance; teaches core ADME principles

---

### Task rdkit_004_tpsa_window

**Difficulty:** simple  
**Objective:** TPSA (topological polar surface area) between 35.0-75.0 Ų

#### Novelty Assessment: ⭐⭐ (Moderate)

TPSA windows are standard in drug design (Egan et al., J. Med. Chem. 2000). The 35-75 Ų range correlates with good oral absorption. Limited novelty as it's a well-established filter.

#### Difficulty Assessment: ✅ Appropriate (simple)

TPSA is highly predictable:
- Directly calculated from 2D structure (count of O, N, their neighbors)
- Polar atoms in specific environments contribute fixed values
- Easy to design molecules hitting a target TPSA

**Examples:**
- `COc1ccccc1CN` (TPSA ≈ 35): lower bound
- `COc1ccc(C(=O)N)cc1` (TPSA ≈ 55): mid-range
- `O=C(O)Cc1cc(O)c(O)cc1` (TPSA ≈ 98): slightly above, needs adjustment

**Verdict:** Simple and correctly labeled

#### Gaming Potential: ⚠️ MODERATE

**Trivial Solutions:**
