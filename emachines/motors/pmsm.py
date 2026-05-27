"""
Permanent Magnet Synchronous Machine (PMSM) — dq-frame model.

Covers steady-state torque, power, back-EMF, and per-unit
dq-axis equations for surface-mount (SPM) and interior (IPM) variants.

References:
    Hanselman, D.C. (2003). Brushless Permanent Magnet Motor Design. 2nd ed.
    Mohan, N. (2011). Advanced Electric Drives. Wiley.
    Pyrhönen, J. et al. (2008). Design of Rotating Electrical Machines.
"""

import numpy as np


class PMSMParams:
    """
    Container for PMSM parameters.

    Attributes:
        p:      Number of pole pairs
        Ld:     d-axis inductance (H)
        Lq:     q-axis inductance (H)
        psi_m:  Permanent magnet flux linkage (Wb)
        Rs:     Stator resistance per phase (Ω)
        J:      Rotor inertia (kg·m²)
    """

    def __init__(
        self,
        p: int,
        Ld: float,
        Lq: float,
        psi_m: float,
        Rs: float = 0.0,
        J: float = 0.0,
    ):
        self.p = p
        self.Ld = Ld
        self.Lq = Lq
        self.psi_m = psi_m
        self.Rs = Rs
        self.J = J

    @property
    def is_spm(self) -> bool:
        """True if surface-mount (Ld ≈ Lq, no reluctance torque)."""
        return bool(np.isclose(self.Ld, self.Lq, rtol=0.05))


def back_emf(omega_e: float, psi_m: float) -> float:
    r"""
    Peak phase back-EMF for a PMSM.

    .. math::
        E = \omega_e \cdot \psi_m

    Args:
        omega_e: Electrical angular velocity (rad/s)
        psi_m:   PM flux linkage (Wb)

    Returns:
        Peak back-EMF (V)

    References:
        Hanselman (2003), eq. 7.3
    """
    return omega_e * psi_m


def torque(
    params: PMSMParams,
    id: float,
    iq: float,
) -> float:
    r"""
    Electromagnetic torque from dq-frame currents.

    .. math::
        T_e = \frac{3}{2} p \left[\psi_m i_q + (L_d - L_q) i_d i_q \right]

    First term: excitation (alignment) torque.
    Second term: reluctance torque (zero for SPM where Ld = Lq).

    Args:
        params: PMSMParams instance
        id:     d-axis current (A)
        iq:     q-axis current (A)

    Returns:
        Electromagnetic torque Te (N·m)

    References:
        Hanselman (2003), eq. 7.10; Mohan (2011), §5.4
    """
    T_excitation = params.psi_m * iq
    T_reluctance = (params.Ld - params.Lq) * id * iq
    return 1.5 * params.p * (T_excitation + T_reluctance)


def dq_currents(
    params: PMSMParams,
    omega_e: float,
    Vd: float,
    Vq: float,
) -> tuple[float, float]:
    r"""
    Steady-state dq currents from applied dq voltages.

    Solves the steady-state voltage equations:

    .. math::
        V_d = R_s i_d - \omega_e L_q i_q

    .. math::
        V_q = R_s i_q + \omega_e (L_d i_d + \psi_m)

    Args:
        params:  PMSMParams instance
        omega_e: Electrical angular velocity (rad/s)
        Vd:      d-axis voltage (V)
        Vq:      q-axis voltage (V)

    Returns:
        Tuple (id, iq) in amperes

    References:
        Pyrhönen et al. (2008), §7.3
    """
    Rs = params.Rs
    Ld = params.Ld
    Lq = params.Lq
    psi_m = params.psi_m
    we = omega_e

    # 2x2 linear system: [Rs, -we*Lq; we*Ld, Rs] · [id; iq] = [Vd; Vq - we*psi_m]
    A = np.array([[Rs, -we * Lq], [we * Ld, Rs]])
    b = np.array([Vd, Vq - we * psi_m])
    id_, iq_ = np.linalg.solve(A, b)
    return float(id_), float(iq_)


