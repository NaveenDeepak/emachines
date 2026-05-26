"""
Permanent Magnet DC Motor — lumped-parameter model.

Covers magnetic circuit analysis, armature resistance, motor constants,
rotor inertia, steady-state torque-speed performance, and loss/efficiency
calculation for brushed PMDC machines.

References
----------
Hanselman, D.C. (2003). Brushless Permanent Magnet Motor Design. 2nd ed.
Chapman, S.J. (2011). Electric Machinery Fundamentals. 5th ed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

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
]


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class GeometricParams:
    """Geometric dimensions of the motor (SI units — metres, radians)."""

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
    armature_wire_cross_section_m2: float  # conductor area from AWG table
    is_lap_winding: bool = True


@dataclass
class MaterialProperties:
    """Material properties for motor components."""

    copper_resistivity: float  # Ω·m
    steel_permeability: float  # H/m  (μ_r · μ_0)
    magnet_remanent_flux_density: float  # T
    magnet_recoil_permeability: float  # H/m  (μ_rec · μ_0)
    steel_density: float  # kg/m³
    copper_density: float  # kg/m³
    shaft_density: float  # kg/m³
    # Iron loss coefficients (Steinmetz model)
    hysteresis_coeff: float
    steinmetz_exponent: float
    eddy_current_coeff: float
    lamination_thickness: float  # m


@dataclass
class OperatingConditions:
    """Terminal operating conditions."""

    terminal_voltage: float  # V
    brush_contact_drop_v: float = 1.0  # Total constant brush contact drop (V)
    brush_resistance_total: float = 0.05  # Total brush body resistance (Ω)


@dataclass
class LumpedParams:
    """Calculated lumped-parameter motor model."""

    armature_resistance: float  # Ω
    armature_inductance: float  # H
    motor_constant: float  # Nm/A = V/(rad/s)  (Kt = Ke in SI)
    rotor_inertia: float  # kg·m²
    viscous_damping: float  # N·m·s/rad
    air_gap_flux_density: float  # T
    flux_per_pole: float  # Wb


# ─────────────────────────────────────────────────────────────────────────────
# Calculation functions
# ─────────────────────────────────────────────────────────────────────────────


def calculate_carter_coefficient(g: float, w_so: float, slot_pitch: float) -> float:
    """
    Carter's coefficient — accounts for armature slotting on effective air gap.

    Parameters
    ----------
    g          : physical air-gap length (m)
    w_so       : slot opening width (m)
    slot_pitch : armature slot pitch (m)

    Returns
    -------
    k_c : float  Carter coefficient (≥ 1)
    """
    gamma = (w_so / g) ** 2 / (5 + w_so / g)
    k_c = slot_pitch / (slot_pitch - gamma * g)
    return max(k_c, 1.0)


def calculate_magnetic_circuit(
    geom: GeometricParams, mat: MaterialProperties
) -> tuple[float, float]:
    """
    Simplified lumped-parameter magnetic circuit analysis.

    Models the circuit as a series reluctance network:
    PM → air gap (×2) → stator yoke → rotor core.

    Parameters
    ----------
    geom : GeometricParams
    mat  : MaterialProperties

    Returns
    -------
    (air_gap_flux_density, flux_per_pole) : tuple[float, float]  (T, Wb)
    """
    mu_0 = 4 * np.pi * 1e-7

    # Air gap
    pole_face_area = (
        geom.magnet_arc_angle_deg / 360 * np.pi * geom.rotor_outer_diameter * geom.stack_length
    )
    slot_pitch = np.pi * geom.rotor_outer_diameter / geom.num_armature_slots
    k_c = calculate_carter_coefficient(geom.air_gap_length, geom.slot_opening_width, slot_pitch)
    effective_gap = geom.air_gap_length * k_c
    R_gap = effective_gap / (mu_0 * pole_face_area)

    # Permanent magnet
    magnet_area = (
        geom.magnet_arc_angle_deg
        / 360
        * np.pi
        * (geom.stator_inner_diameter - geom.magnet_thickness)
        * geom.stack_length
    )
    R_magnet = geom.magnet_thickness / (mat.magnet_recoil_permeability * magnet_area)

    # Stator yoke
    yoke_t = (geom.stator_outer_diameter - geom.stator_inner_diameter) / 2 - geom.magnet_thickness
    R_stator = (
        np.pi
        * (geom.stator_outer_diameter - yoke_t)
        / geom.num_poles
        / (mat.steel_permeability * yoke_t * geom.stack_length)
    )

    # Rotor core
    core_t = (geom.rotor_outer_diameter - geom.rotor_inner_diameter) / 2
    R_rotor = (
        np.pi
        * (geom.rotor_inner_diameter + core_t)
        / geom.num_poles
        / (mat.steel_permeability * core_t * geom.stack_length)
    )

    # PM MMF
    mmf = (
        mat.magnet_remanent_flux_density / mat.magnet_recoil_permeability
    ) * geom.magnet_thickness
    R_total = R_magnet + 2 * R_gap + R_stator + R_rotor

    flux_per_pole = mmf / R_total
    B_gap = flux_per_pole / pole_face_area
    return B_gap, flux_per_pole


def calculate_armature_resistance(geom: GeometricParams, mat: MaterialProperties) -> float:
    """
    Armature winding resistance (Ω).

    Parameters
    ----------
    geom : GeometricParams
    mat  : MaterialProperties

    Returns
    -------
    Ra : float  armature resistance (Ω)
    """
    end_winding = np.pi * (geom.rotor_outer_diameter / 2) / geom.num_poles
    mlt = 2 * geom.stack_length + end_winding
    total_conductors = 2 * geom.turns_per_coil * geom.num_armature_slots
    total_length = (total_conductors / 2) * mlt
    R_wire = mat.copper_resistivity * total_length / geom.armature_wire_cross_section_m2
    parallel_paths = geom.num_poles if geom.is_lap_winding else 2
    return R_wire / parallel_paths**2


def calculate_motor_constants(geom: GeometricParams, flux_per_pole: float) -> float:
    """
    Motor constant K = Kt = Ke (SI units: Nm/A = V·s/rad).

    Parameters
    ----------
    geom          : GeometricParams
    flux_per_pole : float  (Wb)

    Returns
    -------
    K : float
    """
    total_conductors = 2 * geom.turns_per_coil * geom.num_armature_slots
    parallel_paths = geom.num_poles if geom.is_lap_winding else 2
    return (total_conductors * geom.num_poles * flux_per_pole) / (2 * np.pi * parallel_paths)


def calculate_rotor_inertia(geom: GeometricParams, mat: MaterialProperties) -> float:
    """
    Rotor moment of inertia (kg·m²), including core, windings, and shaft.

    Parameters
    ----------
    geom : GeometricParams
    mat  : MaterialProperties

    Returns
    -------
    J : float  (kg·m²)
    """
    r_o = geom.rotor_outer_diameter / 2
    r_i = geom.rotor_inner_diameter / 2

    # Rotor core
    vol_core = np.pi * (r_o**2 - r_i**2) * geom.stack_length
    J_core = 0.5 * mat.steel_density * vol_core * (r_o**2 + r_i**2)

    # Winding approximation (15% of core)
    J_winding = J_core * 0.15

    # Shaft
    vol_shaft = np.pi * r_i**2 * geom.stack_length
    J_shaft = 0.5 * mat.shaft_density * vol_shaft * r_i**2

    return J_core + J_winding + J_shaft


def calculate_lumped_parameters(geom: GeometricParams, mat: MaterialProperties) -> LumpedParams:
    """
    Full sequence: magnetic circuit → armature → motor constant → inertia.

    Parameters
    ----------
    geom : GeometricParams
    mat  : MaterialProperties

    Returns
    -------
    LumpedParams
    """
    B_g, flux_per_pole = calculate_magnetic_circuit(geom, mat)
    Ra = calculate_armature_resistance(geom, mat)
    K = calculate_motor_constants(geom, flux_per_pole)
    J = calculate_rotor_inertia(geom, mat)
    La = 10 * Ra * 1e-6  # rough estimate: τ_e in µs
    b = J * 0.01  # rough viscous damping estimate
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
    """
    Steady-state speed-torque characteristic.

    Parameters
    ----------
    params : LumpedParams
    op     : OperatingConditions

    Returns
    -------
    dict with keys: torque, speed_rpm, current,
                    no_load_speed_rpm, stall_torque, effective_voltage
    """
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
    """
    Loss breakdown and efficiency at a single operating point.

    Parameters
    ----------
    params    : LumpedParams
    geom      : GeometricParams
    mat       : MaterialProperties
    torque    : float  (Nm)
    speed_rpm : float  (rpm)

    Returns
    -------
    dict with keys: p_cu, p_iron, p_mech, p_out, efficiency
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# Visualisation (requires matplotlib)
# ─────────────────────────────────────────────────────────────────────────────


