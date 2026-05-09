"""Motor models: PMSM dq-model, SPM torque-speed profile."""

from emachines.motors.pmsm import PMSMParams, SPM, back_emf, torque, dq_currents

__all__ = ["PMSMParams", "SPM", "back_emf", "torque", "dq_currents"]
