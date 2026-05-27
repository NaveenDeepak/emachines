"""
Iron (core) loss models with curve fitting.

Covers the classical Steinmetz equation, the Modified Steinmetz
equation (iGSE), and Bertotti's three-term separation model.
Fitting functions wrap scipy.optimize.curve_fit for each model.

References:
    Steinmetz, C.P. (1892). On the law of hysteresis.
        AIEE Transactions, 9, 3-64.
    Bertotti, G. (1988). General properties of power losses in soft
        ferromagnetic materials. IEEE Trans. Magnetics, 24(1), 621-630.
    Venkatachalam, K. et al. (2002). Accurate prediction of ferrite core
        loss with nonsinusoidal waveforms. COMPEL, 21(4).
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import curve_fit

__all__ = [
    "steinmetz",
    "modified_steinmetz",
    "bertotti",
    "fit_steinmetz",
    "fit_modified_steinmetz",
    "fit_bertotti",
    "fit_loss_model",
    "MODEL_NAMES",
]

MODEL_NAMES = ("Bertotti", "Steinmetz", "Modified Steinmetz")


# ─────────────────────────────────────────────────────────────────────────────
# Forward models
# ─────────────────────────────────────────────────────────────────────────────


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
        f:      Electrical frequency (Hz)
        B_peak: Peak flux density (T)
        k:      Material constant
        alpha:  Frequency exponent (typically 1.0–1.6)
        beta:   Flux density exponent (typically 1.6–2.2)

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
        f:      Electrical frequency (Hz)
        B_peak: Peak flux density (T)
        k:      Material constant
        alpha:  Frequency exponent
        beta:   Combined exponent

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
    and excess (anomalous) loss components:

    .. math::
        P_{total} = \underbrace{k_h f \hat{B}^{\beta}}_{hysteresis}
                  + \underbrace{k_e (f \hat{B})^2}_{eddy}
                  + \underbrace{k_a (f \hat{B})^{1.5}}_{excess}

    Args:
        f:      Electrical frequency (Hz)
        B_peak: Peak flux density (T)
        k_h:    Hysteresis loss coefficient
        k_e:    Eddy current loss coefficient
        k_a:    Excess loss coefficient
        alpha:  Frequency exponent for hysteresis (default 1.0)
        beta:   Flux density exponent for hysteresis (default 2.0)

    Returns:
        Dict with keys: 'hysteresis', 'eddy', 'excess', 'total' (W/kg)

    References:
        Bertotti (1988), eq. 6
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


# ─────────────────────────────────────────────────────────────────────────────
# Fitting functions
# ─────────────────────────────────────────────────────────────────────────────


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
    r"""
    Fit Classical Steinmetz model parameters (k, α, β) to measured data.

    Args:
        f_arr:    Array of frequency values (Hz)
        B_arr:    Array of peak flux density values (T)
        loss_arr: Array of measured core loss values (W/kg)

    Returns:
        Dict with keys: 'k', 'alpha', 'beta', 'r2', 'rmse', 'model'
    """

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
    r"""
    Fit Modified Steinmetz (iGSE) model parameters (k, α, β).

    Args:
        f_arr:    Array of frequency values (Hz)
        B_arr:    Array of peak flux density values (T)
        loss_arr: Array of measured core loss values (W/kg)

    Returns:
        Dict with keys: 'k', 'alpha', 'beta', 'r2', 'rmse', 'model'
    """

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
    r"""
    Fit Bertotti three-term model parameters (kh, ke, ka).

    Args:
        f_arr:    Array of frequency values (Hz)
        B_arr:    Array of peak flux density values (T)
        loss_arr: Array of measured core loss values (W/kg)

    Returns:
        Dict with keys: 'k_h', 'k_e', 'k_a', 'r2', 'rmse', 'model'
    """

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
    """
    Fit a named core loss model to measured data.

    Args:
        f_arr:    Frequency values (Hz)
        B_arr:    Peak flux density values (T)
        loss_arr: Measured core loss values (W/kg)
        model:    One of 'Bertotti', 'Steinmetz', 'Modified Steinmetz'

    Returns:
        Dict of fitted coefficients plus 'r2', 'rmse', 'model'

    Raises:
        ValueError: If model name is not recognised
    """
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
        raise ValueError(f"Unknown model '{model}'. Choose from: {MODEL_NAMES}")
