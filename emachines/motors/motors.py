"""emachines motors module.

Auto-generated from nbdev notebooks:
- nbs/02_dc_motors.ipynb
- nbs/02_pmsm.ipynb
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

__all__ = [
    "GeometricParams",
    "MaterialProperties",
    "OperatingConditions",
    "LumpedParams",
    "PMSMParams",
    "SPM",
    "calculate_carter_coefficient",
    "calculate_magnetic_circuit",
    "calculate_armature_resistance",
    "calculate_motor_constants",
    "calculate_rotor_inertia",
    "calculate_lumped_parameters",
    "calculate_steady_state_performance",
    "calculate_losses_and_efficiency",
    "plot_efficiency_map",
    "back_emf",
    "torque",
    "dq_currents",
]


@dataclass
class GeometricParams:
    """Geometric dimensions of the motor (SI units)."""

    stator_outer_diameter: float
    stator_inner_diameter: float
    rotor_outer_diameter: float
    rotor_inner_diameter: float
    stack_length: float
    air_gap_length: float
    num_poles: int
    num_armature_slots: int
    slot_opening_width: float
    magnet_arc_angle_deg: float
    magnet_thickness: float
    turns_per_coil: int
    armature_wire_cross_section_m2: float
    is_lap_winding: bool = True


@dataclass
class MaterialProperties:
    """Material properties for motor components."""

    copper_resistivity: float
    steel_permeability: float
    magnet_remanent_flux_density: float
    magnet_recoil_permeability: float
    steel_density: float
    copper_density: float
    shaft_density: float
    hysteresis_coeff: float
    steinmetz_exponent: float
    eddy_current_coeff: float
    lamination_thickness: float


@dataclass
class OperatingConditions:
    """Terminal operating conditions."""

    terminal_voltage: float
    brush_contact_drop_v: float = 1.0
    brush_resistance_total: float = 0.05


@dataclass
class LumpedParams:
    """Calculated lumped-parameter motor model."""

    armature_resistance: float
    armature_inductance: float
    motor_constant: float
    rotor_inertia: float
    viscous_damping: float
    air_gap_flux_density: float
    flux_per_pole: float


def calculate_carter_coefficient(g: float, w_so: float, slot_pitch: float) -> float:
    """Carter's coefficient for slot opening effect."""
    gamma = (w_so / g) ** 2 / (5 + w_so / g)
    k_c = slot_pitch / (slot_pitch - gamma * g)
    return max(k_c, 1.0)


def calculate_magnetic_circuit(
    geom: GeometricParams, mat: MaterialProperties
) -> tuple[float, float]:
    """Magnetic circuit analysis via reluctance network."""
    mu_0 = 4 * np.pi * 1e-7
    pole_face_area = (
        geom.magnet_arc_angle_deg / 360 * np.pi * geom.rotor_outer_diameter * geom.stack_length
    )
    slot_pitch = np.pi * geom.rotor_outer_diameter / geom.num_armature_slots
    k_c = calculate_carter_coefficient(geom.air_gap_length, geom.slot_opening_width, slot_pitch)
    R_gap = (geom.air_gap_length * k_c) / (mu_0 * pole_face_area)

    magnet_area = (
        geom.magnet_arc_angle_deg
        / 360
        * np.pi
        * (geom.stator_inner_diameter - geom.magnet_thickness)
        * geom.stack_length
    )
    R_magnet = geom.magnet_thickness / (mat.magnet_recoil_permeability * magnet_area)

    yoke_t = (geom.stator_outer_diameter - geom.stator_inner_diameter) / 2 - geom.magnet_thickness
    R_stator = (
        np.pi
        * (geom.stator_outer_diameter - yoke_t)
        / geom.num_poles
        / (mat.steel_permeability * yoke_t * geom.stack_length)
    )

    core_t = (geom.rotor_outer_diameter - geom.rotor_inner_diameter) / 2
    R_rotor = (
        np.pi
        * (geom.rotor_inner_diameter + core_t)
        / geom.num_poles
        / (mat.steel_permeability * core_t * geom.stack_length)
    )

    mmf = (
        mat.magnet_remanent_flux_density / mat.magnet_recoil_permeability
    ) * geom.magnet_thickness
    R_total = R_magnet + 2 * R_gap + R_stator + R_rotor
    flux_per_pole = mmf / R_total
    B_gap = flux_per_pole / pole_face_area
    return B_gap, flux_per_pole


def calculate_armature_resistance(geom: GeometricParams, mat: MaterialProperties) -> float:
    """Armature winding resistance."""
    end_winding = np.pi * (geom.rotor_outer_diameter / 2) / geom.num_poles
    mlt = 2 * geom.stack_length + end_winding
    total_conductors = 2 * geom.turns_per_coil * geom.num_armature_slots
    total_length = (total_conductors / 2) * mlt
    R_wire = mat.copper_resistivity * total_length / geom.armature_wire_cross_section_m2
    parallel_paths = geom.num_poles if geom.is_lap_winding else 2
    return R_wire / parallel_paths**2


