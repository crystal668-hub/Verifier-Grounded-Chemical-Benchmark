"""Optional OpenMM/OpenFF runtime helpers."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import math
from dataclasses import dataclass
from typing import Any


ENV_FAILURE = "verifier_env_error"
TOOL_FAILURE = "verifier_tool_error"
DEFAULT_OPENFF_SMILES = "CCO"
DEFAULT_OPENFF_FORCEFIELD = "openff-2.2.1.offxml"


class OpenMMEnvironmentError(RuntimeError):
    """Raised when the optional OpenMM/OpenFF runtime is missing or unusable."""


class OpenMMToolError(RuntimeError):
    """Raised when an installed OpenMM/OpenFF tool fails during calculation."""


@dataclass(frozen=True)
class RuntimeModules:
    openmm: Any
    unit: Any
    app: Any | None = None
    openff_toolkit: Any | None = None
    openff_interchange: Any | None = None
    openmmforcefields: Any | None = None


def package_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "unknown"


def import_required(module_name: str) -> Any:
    try:
        return importlib.import_module(module_name)
    except Exception as exc:
        raise OpenMMEnvironmentError(f"missing optional dependency: {module_name}") from exc


def load_core_modules() -> RuntimeModules:
    openmm = import_required("openmm")
    unit = import_required("openmm.unit")
    return RuntimeModules(openmm=openmm, unit=unit)


def load_openff_modules() -> RuntimeModules:
    openmm = import_required("openmm")
    unit = import_required("openmm.unit")
    app = import_required("openmm.app")
    openff_toolkit = import_required("openff.toolkit")
    openff_interchange = import_required("openff.interchange")
    return RuntimeModules(
        openmm=openmm,
        unit=unit,
        app=app,
        openff_toolkit=openff_toolkit,
        openff_interchange=openff_interchange,
    )


def load_gaff_modules() -> RuntimeModules:
    modules = load_openff_modules()
    openmmforcefields = import_required("openmmforcefields.generators")
    return RuntimeModules(
        openmm=modules.openmm,
        unit=modules.unit,
        app=modules.app,
        openff_toolkit=modules.openff_toolkit,
        openff_interchange=modules.openff_interchange,
        openmmforcefields=openmmforcefields,
    )


def openmm_platforms(openmm: Any) -> list[str]:
    try:
        return [openmm.Platform.getPlatform(index).getName() for index in range(openmm.Platform.getNumPlatforms())]
    except Exception as exc:
        raise OpenMMEnvironmentError(f"failed to enumerate OpenMM platforms: {exc}") from exc


def select_platform(openmm: Any, preferred: str = "Reference") -> Any:
    platforms = openmm_platforms(openmm)
    if preferred in platforms:
        return openmm.Platform.getPlatformByName(preferred)
    if "CPU" in platforms:
        return openmm.Platform.getPlatformByName("CPU")
    if platforms:
        return openmm.Platform.getPlatformByName(platforms[0])
    raise OpenMMEnvironmentError("no OpenMM Reference or CPU platform available")


def finite_float(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise OpenMMToolError(f"{label} was not finite")
    return result


def run_core_smoke(preferred_platform: str = "Reference") -> dict[str, Any]:
    modules = load_core_modules()
    openmm = modules.openmm
    unit = modules.unit
    platform = select_platform(openmm, preferred_platform)

    system = openmm.System()
    system.addParticle(39.9)
    system.addParticle(39.9)
    bond = openmm.HarmonicBondForce()
    bond.addBond(0, 1, 0.2 * unit.nanometer, 100.0 * unit.kilojoule_per_mole / unit.nanometer**2)
    system.addForce(bond)
    integrator = openmm.VerletIntegrator(0.001 * unit.picoseconds)
    context = openmm.Context(system, integrator, platform)
    try:
        context.setPositions([[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]] * unit.nanometer)
        initial_state = context.getState(getEnergy=True)
        initial_energy = initial_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        openmm.LocalEnergyMinimizer.minimize(context, maxIterations=50)
        final_state = context.getState(getEnergy=True, getForces=True)
        minimized_energy = final_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        forces = final_state.getForces()
        max_force = max(
            vector.norm().value_in_unit(unit.kilojoule_per_mole / unit.nanometer)
            for vector in forces
        )
    finally:
        del context
        del integrator

    return {
        "status": "ok",
        "selected_platform": platform.getName(),
        "initial_energy_kj_mol": finite_float(initial_energy, "initial_energy_kj_mol"),
        "minimized_energy_kj_mol": finite_float(minimized_energy, "minimized_energy_kj_mol"),
        "energy_drop_kj_mol": finite_float(initial_energy - minimized_energy, "energy_drop_kj_mol"),
        "final_max_force_kj_mol_nm": finite_float(max_force, "final_max_force_kj_mol_nm"),
    }


def run_openmm_system_minimization(
    *,
    modules: RuntimeModules,
    system: Any,
    positions: Any,
    preferred_platform: str,
    max_iterations: int = 200,
) -> dict[str, float | str]:
    openmm = modules.openmm
    unit = modules.unit
    platform = select_platform(openmm, preferred_platform)
    integrator = openmm.VerletIntegrator(0.001 * unit.picoseconds)
    context = openmm.Context(system, integrator, platform)
    try:
        context.setPositions(positions)
        initial_state = context.getState(getEnergy=True)
        initial_energy = initial_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        openmm.LocalEnergyMinimizer.minimize(context, maxIterations=max_iterations)
        final_state = context.getState(getEnergy=True, getForces=True)
        minimized_energy = final_state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
        forces = final_state.getForces()
        max_force = max(
            vector.norm().value_in_unit(unit.kilojoule_per_mole / unit.nanometer)
            for vector in forces
        )
    finally:
        del context
        del integrator

    return {
        "selected_platform": platform.getName(),
        "initial_energy_kj_mol": finite_float(initial_energy, "initial_energy_kj_mol"),
        "minimized_energy_kj_mol": finite_float(minimized_energy, "minimized_energy_kj_mol"),
        "energy_drop_kj_mol": finite_float(initial_energy - minimized_energy, "energy_drop_kj_mol"),
        "final_max_force_kj_mol_nm": finite_float(max_force, "final_max_force_kj_mol_nm"),
    }


def run_openff_smoke(
    smiles: str = DEFAULT_OPENFF_SMILES,
    forcefield_name: str = DEFAULT_OPENFF_FORCEFIELD,
    preferred_platform: str = "Reference",
) -> dict[str, Any]:
    modules = load_openff_modules()
    toolkit = modules.openff_toolkit
    interchange_module = modules.openff_interchange

    try:
        molecule = toolkit.Molecule.from_smiles(smiles, allow_undefined_stereo=True)
        molecule.generate_conformers(n_conformers=1)
        molecule.assign_partial_charges(partial_charge_method="am1bcc")
        forcefield = toolkit.ForceField(forcefield_name)
        topology = molecule.to_topology()
        interchange = interchange_module.Interchange.from_smirnoff(forcefield, topology)
        system = interchange.to_openmm()
    except Exception as exc:
        raise OpenMMToolError(f"OpenFF parameterization failed: {exc}") from exc

    metrics = run_openmm_system_minimization(
        modules=modules,
        system=system,
        positions=interchange.positions.to_openmm(),
        preferred_platform=preferred_platform,
    )
    metrics.update(
        {
            "status": "ok",
            "forcefield_name": forcefield_name,
            "charge_method": "am1bcc",
            "parameterization_success": 1,
            "system_particle_count": system.getNumParticles(),
        }
    )
    return metrics


def run_gaff_smoke(preferred_platform: str = "Reference") -> dict[str, Any]:
    del preferred_platform
    modules = load_gaff_modules()
    if not hasattr(modules.openmmforcefields, "GAFFTemplateGenerator"):
        raise OpenMMEnvironmentError("GAFFTemplateGenerator is unavailable in openmmforcefields.generators")
    return {
        "status": "ok",
        "ambertools_available": 1,
        "gaff_template_generator_available": 1,
        "message": "GAFF template generator import smoke passed",
    }
