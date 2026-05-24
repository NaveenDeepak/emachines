"""Electric Motors module — DC and PMSM models."""

from .motors import (
    # DC Motor classes
    GeometricParams,
    MaterialProperties,
    OperatingConditions,
    LumpedParams,
    # DC Motor functions
    calculate_carter_coefficient,
    calculate_magnetic_circuit,
    calculate_armature_resistance,
    calculate_motor_constants,
    calculate_rotor_inertia,
    calculate_lumped_parameters,
    calculate_steady_state_performance,
    calculate_losses_and_efficiency,
    plot_efficiency_map,
    # PMSM classes
    PMSMParams,
    SPM,
    # PMSM functions
    back_emf,
    torque,
    dq_currents,
)

__all__ = [
    "GeometricParams",
    "MaterialProperties",
    "OperatingConditions",
    "LumpedParams",
    "calculate_carter_coefficient",
    "calculate_magnetic_circuit",
    "calculate_armature_resistance",
    "calculate_motor_constants",
    "calculate_rotor_inertia",
    "calculate_lumped_parameters",
    "calculate_steady_state_performance",
    "calculate_losses_and_efficiency",
    "plot_efficiency_map",
    "PMSMParams",
    "SPM",
    "back_emf",
    "torque",
    "dq_currents",
]