def calculate_motor_constants(geom: GeometricParams, flux_per_pole: float) -> float:
    """Motor constant K = Kt = Ke."""
    total_conductors = 2 * geom.turns_per_coil * geom.num_armature_slots
    parallel_paths = geom.num_poles if geom.is_lap_winding else 2
    return (total_conductors * geom.num_poles * flux_per_pole) / (2 * np.pi * parallel_paths)


def calculate_rotor_inertia(geom: GeometricParams, mat: MaterialProperties) -> float:
    """Rotor moment of inertia."""
    r_o = geom.rotor_outer_diameter / 2
    r_i = geom.rotor_inner_diameter / 2
    vol_core = np.pi * (r_o**2 - r_i**2) * geom.stack_length
    J_core = 0.5 * mat.steel_density * vol_core * (r_o**2 + r_i**2)
    J_winding = J_core * 0.15
    vol_shaft = np.pi * r_i**2 * geom.stack_length
    J_shaft = 0.5 * mat.shaft_density * vol_shaft * r_i**2
    return J_core + J_winding + J_shaft


def calculate_lumped_parameters(geom: GeometricParams, mat: MaterialProperties) -> LumpedParams:
    """Complete lumped model."""
    B_g, flux_per_pole = calculate_magnetic_circuit(geom, mat)
    Ra = calculate_armature_resistance(geom, mat)
    K = calculate_motor_constants(geom, flux_per_pole)
    J = calculate_rotor_inertia(geom, mat)
    La = 10 * Ra * 1e-6
    b = J * 0.01
    return LumpedParams(
        armature_resistance=Ra,
        armature_inductance=La,
        motor_constant=K,
        rotor_inertia=J,
        viscous_damping=b,
        air_gap_flux_density=B_g,
        flux_per_pole=flux_per_pole,
    )


def calculate_steady_state_performance(params: LumpedParams, op: OperatingConditions) -> dict:
    """Steady-state speed-torque characteristic."""
    K = params.motor_constant
    Ra = params.armature_resistance
    V_eff = max(0.0, op.terminal_voltage - op.brush_contact_drop_v)
    stall_torque = (V_eff * K) / Ra
    torque_range = np.linspace(0, stall_torque, 200)
    speed_rad_s = V_eff / K - (Ra / K**2) * torque_range
    speed_rpm = speed_rad_s * 60 / (2 * np.pi)
    return {
        "torque": torque_range,
        "speed_rpm": speed_rpm,
        "current": torque_range / K,
        "no_load_speed_rpm": (V_eff / K) * 60 / (2 * np.pi),
        "stall_torque": stall_torque,
        "effective_voltage": V_eff,
    }


def calculate_losses_and_efficiency(
    params: LumpedParams,
    geom: GeometricParams,
    mat: MaterialProperties,
    torque: float,
    speed_rpm: float,
) -> dict:
    """Loss breakdown and efficiency."""
    if speed_rpm < 0 or torque < 0:
        return {"p_cu": 0, "p_iron": 0, "p_mech": 0, "p_out": 0, "efficiency": 0}
    omega = speed_rpm * 2 * np.pi / 60
    current = torque / params.motor_constant if params.motor_constant > 0 else 0
    p_cu = current**2 * params.armature_resistance
    p_mech = params.viscous_damping * omega**2
    f_e = (geom.num_poles / 2) * (omega / (2 * np.pi))
    vol_rotor = (
        np.pi
        * ((geom.rotor_outer_diameter / 2) ** 2 - (geom.rotor_inner_diameter / 2) ** 2)
        * geom.stack_length
    )
    B = params.air_gap_flux_density
    p_hyst = mat.hysteresis_coeff * f_e * B**mat.steinmetz_exponent * vol_rotor
    p_eddy = mat.eddy_current_coeff * (f_e * B * mat.lamination_thickness) ** 2 * vol_rotor
    p_iron = p_hyst + p_eddy
    p_out = torque * omega
    p_in = p_out + p_cu + p_mech + p_iron
    eff = p_out / p_in if p_in > 0 else 0.0
    return {"p_cu": p_cu, "p_iron": p_iron, "p_mech": p_mech, "p_out": p_out, "efficiency": eff}


