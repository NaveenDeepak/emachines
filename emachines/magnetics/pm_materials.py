"""
Permanent Magnet Materials — NdFeB grade database and demagnetisation curves.

Provides:
    MagnetGrade   dataclass of room-temperature magnet properties
    MAGNET_LIBRARY  dict of NdFeB grades sourced from Arnold Magnetics
    MagnetData    dataclass for temperature-dependent BH/JH curve calculation

References
----------
Arnold Magnetics NdFeB datasheet:
    https://www.arnoldmagnetics.com/products/neodymium-iron-boron-magnets/
Hanselman, D.C. (2003). Brushless Permanent Magnet Motor Design. 2nd ed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["MagnetGrade", "MAGNET_LIBRARY", "MagnetData"]


# ─────────────────────────────────────────────────────────────────────────────
# Magnet grade dataclass
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MagnetGrade:
    """
    Room-temperature properties of a permanent magnet grade.

    Attributes
    ----------
    grade     : str    Grade designation (e.g. 'N42', 'N38H')
    br        : float  Remanence at 20 °C (T)
    hcb       : float  Normal coercivity at 20 °C (kA/m)
    hcj       : float  Intrinsic coercivity at 20 °C (kA/m)
    alpha_br  : float  Temperature coefficient of Br (%/°C)
    alpha_hcj : float  Temperature coefficient of Hcj (%/°C)
    """

    grade: str
    br: float
    hcb: float
    hcj: float
    alpha_br: float
    alpha_hcj: float


# ─────────────────────────────────────────────────────────────────────────────
# NdFeB grade library  (source: Arnold Magnetics)
# ─────────────────────────────────────────────────────────────────────────────
# Br   — average of specified range (T)
# Hcb  — minimum from datasheet (kA/m)
# Hcj  — minimum from datasheet (kA/m)
# alpha_br  — -0.12 %/°C for all grades (typical)
# alpha_hcj — estimated by temperature rating:
#   N  → -0.60  M  → -0.55  H/SH/UH/EH → -0.50

MAGNET_LIBRARY: dict[str, MagnetGrade] = {
    # ── N-series  (Tmax 80 °C) ───────────────────────────────────────────────
    "N35": MagnetGrade("N35", 1.190, 868, 955, -0.12, -0.60),
    "N38": MagnetGrade("N38", 1.235, 899, 955, -0.12, -0.60),
    "N40": MagnetGrade("N40", 1.275, 923, 955, -0.12, -0.60),
    "N42": MagnetGrade("N42", 1.305, 947, 955, -0.12, -0.60),
    "N45": MagnetGrade("N45", 1.350, 955, 955, -0.12, -0.60),
    "N48": MagnetGrade("N48", 1.400, 955, 955, -0.12, -0.60),
    "N50": MagnetGrade("N50", 1.420, 955, 955, -0.12, -0.60),
    "N52": MagnetGrade("N52", 1.455, 836, 876, -0.12, -0.60),
    "N55": MagnetGrade("N55", 1.485, 836, 876, -0.12, -0.60),
    # ── M-series  (Tmax 100 °C) ──────────────────────────────────────────────
    "N35M": MagnetGrade("N35M", 1.190, 868, 1114, -0.12, -0.55),
    "N38M": MagnetGrade("N38M", 1.235, 899, 1114, -0.12, -0.55),
    "N40M": MagnetGrade("N40M", 1.275, 923, 1114, -0.12, -0.55),
    "N42M": MagnetGrade("N42M", 1.305, 947, 1114, -0.12, -0.55),
    "N45M": MagnetGrade("N45M", 1.350, 955, 1114, -0.12, -0.55),
    "N48M": MagnetGrade("N48M", 1.380, 955, 1114, -0.12, -0.55),
    "N50M": MagnetGrade("N50M", 1.410, 955, 1114, -0.12, -0.55),
    # ── H-series  (Tmax 120 °C) ──────────────────────────────────────────────
    "N30H": MagnetGrade("N30H", 1.110, 836, 1353, -0.12, -0.50),
    "N33H": MagnetGrade("N33H", 1.150, 868, 1353, -0.12, -0.50),
    "N35H": MagnetGrade("N35H", 1.190, 899, 1353, -0.12, -0.50),
    "N38H": MagnetGrade("N38H", 1.235, 923, 1353, -0.12, -0.50),
    "N40H": MagnetGrade("N40H", 1.275, 947, 1353, -0.12, -0.50),
    "N42H": MagnetGrade("N42H", 1.305, 955, 1353, -0.12, -0.50),
    "N45H": MagnetGrade("N45H", 1.350, 955, 1353, -0.12, -0.50),
    "N48H": MagnetGrade("N48H", 1.380, 955, 1194, -0.12, -0.50),
    "N50H": MagnetGrade("N50H", 1.420, 975, 1114, -0.12, -0.50),
    # ── SH-series (Tmax 150 °C) ──────────────────────────────────────────────
    "N30SH": MagnetGrade("N30SH", 1.110, 836, 1592, -0.12, -0.50),
    "N33SH": MagnetGrade("N33SH", 1.150, 868, 1592, -0.12, -0.50),
    "N35SH": MagnetGrade("N35SH", 1.190, 899, 1592, -0.12, -0.50),
    "N38SH": MagnetGrade("N38SH", 1.235, 923, 1592, -0.12, -0.50),
    "N40SH": MagnetGrade("N40SH", 1.260, 947, 1592, -0.12, -0.50),
    "N42SH": MagnetGrade("N42SH", 1.305, 955, 1433, -0.12, -0.50),
    "N45SH": MagnetGrade("N45SH", 1.350, 955, 1353, -0.12, -0.50),
    # ── UH-series (Tmax 180 °C) ──────────────────────────────────────────────
    "N28UH": MagnetGrade("N28UH", 1.060, 804, 1990, -0.12, -0.50),
    "N30UH": MagnetGrade("N30UH", 1.110, 836, 1990, -0.12, -0.50),
    "N33UH": MagnetGrade("N33UH", 1.150, 868, 1990, -0.12, -0.50),
    "N35UH": MagnetGrade("N35UH", 1.190, 899, 1990, -0.12, -0.50),
    "N38UH": MagnetGrade("N38UH", 1.235, 923, 1751, -0.12, -0.50),
    "N40UH": MagnetGrade("N40UH", 1.260, 947, 1592, -0.12, -0.50),
    # ── EH-series (Tmax 200 °C) ──────────────────────────────────────────────
    "N28EH": MagnetGrade("N28EH", 1.060, 804, 2388, -0.12, -0.50),
    "N30EH": MagnetGrade("N30EH", 1.110, 836, 2388, -0.12, -0.50),
    "N33EH": MagnetGrade("N33EH", 1.150, 868, 2388, -0.12, -0.50),
    "N35EH": MagnetGrade("N35EH", 1.190, 899, 2388, -0.12, -0.50),
    "N38EH": MagnetGrade("N38EH", 1.220, 923, 1990, -0.12, -0.50),
}


# ─────────────────────────────────────────────────────────────────────────────
# MagnetData — temperature-dependent BH / JH curve
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MagnetData:
    """
    Temperature-corrected demagnetisation curves for a permanent magnet.

    Call ``calculate_JH()`` first to populate the curve arrays, then
    ``plot_JH()`` to get a Plotly figure.

    Parameters
    ----------
    grade         : str    Grade label (e.g. 'N42')
    from_standard : str    Data source label (e.g. 'Arnold Magnetics')
    temperature_C : float  Operating temperature (°C)
    T_max         : float  Maximum rated temperature (°C)
    Br            : float  Remanence at 20 °C (T)
    Hcj           : float  Intrinsic coercivity at 20 °C (A/m, positive)
    alpha_br      : float  Br temperature coefficient (%/°C)
    alpha_hcj     : float  Hcj temperature coefficient (%/°C)

    Examples
    --------
    >>> from emachines.magnetics.pm_materials import MagnetData, MAGNET_LIBRARY
    >>> g = MAGNET_LIBRARY['N42']
    >>> m = MagnetData('N42', 'Arnold', 80, 80,
    ...                g.br, g.hcj * 1e3, g.alpha_br, g.alpha_hcj)
    >>> m.calculate_JH()
    >>> fig = m.plot_JH()
    """

    grade: str
    from_standard: str
    temperature_C: float
    T_max: float
    Br: float  # T at 20 °C
    Hcj: float  # A/m at 20 °C (positive value)
    alpha_br: float  # %/°C
    alpha_hcj: float  # %/°C

    # Arrays populated by calculate_JH()
    H: np.ndarray = field(default_factory=lambda: np.array([]))
    J: np.ndarray = field(default_factory=lambda: np.array([]))
    B: np.ndarray = field(default_factory=lambda: np.array([]))
    J_20C: np.ndarray = field(default_factory=lambda: np.array([]))
    B_20C: np.ndarray = field(default_factory=lambda: np.array([]))

    def calculate_JH(self) -> None:
        """Compute J-H and B-H curves at operating temperature and at 20 °C."""
        delta_T = self.temperature_C - 20
        beta_br = self.alpha_br * delta_T * 1e-2
        beta_hcj = self.alpha_hcj * delta_T * 1e-2

        Br_temp = self.Br * (1 + beta_br)
        Hcj_temp = self.Hcj * (1 + beta_hcj)

        self.H = np.linspace(-self.Hcj, 0, 100)
        self.J, self.B = self._jh_data(self.H, Br_temp, -Hcj_temp)
        self.J_20C, self.B_20C = self._jh_data(self.H, self.Br, -self.Hcj)

    def _jh_data(
        self,
        H: np.ndarray,
        Br_temp: float,
        Hcj_temp: float,
        k1: float = -6e-5,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Exponential J-H model for NdFeB magnets.

        Parameters
        ----------
        H        : field strength array (A/m)
        Br_temp  : temperature-corrected remanence (T)
        Hcj_temp : temperature-corrected intrinsic coercivity (A/m, negative)
        k1       : shape parameter (default -6e-5)

        Returns
        -------
        (J, B) : tuple of np.ndarray
        """
        u0 = 4 * np.pi * 1e-7
        ur = 1.05

        k2 = np.log(Br_temp + (ur - 1) * u0 * Hcj_temp) / k1 - Hcj_temp

        J2 = np.exp(k1 * (k2 + H))
        J_cal = Br_temp + u0 * (ur - 1) * H - J2
        B_cal = Br_temp + u0 * ur * H - J2
        return J_cal, B_cal

    def plot_JH(self):
        """
        Plotly demagnetisation curve figure (J-H and B-H at operating and 20 °C).

        Returns
        -------
        plotly.graph_objects.Figure
        """
        try:
            import plotly.graph_objects as go
        except ImportError as e:
            raise ImportError("plotly is required for plot_JH()") from e

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=self.H, y=self.J, mode="lines", name="J-H curve", line=dict(color="cyan"))
        )
        fig.add_trace(
            go.Scatter(
                x=self.H, y=self.B, mode="lines", name="B-H curve", line=dict(color="magenta")
            )
        )
        fig.add_trace(
            go.Scatter(
                x=self.H,
                y=self.J_20C,
                mode="lines",
                name="J-H curve (20°C)",
                line=dict(dash="dash", color="cyan"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=self.H,
                y=self.B_20C,
                mode="lines",
                name="B-H curve (20°C)",
                line=dict(dash="dash", color="magenta"),
            )
        )

        fig.update_yaxes(range=[0, 1.5])
        fig.update_xaxes(range=[-self.Hcj, 0])
        fig.update_layout(
            title=f"Magnet Properties ({round(self.temperature_C, 1)} °C)",
            xaxis_title="H (A/m)",
            yaxis_title="J, B (T)",
            legend_title="Demagnetisation Curves",
            template="plotly_dark",
        )
        return fig