class SPM:
    """
    Surface-Mount Permanent Magnet (SPM) motor — torque-speed profile.

    Computes the steady-state torque, power, voltage, and current-angle
    profile across the full speed range, covering both the constant-torque
    region (voltage-limited below base speed) and the constant-voltage /
    flux-weakening region (above base speed).

    Parameters
    ----------
    phi_m : float   PM flux linkage per phase (Wb) — often derived as ke/(pp·√3)
    ld    : float   d-axis (= q-axis for SPM) inductance (H)
    pp    : int     Number of pole pairs
    Vb    : float   DC bus voltage (V); phase limit = Vb/√3
    Ib    : float   Peak phase current (A)

    Examples
    --------
    >>> ke, pp, ld, Vdc, Ipk = 0.15, 5, 78e-6, 48, 200
    >>> phi_m = ke / (pp * 1.732)
    >>> m = SPM(phi_m=phi_m, ld=ld, pp=pp, Vb=Vdc, Ib=Ipk)
    >>> m.motor_profile()
    >>> fig = m.plot_profile()

    References
    ----------
    Hanselman, D.C. (2003). Brushless Permanent Magnet Motor Design. 2nd ed.
    """

    def __init__(self, phi_m: float, ld: float, pp: int, Vb: float, Ib: float):
        self.phi_m = phi_m  # PM flux linkage (Wb)
        self.sal = 0  # saliency ratio Lq/Ld (0 for SPM = no reluctance torque)
        self.ld = ld  # d-axis inductance (H)
        self.Vb = Vb  # DC bus voltage (V)
        self.Ib = Ib  # Peak phase current (A)
        self.Pb = 1.5 * Vb * Ib  # VA rating
        self.pp = pp  # pole pairs

        # Results populated by motor_profile()
        self.speed: list[float] = []
        self.torque: list[float] = []
        self.voltage: list[float] = []
        self.current: list[float] = []
        self.gamma: list[float] = []
        self.power: list[float] = []
        self.valid: int = 0

    def validate(self) -> bool:
        """
        Check that the parameter combination supports flux-weakening.

        Returns True if the MTPA angle exists (sin_gamma ≤ 1),
        i.e. the machine can reach base speed with the given Ib and ld.
        Sets self.valid = 1 on success.
        """
        # For SPM (sal=0) the denominator vanishes; treat as always valid
        if self.sal == 0:
            self.valid = 1
            return True
        denom = 4 * self.ld * (self.sal - 1)
        if denom == 0:
            self.valid = 1
            return True
        sin_gamma = (
            -self.phi_m + np.sqrt(self.phi_m**2 + 8 * (self.ld * (self.sal - 1)) ** 2)
        ) / denom
        if sin_gamma <= 1:
            self.valid = 1
            return True
        return False

    def motor_profile(self) -> None:
        """
        Compute the torque-speed profile and populate result lists.

        Constant-torque region  (γ = 0, speed swept until V = Vb/√3)
        Flux-weakening region   (γ swept 1°→84°, speed set by voltage limit)
        """
        # Reset previous results
        self.speed = []
        self.torque = []
        self.voltage = []
        self.gamma = []
        self.power = []

        gamma_deg = 0
        gamma = 0.0
        omega = 0.0
        v = 0.0
        v_lim = self.Vb / 1.732  # phase voltage limit (V_dc / √3)

        # ── Constant-torque region ────────────────────────────────────────────
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
            self.speed.append(omega * 30 / np.pi)  # rad/s → rpm
            self.voltage.append(v)
            self.gamma.append(gamma_deg)
            self.torque.append(t)
            self.power.append(p)

        # ── Flux-weakening region ─────────────────────────────────────────────
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

    def plot_profile(self):
        """
        Four-panel Plotly figure: torque, power, voltage, and current angle
        vs speed.

        Returns
        -------
        plotly.graph_objects.Figure
        """
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except ImportError as e:
            raise ImportError("plotly is required for plot_profile()") from e

        fig = make_subplots(
            rows=4,
            cols=1,
            subplot_titles=(
                "Torque vs Speed",
                "Power vs Speed",
                "Voltage vs Speed",
                "Current Angle vs Speed",
            ),
            vertical_spacing=0.08,
            specs=[[{"secondary_y": False}]] * 4,
        )

        fig.add_trace(
            go.Scatter(
                x=self.speed,
                y=self.torque,
                mode="lines",
                name="Torque",
                line=dict(color="blue", width=2),
                hovertemplate="Speed: %{x:.1f} rpm<br>Torque: %{y:.3f} N·m<extra></extra>",
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=self.speed,
                y=self.power,
                mode="lines",
                name="Power",
                line=dict(color="green", width=2),
                hovertemplate="Speed: %{x:.1f} rpm<br>Power: %{y:.1f} W<extra></extra>",
            ),
            row=2,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=self.speed,
                y=self.voltage,
                mode="lines",
                name="Voltage",
                line=dict(color="orange", width=2),
                hovertemplate="Speed: %{x:.1f} rpm<br>Voltage: %{y:.1f} V<extra></extra>",
            ),
            row=3,
            col=1,
        )

        vb_phase = self.Vb / 1.732
        fig.add_hline(
            y=vb_phase,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Vb = {vb_phase:.1f} V",
            annotation_position="left",
            row=3,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=self.speed,
                y=self.gamma,
                mode="lines",
                name="Current Angle",
                line=dict(color="purple", width=2),
                hovertemplate="Speed: %{x:.1f} rpm<br>Angle: %{y:.1f}°<extra></extra>",
            ),
            row=4,
            col=1,
        )

        for i in range(1, 5):
            fig.update_xaxes(range=[0, 10000], row=i, col=1)

        fig.update_yaxes(title_text="Torque (N·m)", row=1, col=1)
        fig.update_yaxes(title_text="Power (W)", row=2, col=1)
        fig.update_yaxes(title_text="Voltage (V)", row=3, col=1)
        fig.update_yaxes(title_text="Angle (°)", row=4, col=1)
        fig.update_xaxes(title_text="Speed (rpm)", row=4, col=1)

        fig.update_layout(
            height=800,
            showlegend=False,
            title_text="Motor Performance Profile",
            title_x=0.5,
            font=dict(size=12),
            margin=dict(l=60, r=60, t=80, b=60),
        )
        return fig


__all__ = ["back_emf", "torque", "dq_currents", "PMSMParams", "SPM"]