def plot_efficiency_map(
    params: LumpedParams,
    geom: GeometricParams,
    mat: MaterialProperties,
    op_conditions: OperatingConditions,
    steady_state_data: dict,
    target_torque: float | None = None,
    target_speed_rpm: float | None = None,
):
    """
    2-D efficiency map as a matplotlib contour figure.

    Parameters
    ----------
    params, geom, mat, op_conditions : model objects
    steady_state_data : dict          output of calculate_steady_state_performance()
    target_torque     : float|None    optional target operating point (Nm)
    target_speed_rpm  : float|None    optional target operating point (rpm)

    Returns
    -------
    matplotlib.figure.Figure
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise ImportError("matplotlib is required for plot_efficiency_map()") from e

    torque_max = steady_state_data["stall_torque"]
    speed_max = steady_state_data["no_load_speed_rpm"]
    V_eff = steady_state_data.get(
        "effective_voltage",
        op_conditions.terminal_voltage - op_conditions.brush_contact_drop_v,
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
        in_env = (
            target_torque <= max_t_at_target
            and max_t_at_target > 0
            and target_speed_rpm >= 0
            and target_torque >= 0
        )
        color = "lime" if in_env else "red"
        ax.plot(
            target_torque,
            target_speed_rpm,
            "*",
            color=color,
            markersize=16,
            markeredgecolor="white",
            markeredgewidth=1,
            label=f"Target ({target_torque:.3f} Nm, {target_speed_rpm:.0f} RPM)",
        )

    ax.set_xlabel("Torque (Nm)")
    ax.set_ylabel("Speed (RPM)")
    ax.set_title("Motor Efficiency Map")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend()
    fig.tight_layout()
    return fig
