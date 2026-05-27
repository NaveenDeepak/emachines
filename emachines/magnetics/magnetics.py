"""Auto-generated from multiple notebooks

Magnetics module - Tools for magnetic circuit analysis, iron loss modeling,
and permanent magnet material properties.

This module is auto-generated from Jupyter notebooks using nbdev:
  - nbs/03_bh_models.ipynb
  - nbs/03_iron_loss.ipynb
  - nbs/03_electrical_steel.ipynb
  - nbs/03_pm_materials.ipynb

To modify this module, edit the notebooks, not this file directly.
"""

from __future__ import annotations

import functools
import os
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

__all__ = [
    # BH Models
    "frolich",
    "linear_region",
    "fit_frolich",
    # Iron Loss Models
    "steinmetz",
    "modified_steinmetz",
    "bertotti",
    "fit_loss_model",
    "fit_steinmetz",
    "fit_modified_steinmetz",
    "fit_bertotti",
    # Steel Database
    "SteelGrade",
    "SteelDatabase",
    "SAMPLE_BH",
    "SAMPLE_LOSS",
    # Magnet Materials
    "MagnetGrade",
    "MagnetData",
    "MAGNET_LIBRARY",
]


def linear_region(H: np.ndarray, mu_r: float) -> np.ndarray:
    r"""
    Linear BH approximation: B = μ₀ · μr · H

    Valid for low flux densities well below saturation.

    Args:
        H: Magnetic field intensity (A/m)
        mu_r: Relative permeability

    Returns:
        Flux density B (T)
    """
    MU_0 = 4 * np.pi * 1e-7
    return MU_0 * mu_r * np.asarray(H, dtype=float)


def frolich(H: np.ndarray, a: float, b: float) -> np.ndarray:
    r"""
    Fröhlich-Kennelly analytical BH approximation.

    .. math::
        B = \frac{H}{a + b \cdot |H|}

    Simple two-parameter model. Accurate for moderate flux densities.
    Breaks down near and above saturation.

    Args:
        H: Magnetic field intensity (A/m), array-like
        a: Model parameter (dimensionless)
        b: Model parameter (m/A)

    Returns:
        Flux density B (T)

    References:
        Fröhlich (1881); see also Hanselman (2003), §3.2
    """
    H = np.asarray(H, dtype=float)
    return H / (a + b * np.abs(H))


def fit_frolich(H: np.ndarray, B: np.ndarray) -> tuple[float, float]:
    """
    Fit Fröhlich model parameters (a, b) to measured BH data.

    Args:
        H: Measured field intensity values (A/m)
        B: Measured flux density values (T)

    Returns:
        Tuple (a, b) of fitted parameters
    """
    H = np.asarray(H, dtype=float)
    B = np.asarray(B, dtype=float)
    (a, b), _ = curve_fit(frolich, H, B, p0=[1.0, 1.0], maxfev=5000)
    return float(a), float(b)


def steinmetz(
    f: float | np.ndarray,
    B_peak: float | np.ndarray,
    k: float,
    alpha: float,
    beta: float,
) -> float | np.ndarray:
    r"""
    Classical Steinmetz core loss model (per unit mass).

    .. math::
        P = k \cdot f^{\alpha} \cdot \hat{B}^{\beta}

    Valid for sinusoidal excitation.

    Args:
        f: Electrical frequency (Hz)
        B_peak: Peak flux density (T)
        k: Material constant
        alpha: Frequency exponent (typically 1.0–1.6)
        beta: Flux density exponent (typically 1.6–2.2)

    Returns:
        Core loss power density (W/kg)

    References:
        Steinmetz (1892)
    """
    return k * (np.asarray(f) ** alpha) * (np.asarray(B_peak) ** beta)


def modified_steinmetz(
    f: float | np.ndarray,
    B_peak: float | np.ndarray,
    k: float,
    alpha: float,
    beta: float,
) -> float | np.ndarray:
    r"""
    Modified Steinmetz equation (iGSE) — improved for PWM and
    non-sinusoidal waveforms.

    .. math::
        P = k \cdot f^{\alpha - 1} \cdot (f \cdot \hat{B})^{\beta}

    Args:
        f: Electrical frequency (Hz)
        B_peak: Peak flux density (T)
        k: Material constant
        alpha: Frequency exponent
        beta: Combined exponent

    Returns:
        Core loss power density (W/kg)

    References:
        Venkatachalam et al. (2002), COMPEL 21(4)
    """
    f = np.asarray(f)
    B = np.asarray(B_peak)
    return k * (f ** (alpha - 1)) * ((f * B) ** beta)


