"""
MEC permeability models.

Three concrete implementations are provided:

* ``LinearPermeabilityModel``  – constant μ = μ₀·μᵣ  (no saturation)
* ``SplinePermeabilityModel``  – cubic-spline fit to a B-H data set
  (integrates directly with :class:`emachines.magnetics.SteelGrade`)
* ``ShanesudhoffModel``        – analytical Shane-Sudhoff (2010) model,
  originally published for 3C90 ferrite; can be parameterised for any
  material.

All models expose the same two-method interface required by the MEC solver:

    mu(B)       → permeability [H/m]
    dmu_dB(B)   → dμ/dB       [H/m per T]

References:
    Shane, S.D. & Sudhoff, S.D. (2010). Refinements in Anhysteretic
    Characterization and Permeability Modeling. IEEE Trans. Magn., 46(11).
"""

from __future__ import annotations

import abc
from typing import Sequence

import numpy as np
from scipy.interpolate import CubicSpline

__all__ = [
    "PermeabilityModel",
    "LinearPermeabilityModel",
    "SplinePermeabilityModel",
    "ShanesudhoffModel",
]

MU0 = 4e-7 * np.pi  # H/m


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────


class PermeabilityModel(abc.ABC):
    """Abstract interface for permeability models used by the MEC solver."""

    @abc.abstractmethod
    def mu(self, B: float) -> float:
        """Return permeability μ [H/m] at flux density *B* [T]."""

    @abc.abstractmethod
    def dmu_dB(self, B: float) -> float:
        """Return dμ/dB [H/m·T⁻¹] at flux density *B* [T]."""


# ─────────────────────────────────────────────────────────────────────────────
# Linear (constant μ)
# ─────────────────────────────────────────────────────────────────────────────


class LinearPermeabilityModel(PermeabilityModel):
    """
    Constant permeability  μ = μ₀ · μᵣ.

    Parameters
    ----------
    mu_r:
        Relative permeability (dimensionless).  Default is 1 (free space).
    """

    def __init__(self, mu_r: float = 1.0) -> None:
        if mu_r <= 0:
            raise ValueError(f"mu_r must be positive, got {mu_r}")
        self._mu = MU0 * mu_r

    def mu(self, B: float) -> float:  # noqa: D102
        return self._mu

    def dmu_dB(self, B: float) -> float:  # noqa: D102
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Spline model from B-H data
# ─────────────────────────────────────────────────────────────────────────────


class SplinePermeabilityModel(PermeabilityModel):
    """
    Permeability model built from tabulated B-H data via a cubic spline.

    The data are assumed to start at (H=0, B=0).  Negative-B evaluation
    uses odd symmetry:  μ(−|B|) = μ(|B|),  dμ/dB(−|B|) = −dμ/dB(|B|).

    Parameters
    ----------
    H_data:
        Array of field strengths [A/m], monotonically increasing from 0.
    B_data:
        Corresponding flux densities [T].

    Class methods
    -------------
    from_steel_grade(grade)
        Convenience constructor that reads the ``bh_data`` DataFrame of an
        :class:`emachines.magnetics.SteelGrade` instance.
    """

    def __init__(
        self,
        H_data: Sequence[float],
        B_data: Sequence[float],
    ) -> None:
        H = np.asarray(H_data, dtype=float)
        B = np.asarray(B_data, dtype=float)

        if H.shape != B.shape:
            raise ValueError("H_data and B_data must have the same length.")
        if H[0] != 0.0 or B[0] != 0.0:
            raise ValueError("B-H data must start at (H=0, B=0).")
        if not np.all(np.diff(H) > 0):
            raise ValueError("H_data must be strictly increasing.")

        # μ(B) = μ₀ * H/B  — defined for B > 0 only
        # We build a spline of μ as a function of B so we can differentiate.
        # At B=0 we use the initial slope (μ₀·μᵣ from the linear region).
        B_pos = B[1:]  # skip (0,0) point
        H_pos = H[1:]
        mu_pos = MU0 * H_pos / B_pos

        # Prepend the B=0 point using the initial chord slope as μ(0)
        mu_at_0 = MU0 * H_pos[0] / B_pos[0]  # initial linear slope
        B_knots = np.concatenate([[0.0], B_pos])
        mu_knots = np.concatenate([[mu_at_0], mu_pos])

        self._B_max = B_knots[-1]
        self._mu_min = mu_knots[-1]

        # Build spline μ(B) — use not-a-knot boundary conditions (default)
        self._cs = CubicSpline(B_knots, mu_knots)
        self._cs_deriv = self._cs.derivative()

    @classmethod
    def from_steel_grade(cls, grade) -> "SplinePermeabilityModel":
        """
        Create a SplinePermeabilityModel from a
        :class:`emachines.magnetics.SteelGrade`.

        The DataFrame is expected to have columns whose names *contain*
        'H' and 'B' (case-insensitive substring match), e.g.
        ``'field strength H [A/m]'`` and ``'B [T]'``.
        """
        df = grade.bh_data
        # Find the H column and B column by substring match
        h_col = next(c for c in df.columns if "H" in c.upper() and "B" not in c.upper())
        b_col = next(c for c in df.columns if c.upper().startswith("B"))
        H = df[h_col].to_numpy(dtype=float)
        B = df[b_col].to_numpy(dtype=float)
        # Sort and ensure starts at origin
        order = np.argsort(H)
        H, B = H[order], B[order]
        if H[0] != 0:
            H = np.concatenate([[0.0], H])
            B = np.concatenate([[0.0], B])
        return cls(H, B)

    def mu(self, B: float) -> float:  # noqa: D102
        absB = abs(B)
        if absB >= self._B_max:
            return self._mu_min
        return float(self._cs(absB))

    def dmu_dB(self, B: float) -> float:  # noqa: D102
        absB = abs(B)
        if absB >= self._B_max:
            return 0.0
        sign = 1.0 if B >= 0 else -1.0
        return sign * float(self._cs_deriv(absB))


