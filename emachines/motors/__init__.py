"""Motor models: PMSM dq-model, SPM torque-speed profile, PMDC motor."""

from emachines.motors.pmsm import PMSMParams, SPM, back_emf, torque, dq_currents
from emachines.motors.dc_motor import (
    GeometricParams, MaterialProperties, OperatingConditions, LumpedParams,
    calculate_lumped_parameters, calculate_steady_state_performance,
    calculate_losses_and_efficiency, plot_efficiency_map,
)

__all__ = [
    "PMSMParams", "SPM", "back_emf", "torque", "dq_currents",
    "GeometricParams", "MaterialProperties", "OperatingConditions", "LumpedParams",
    "calculate_lumped_parameters", "calculate_steady_state_performance",
    "calculate_losses_and_efficiency", "plot_efficiency_map",
]