def bertotti(
    f: float | np.ndarray,
    B_peak: float | np.ndarray,
    k_h: float,
    k_e: float,
    k_a: float,
    alpha: float = 1.0,
    beta: float = 2.0,
) -> dict[str, float | np.ndarray]:
    r"""
    Bertotti three-term iron loss separation model (per unit mass).

    Separates total loss into hysteresis, classical eddy current,
    and excess (anomalous) loss components.

    Args:
        f: Electrical frequency (Hz)
        B_peak: Peak flux density (T)
        k_h: Hysteresis loss coefficient
        k_e: Eddy current loss coefficient
        k_a: Excess loss coefficient
        alpha: Frequency exponent for hysteresis (default 1.0)
        beta: Flux density exponent for hysteresis (default 2.0)

    Returns:
        Dict with keys: 'hysteresis', 'eddy', 'excess', 'total' (W/kg)

    References:
        Bertotti (1988)
    """
    f = np.asarray(f)
    B = np.asarray(B_peak)
    p_hyst = k_h * (f**alpha) * (B**beta)
    p_eddy = k_e * (f * B) ** 2
    p_exc = k_a * (f * B) ** 1.5
    return {
        "hysteresis": p_hyst,
        "eddy": p_eddy,
        "excess": p_exc,
        "total": p_hyst + p_eddy + p_exc,
    }


def _r2_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    """Return (R², RMSE) for a fit."""
    ss_res = np.sum((y_true - y_pred) ** 2)
    r2 = 1.0 - ss_res / np.sum((y_true - np.mean(y_true)) ** 2)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return float(r2), rmse


def fit_steinmetz(
    f_arr: np.ndarray,
    B_arr: np.ndarray,
    loss_arr: np.ndarray,
) -> dict:
    """Fit Classical Steinmetz parameters (k, α, β) to measured data."""

    def _func(X, k, alpha, beta):
        return steinmetz(X[0], X[1], k, alpha, beta)

    popt, _ = curve_fit(_func, (f_arr, B_arr), loss_arr, p0=[0.01, 1.5, 2.5], maxfev=10000)
    fitted = _func((f_arr, B_arr), *popt)
    r2, rmse = _r2_rmse(loss_arr, fitted)
    return {
        "k": popt[0],
        "alpha": popt[1],
        "beta": popt[2],
        "r2": r2,
        "rmse": rmse,
        "model": "Steinmetz",
    }


def fit_modified_steinmetz(
    f_arr: np.ndarray,
    B_arr: np.ndarray,
    loss_arr: np.ndarray,
) -> dict:
    """Fit Modified Steinmetz (iGSE) parameters."""

    def _func(X, k, alpha, beta):
        return modified_steinmetz(X[0], X[1], k, alpha, beta)

    popt, _ = curve_fit(_func, (f_arr, B_arr), loss_arr, p0=[0.01, 1.5, 2.0], maxfev=10000)
    fitted = _func((f_arr, B_arr), *popt)
    r2, rmse = _r2_rmse(loss_arr, fitted)
    return {
        "k": popt[0],
        "alpha": popt[1],
        "beta": popt[2],
        "r2": r2,
        "rmse": rmse,
        "model": "Modified Steinmetz",
    }


def fit_bertotti(
    f_arr: np.ndarray,
    B_arr: np.ndarray,
    loss_arr: np.ndarray,
) -> dict:
    """Fit Bertotti three-term parameters (kh, ke, ka)."""

    def _func(X, kh, ke, ka):
        return bertotti(X[0], X[1], kh, ke, ka)["total"]

    popt, _ = curve_fit(_func, (f_arr, B_arr), loss_arr, p0=[0.01, 0.0001, 0.001], maxfev=10000)
    fitted = _func((f_arr, B_arr), *popt)
    r2, rmse = _r2_rmse(loss_arr, fitted)
    return {
        "k_h": popt[0],
        "k_e": popt[1],
        "k_a": popt[2],
        "r2": r2,
        "rmse": rmse,
        "model": "Bertotti",
    }