def plot_efficiency_map(
    params: LumpedParams,
    geom: GeometricParams,
    mat: MaterialProperties,
    op_conditions: OperatingConditions,
    steady_state_data: dict,
    target_torque: Optional[float] = None,
    target_speed_rpm: Optional[float] = None,
):
    """2-D efficiency contour map."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib required") from e
    torque_max = steady_state_data["stall_torque"]
    speed_max = steady_state_data["no_load_speed_rpm"]
    V_eff = steady_state_data.get(
        "effective_voltage", op_conditions.terminal_voltage - op_conditions.brush_contact_drop_v
    )
    torque_grid = np.linspace(0.01, torque_max, 50)
    speed_grid = np.linspace(0.01, speed_max, 50)
    T, S = np.meshgrid(torque_grid, speed_grid)
    Eff = np.zeros_like(T)
    K = params.motor_constant
    Ra = params.armature_resistance
    for i in range(T.shape[0]):
        for j in range(T.shape[1]):
            max_t = (K**2 / Ra) * (V_eff / K - S[i, j] * 2 * np.pi / 60)
            if T[i, j] <= max_t and max_t > 0:
                d = calculate_losses_and_efficiency(params, geom, mat, T[i, j], S[i, j])
                Eff[i, j] = d["efficiency"]
            else:
                Eff[i, j] = np.nan
    fig, ax = plt.subplots(figsize=(10, 6))
    cf = ax.contourf(T, S, Eff * 100, levels=np.arange(0, 101, 5), cmap="viridis")
    fig.colorbar(cf, ax=ax, label="Efficiency (%)")
    ax.plot(
        steady_state_data["torque"],
        steady_state_data["speed_rpm"],
        "r--",
        linewidth=2,
        label="Operating Envelope",
    )
    if target_torque is not None and target_speed_rpm is not None:
        max_t_at_target = (K**2 / Ra) * (V_eff / K - target_speed_rpm * 2 * np.pi / 60)
        in_env = target_torque <= max_t_at_target and max_t_at_target > 0
        color = "lime" if in_env else "red"
        ax.plot(target_torque, target_speed_rpm, "*", color=color, markersize=16)
    ax.set_xlabel("Torque (Nm)")
    ax.set_ylabel("Speed (RPM)")
    ax.set_title("Motor Efficiency Map")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend()
    fig.tight_layout()
    return fig


class PMSMParams:
    """Container for PMSM parameters."""

    def __init__(self, p: int, Ld: float, Lq: float, psi_m: float, Rs: float = 0.0, J: float = 0.0):
        self.p = p
        self.Ld = Ld
        self.Lq = Lq
        self.psi_m = psi_m
        self.Rs = Rs
        self.J = J

    @property
    def is_spm(self) -> bool:
        """True if surface-mount (Ld ≈ Lq)."""
        return bool(np.isclose(self.Ld, self.Lq, rtol=0.05))


def back_emf(omega_e: float, psi_m: float) -> float:
    """Peak phase back-EMF."""
    return omega_e * psi_m


def torque(params: PMSMParams, id: float, iq: float) -> float:
    """Electromagnetic torque."""
    T_excitation = params.psi_m * iq
    T_reluctance = (params.Ld - params.Lq) * id * iq
    return 1.5 * params.p * (T_excitation + T_reluctance)


def dq_currents(params: PMSMParams, omega_e: float, Vd: float, Vq: float) -> tuple[float, float]:
    """Steady-state dq currents."""
    A = np.array([[params.Rs, -omega_e * params.Lq], [omega_e * params.Ld, params.Rs]])
    b = np.array([Vd, Vq - omega_e * params.psi_m])
    id_, iq_ = np.linalg.solve(A, b)
    return float(id_), float(iq_)


class SPM:
    """Surface-Mount PMSM motor profile."""

    def __init__(self, phi_m: float, ld: float, pp: int, Vb: float, Ib: float):
        self.phi_m = phi_m
        self.sal = 0
        self.ld = ld
        self.Vb = Vb
        self.Ib = Ib
        self.Pb = 1.5 * Vb * Ib
        self.pp = pp
        self.speed: list[float] = []
        self.torque: list[float] = []
        self.voltage: list[float] = []
        self.gamma: list[float] = []
        self.power: list[float] = []
        self.valid = 0

    def validate(self) -> bool:
        """Check parameter validity."""
        self.valid = 1 if self.sal == 0 else 0
        return self.valid == 1

    def motor_profile(self) -> None:
        """Compute torque-speed profile."""
        self.speed = []
        self.torque = []
        self.voltage = []
        self.gamma = []
        self.power = []
        gamma_deg = 0
        gamma = 0.0
        omega = 0.0
        v = 0.0
        v_lim = self.Vb / 1.732
        while v < v_lim:
            v = (
                omega
                * self.pp
                * np.sqrt(
                    (self.phi_m - self.Ib * np.sin(gamma) * self.ld) ** 2
                    + (self.Ib * self.ld * np.cos(gamma)) ** 2
                )
            )
            t = 1.5 * self.pp * self.phi_m * self.Ib * np.cos(gamma)
            p = t * omega
            omega += 0.1
            self.speed.append(omega * 30 / np.pi)
            self.voltage.append(v)
            self.gamma.append(gamma_deg)
            self.torque.append(t)
            self.power.append(p)
        for gamma_deg in range(1, 85):
            gamma = gamma_deg * np.pi / 180
            omega = (v_lim) / (
                self.pp
                * np.sqrt(
                    (self.phi_m - self.Ib * np.sin(gamma) * self.ld) ** 2
                    + (self.Ib * self.ld * np.cos(gamma)) ** 2
                )
            )
            t = 1.5 * self.pp * self.Ib * self.phi_m * np.cos(gamma)
            p = t * omega
            self.speed.append(omega * 30 / np.pi)
            self.voltage.append(v)
            self.gamma.append(gamma_deg)
            self.torque.append(t)
            self.power.append(p)
