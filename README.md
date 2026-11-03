# Verifier-Grounded Benchmark — v1.0.0-rc

Python package version: **1.0.0rc1**. Requires Python **3.12**.

The benchmark evaluates chemical problem solving through two complementary task
families. Open generation asks for candidates that satisfy stated property goals
and verifies their properties with fixed computational workflows. Property
calculation asks for properties of given objects and compares final answers with
frozen references. Numeric goals use continuous distance scoring alongside the
required hard gates and discrete-answer rules.

The formal suite contains 100 tasks: RDKit 10, xTB 20, Property Calculation
Basic 51 and Advanced 19. The package supplies tasks and evaluates answers;
model execution and answers are provided by the caller. No track includes
public sample answers. Development regression fixtures are excluded from wheel/sdist.

- [Research positioning and design evolution](docs/design/INITIAL-DESIGN.md)
- [Installation, QuickStart and API/CLI contracts](src/verifier_grounded_benchmark/README.md)
- [RC changes, migration and verification boundaries](docs/research/2026-10-28-v1.0.0-rc-release-notes.md)
- [Detailed implementation and acceptance plan](docs/research/2026-10-28-v1.0.0-rc-implementation-plan.md)
- [Formal task inventory](docs/benchmark_registered_tasks.md)

This RC delivery consists of local distribution artifacts, release materials
and a Git tag. Licensing and redistribution permissions are not declared by
this local build and must be settled before a later public distribution.
The development-only review_system application is not included in the package.