# ─────────────────────────────────────────────────────────────────────────────
# Shane-Sudhoff analytical model
# ─────────────────────────────────────────────────────────────────────────────


class ShanesudhoffModel(PermeabilityModel):
    """
    Shane-Sudhoff (2010) analytical permeability model.

    The model defines an auxiliary function

        f(B) = μᵣ/(μᵣ−1) + Σₙ [ aₙ·|B| + dₙ·log(eₙ + zₙ·exp(−bₙ·|B|)) ]

    where  dₙ = aₙ/bₙ,  zₙ = (γₙ − 1)/γₙ,  eₙ = 1 − zₙ  (so that
    eₙ + zₙ = 1 and log(eₙ + zₙ) = 0 at B = 0, ensuring the model
    reduces to μ = μ₀·μᵣ at the origin).

    Then:
        μ(B)      = μ₀ · f / (f − 1)
        dμ/dB(B)  = −μ₀ · sign(B) · Σ h_n / (t_n + exp(−bₙ·|B|))  /  (f−1)²

    Parameters
    ----------
    mu_r:
        Initial relative permeability.
    a, b, gamma:
        Sequences of equal length, one entry per term.
    mu0:
        Permeability of free space [H/m].  Default: 4π×10⁻⁷.

    Class methods
    -------------
    ferrite_3C90()
        Returns a ShanesudhoffModel with the 3C90 ferrite parameters from
        the MEC 3.2 toolbox example (Sudhoff, 2014).
    """

    def __init__(
        self,
        mu_r: float,
        a: Sequence[float],
        b: Sequence[float],
        gamma: Sequence[float],
        mu0: float = MU0,
    ) -> None:
        a_arr: np.ndarray = np.asarray(a, dtype=float)
        b_arr: np.ndarray = np.asarray(b, dtype=float)
        gamma_arr: np.ndarray = np.asarray(gamma, dtype=float)
        if not (len(a_arr) == len(b_arr) == len(gamma_arr)):
            raise ValueError("a, b, gamma must all have the same length.")

        self._mu_r = float(mu_r)
        self._a: np.ndarray = a_arr
        self._b: np.ndarray = b_arr
        self._mu0 = float(mu0)

        # Pre-compute derived constants (n-vectors)
        self._d: np.ndarray = a_arr / b_arr  # dₙ
        self._z: np.ndarray = (gamma_arr - 1.0) / gamma_arr  # zₙ
        self._e = 1.0 - self._z  # eₙ = 1 − zₙ (ensures log=0 at B=0)

        # For dmu/dB: h_n = mu0 * a_n / b_n * b_n = mu0 * a_n
        # Full derivation gives: h_n coefficient in numerator
        self._h: np.ndarray = self._mu0 * a_arr * self._z * b_arr  # mu0 * a_n * z_n * b_n

    # ── internal helpers ──────────────────────────────────────────────────

    def _f_and_df(self, absB: float):
        """Return (f, df/d|B|) at |B|."""
        eb = np.exp(-self._b * absB)
        # Recheck formula: log(eₙ + zₙ·exp(−bₙ|B|))
        # z_n = (γ-1)/γ,  e_n = 1 + z_n = 1/γ + ... — let's use the
        # original MEC 3.2 muB.m directly:
        #   f = mur/(mur-1) + sum( a.*abs(B) + d.*log(e + z.*exp(-b.*abs(B))) )
        arg = self._e + self._z * eb

        sum_terms = np.sum(self._a * absB + self._d * np.log(arg))
        f = self._mu_r / (self._mu_r - 1.0) + sum_terms

        # df/d|B|:  d/d|B| [a·|B|] = a
        #           d/d|B| [d·log(arg)] = d · (−z·b·exp(−b|B|)) / arg
        dlog_dabs = -self._d * self._z * self._b * eb / arg
        df = np.sum(self._a + dlog_dabs)

        return f, df

    # ── public interface ──────────────────────────────────────────────────

    def mu(self, B: float) -> float:  # noqa: D102
        absB = abs(float(B))
        f, _ = self._f_and_df(absB)
        return self._mu0 * f / (f - 1.0)

    def dmu_dB(self, B: float) -> float:  # noqa: D102
        absB = abs(float(B))
        f, df = self._f_and_df(absB)
        fm1 = f - 1.0
        # dμ/dB = μ₀ · [df/d|B|·(f−1) − f·df/d|B|] / (f−1)²
        #       = −μ₀ · df/d|B| / (f−1)²   × sign(B)
        sign = 1.0 if B >= 0 else -1.0
        return -self._mu0 * df / (fm1 * fm1) * sign

    # ── class methods ─────────────────────────────────────────────────────

    @classmethod
    def ferrite_3C90(cls) -> "ShanesudhoffModel":
        """
        3C90 ferrite parameters from MEC 3.2 toolbox (Sudhoff, 2014).

            μᵣ = 22 340.9259
            a  = [1.1542,    0.049742,  0.049644,  0.041155]
            b  = [431.1763,  2.29503,  15.04824,  74.28908]
            γ  = [0.4742,    2.7955,    0.59862,   0.43996]
        """
        return cls(
            mu_r=22340.9259,
            a=[1.1542, 0.049742, 0.049644, 0.041155],
            b=[431.1763, 2.29503, 15.04824, 74.28908],
            gamma=[0.4742, 2.7955, 0.59862, 0.43996],
        )