def fit_loss_model(
    f_arr: np.ndarray,
    B_arr: np.ndarray,
    loss_arr: np.ndarray,
    model: str = "Bertotti",
) -> dict:
    """Fit a named core loss model to measured data."""
    f_arr = np.asarray(f_arr, dtype=float)
    B_arr = np.asarray(B_arr, dtype=float)
    loss_arr = np.asarray(loss_arr, dtype=float)
    if model == "Bertotti":
        return fit_bertotti(f_arr, B_arr, loss_arr)
    elif model == "Steinmetz":
        return fit_steinmetz(f_arr, B_arr, loss_arr)
    elif model == "Modified Steinmetz":
        return fit_modified_steinmetz(f_arr, B_arr, loss_arr)
    else:
        raise ValueError(f"Unknown model '{model}'")


@dataclass
class SteelGrade:
    """
    Container for a single electrical steel grade.

    Attributes:
        name:         Grade identifier (e.g. 'ISOVAC310 50A')
        manufacturer: One of 'voestalpine', 'thyssenkrupp', 'sura'
        bh_data:      DataFrame with B-H curve data
        loss_data:    DataFrame with core loss vs frequency and flux density
        source_file:  Path to the originating data file
    """

    name: str
    manufacturer: str
    bh_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    loss_data: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_file: str = ""

    @property
    def frequencies(self) -> list[float]:
        """Available frequencies in the loss dataset (Hz)."""
        if self.loss_data.empty or "frequency [Hz]" not in self.loss_data.columns:
            return []
        return sorted(self.loss_data["frequency [Hz]"].unique().tolist())

    @property
    def bh_points(self) -> int:
        """Number of B-H data points."""
        return len(self.bh_data)

    def loss_at(self, freq: float, B: float) -> float:
        """Interpolate core loss at given frequency and flux density."""
        if freq not in self.frequencies:
            raise ValueError(f"Frequency {freq} Hz not available. Available: {self.frequencies}")
        b_col = next((c for c in ("B [T]", "J [T]") if c in self.loss_data.columns), None)
        loss_col = next(
            (c for c in ("core loss P [W/kg]", "Core Loss [W/kg]") if c in self.loss_data.columns),
            None,
        )
        if not b_col or not loss_col:
            raise ValueError("Loss data missing expected columns.")
        subset = self.loss_data[self.loss_data["frequency [Hz]"] == freq].sort_values(b_col)
        return float(np.interp(B, subset[b_col].values, subset[loss_col].values))


SAMPLE_BH: dict = {
    "M-19 Steel": {
        "H (A/m)": [0, 50, 100, 150, 200, 300, 400, 500, 1000, 1500, 2000, 3000, 4000, 5000],
        "B (T)": [0, 0.6, 1.0, 1.2, 1.3, 1.4, 1.45, 1.5, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85],
    },
    "M-36 Steel": {
        "H (A/m)": [0, 40, 80, 120, 160, 240, 320, 400, 800, 1200, 1600, 2400, 3200, 4000],
        "B (T)": [0, 0.5, 0.9, 1.1, 1.2, 1.3, 1.35, 1.4, 1.5, 1.55, 1.6, 1.65, 1.7, 1.75],
    },
}


SAMPLE_LOSS: dict = {
    "M-19 Steel": pd.DataFrame(
        {
            "Frequency (Hz)": [60, 60, 60, 60, 400, 400, 400, 400],
            "Flux Density (T)": [0.5, 1.0, 1.5, 1.7, 0.5, 1.0, 1.5, 1.7],
            "Core Loss (W/kg)": [0.4, 1.0, 1.8, 2.5, 4.0, 12.0, 25.0, 35.0],
        }
    ),
    "M-36 Steel": pd.DataFrame(
        {
            "Frequency (Hz)": [60, 60, 60, 60, 400, 400, 400, 400],
            "Flux Density (T)": [0.5, 1.0, 1.5, 1.7, 0.5, 1.0, 1.5, 1.7],
            "Core Loss (W/kg)": [0.5, 1.2, 2.2, 3.0, 5.0, 15.0, 30.0, 42.0],
        }
    ),
}


class SteelDatabase:
    """Unified loader for electrical steel manufacturer data."""

    _CACHE_SUBDIR = "steel_data_cache"
    _VOEST_SUBDIR = "Voelstapine Electrical Steel"

    def __init__(self, data_dir: str):
        self._data_dir = Path(data_dir)
        self._cache_dir = self._data_dir / self._CACHE_SUBDIR
        self._voest_dir = self._data_dir / self._VOEST_SUBDIR
        self._index: dict[str, tuple[str, str]] | None = None

    def _build_index(self) -> dict[str, tuple[str, str]]:
        """Scan data directories and build grade index."""
        index: dict[str, tuple[str, str]] = {}

        if self._voest_dir.exists():
            for f in os.listdir(self._voest_dir):
                if f.endswith(".xlsx") and f.startswith("Simulation-data-isovac"):
                    parts = f.replace("Simulation-data-", "").replace("-voestalpine", "").split("-")
                    if len(parts) >= 2:
                        grade = f"ISOVAC{parts[0]} {parts[1]}"
                        index[grade] = ("voestalpine", str(self._voest_dir / f))

        if self._cache_dir.exists():
            for f in os.listdir(self._cache_dir):
                if not f.endswith(".pkl"):
                    continue
                pkl_path = str(self._cache_dir / f)
                try:
                    with open(pkl_path, "rb") as fh:
                        data = pickle.load(fh)
                    grade = data.get("grade")
                    if not grade:
                        continue
                    if "powercore" in f.lower():
                        index[grade] = ("thyssenkrupp", pkl_path)
                    elif f.lower().startswith("sura_"):
                        index[grade] = ("sura", pkl_path)
                except Exception:
                    pass

        return index

    @property
    def index(self) -> dict[str, tuple[str, str]]:
        """Grade → (manufacturer, path) mapping."""
        if self._index is None:
            self._index = self._build_index()
        return self._index

    @property
    def grades(self) -> list[str]:
        """Sorted list of available grades."""
        return sorted(self.index.keys())

    @property
    def manufacturers(self) -> dict[str, list[str]]:
        """Manufacturer → grades mapping."""
        result: dict[str, list[str]] = {}
        for grade, (mfr, _) in self.index.items():
            result.setdefault(mfr, []).append(grade)
        return {k: sorted(v) for k, v in result.items()}

    @functools.lru_cache(maxsize=64)
    def load(self, grade: str) -> SteelGrade:
        """Load a grade by name."""
        if grade not in self.index:
            raise KeyError(f"Grade '{grade}' not found")
        mfr, path = self.index[grade]
        bh_df, loss_df = self._load_file(path)
        return SteelGrade(
            name=grade,
            manufacturer=mfr,
            bh_data=bh_df,
            loss_data=loss_df,
            source_file=path,
        )

    def _load_file(self, path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load BH and loss DataFrames."""
        path_obj = Path(path)
        if path_obj.suffix == ".pkl":
            return self._from_pickle(path_obj)
        cache_path = self._cache_dir / (path_obj.stem + ".pkl")
        if cache_path.exists():
            return self._from_pickle(cache_path)
        return self._from_excel(path_obj)

    @staticmethod
    def _from_pickle(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        with open(path, "rb") as f:
            d = pickle.load(f)
        return d.get("bh_data", pd.DataFrame()), d.get("loss_data", pd.DataFrame())

    @staticmethod
    def _from_excel(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        mu0 = 4 * np.pi * 1e-7
        try:
            xls = pd.ExcelFile(path, engine="openpyxl")
            sheet = next(
                (n for n in xls.sheet_names if n.lower() in ("simulation data", "datasheet")),
                None,
            )
            if sheet is None:
                return pd.DataFrame(), pd.DataFrame()
            df = pd.read_excel(path, sheet_name=sheet, header=1, engine="openpyxl")
            df = df[:-2].dropna(subset=["grade"])
            bh = df[df["frequency [Hz]"] == 0].copy()
            loss = df[df["frequency [Hz]"] > 0].copy()
            for part in (bh, loss):
                if part.empty:
                    continue
                if "permeability µr [1]" in part.columns:
                    part["B [T]"] = (
                        part["permeability µr [1]"] * mu0 * part["field strength H [A/m]"]
                    )
                else:
                    part["B [T]"] = (
                        mu0 * part["field strength H [A/m]"] + part["polarisation J [T]"]
                    )
            return bh, loss
        except Exception:
            return pd.DataFrame(), pd.DataFrame()


@dataclass
class MagnetGrade:
    """
    Room-temperature properties of a permanent magnet grade.

    Attributes:
        grade:     Grade designation (e.g. 'N42', 'N38H')
        br:        Remanence at 20 °C (T)
        hcb:       Normal coercivity at 20 °C (kA/m)
        hcj:       Intrinsic coercivity at 20 °C (kA/m)
        alpha_br:  Temperature coefficient of Br (%/°C)
        alpha_hcj: Temperature coefficient of Hcj (%/°C)
    """

    grade: str
    br: float
    hcb: float
    hcj: float
    alpha_br: float
    alpha_hcj: float


MAGNET_LIBRARY: dict[str, MagnetGrade] = {
    # N-series (Tmax 80°C)
    "N35": MagnetGrade("N35", 1.190, 868, 955, -0.12, -0.60),
    "N38": MagnetGrade("N38", 1.235, 899, 955, -0.12, -0.60),
    "N40": MagnetGrade("N40", 1.275, 923, 955, -0.12, -0.60),
    "N42": MagnetGrade("N42", 1.305, 947, 955, -0.12, -0.60),
    "N45": MagnetGrade("N45", 1.350, 955, 955, -0.12, -0.60),
    "N48": MagnetGrade("N48", 1.400, 955, 955, -0.12, -0.60),
    "N50": MagnetGrade("N50", 1.420, 955, 955, -0.12, -0.60),
    "N52": MagnetGrade("N52", 1.455, 836, 876, -0.12, -0.60),
    "N55": MagnetGrade("N55", 1.485, 836, 876, -0.12, -0.60),
    # M-series (Tmax 100°C)
    "N35M": MagnetGrade("N35M", 1.190, 868, 1114, -0.12, -0.55),
    "N38M": MagnetGrade("N38M", 1.235, 899, 1114, -0.12, -0.55),
    "N40M": MagnetGrade("N40M", 1.275, 923, 1114, -0.12, -0.55),
    "N42M": MagnetGrade("N42M", 1.305, 947, 1114, -0.12, -0.55),
    "N45M": MagnetGrade("N45M", 1.350, 955, 1114, -0.12, -0.55),
    "N48M": MagnetGrade("N48M", 1.380, 955, 1114, -0.12, -0.55),
    "N50M": MagnetGrade("N50M", 1.410, 955, 1114, -0.12, -0.55),
    # H-series (Tmax 120°C)
    "N30H": MagnetGrade("N30H", 1.110, 836, 1353, -0.12, -0.50),
    "N33H": MagnetGrade("N33H", 1.150, 868, 1353, -0.12, -0.50),
    "N35H": MagnetGrade("N35H", 1.190, 899, 1353, -0.12, -0.50),
    "N38H": MagnetGrade("N38H", 1.235, 923, 1353, -0.12, -0.50),
    "N40H": MagnetGrade("N40H", 1.275, 947, 1353, -0.12, -0.50),
    "N42H": MagnetGrade("N42H", 1.305, 955, 1353, -0.12, -0.50),
    "N45H": MagnetGrade("N45H", 1.350, 955, 1353, -0.12, -0.50),
    "N48H": MagnetGrade("N48H", 1.380, 955, 1194, -0.12, -0.50),
    "N50H": MagnetGrade("N50H", 1.420, 975, 1114, -0.12, -0.50),
}


@dataclass
class MagnetData:
    """
    Temperature-corrected demagnetization curves for a permanent magnet.

    Parameters:
        grade:         Grade label (e.g. 'N42')
        from_standard: Data source label (e.g. 'Arnold Magnetics')
        temperature_C: Operating temperature (°C)
        T_max:         Maximum rated temperature (°C)
        Br:            Remanence at 20 °C (T)
        Hcj:           Intrinsic coercivity at 20 °C (A/m, positive)
        alpha_br:      Br temperature coefficient (%/°C)
        alpha_hcj:     Hcj temperature coefficient (%/°C)

    Call calculate_JH() first to populate curve arrays, then access B, J arrays.
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
        self, H: np.ndarray, Br_temp: float, Hcj_temp: float, k1: float = -6e-5
    ) -> tuple[np.ndarray, np.ndarray]:
        """Exponential J-H model for NdFeB magnets."""
        u0 = 4 * np.pi * 1e-7
        ur = 1.05
        k2 = np.log(Br_temp + (ur - 1) * u0 * Hcj_temp) / k1 - Hcj_temp
        J2 = np.exp(k1 * (k2 + H))
        J_cal = Br_temp + u0 * (ur - 1) * H - J2
        B_cal = Br_temp + u0 * ur * H - J2
        return J_cal, B_cal
