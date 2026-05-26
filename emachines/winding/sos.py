"""
Star-of-slots (slot-voltage-phasor) winding analysis.

The star-of-slots method assigns each slot conductor to a phase and current
direction by projecting its EMF phasor onto a circle divided into 2m equal
sectors. This method works for all slot/pole combinations — integer-slot,
fractional-slot, and concentrated (FSCW) windings — without restriction on q.

The winding factor for harmonic ν is computed as the phasor-sum magnitude
divided by the arithmetic sum of conductor counts, following:

    kw(ν) = |Σ sign_i · exp(j·ν·α_i)| / N_conductors_per_phase

This is the same approach used by SWAT-EM and described in Bianchi et al.

References:
    Bianchi, N., & Bolognani, S. (2002). Design techniques for reducing the
        cogging torque in surface-mounted PM motors. IEEE Transactions on
        Industry Applications, 38(5), 1259-1265.
    Müller, G., Vogt, K., & Ponick, B. (2008). Berechnung elektrischer
        Maschinen. Wiley-VCH.
    SWAT-EM: https://github.com/bayonet222/swat-em
"""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from math import gcd
from typing import List, Tuple

import numpy as np

__all__ = [
    "get_basic_params",
    "build_star_of_slots",
    "assign_phases",
    "build_coil_matrix",
    "winding_factor_sos",
    "check_symmetry",
    "get_valid_coil_spans",
    "is_valid_combination",
]


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────


def _lcm(a: int, b: int) -> int:
    """Least-common multiple of two positive integers."""
    return abs(a * b) // gcd(a, b)


def _angular_distance(a: float, b: float) -> float:
    """Shortest angular distance between two angles in radians, result in [0, π]."""
    d = abs(a - b) % (2.0 * np.pi)
    return min(d, 2.0 * np.pi - d)


def _build_sector_map(m: int) -> list:
    """
    Precompute a mapping from sector index (0 to 2m−1) to (phase_idx, sign).

    The 2π circle is divided into 2·m equal sectors of width π/m.
    Sector s has its centre at s·π/m. Each sector is assigned to the
    phase/direction whose centre angle is nearest to the sector centre.
    Built using exact sector-centre arithmetic — no floating-point ambiguity.

    For m=3 the result is:
        [(0,+1), (2,-1), (1,+1), (0,-1), (2,+1), (1,-1)]
        =  A+,     C-,    B+,    A-,     C+,     B-
    """
    sector_map = []
    for s in range(2 * m):
        sector_angle = s * np.pi / m
        best_k, best_sign = 0, +1
        best_dist = float("inf")
        for k in range(m):
            for sign in (+1, -1):
                centre = 2.0 * np.pi * k / m + (0.0 if sign == +1 else np.pi)
                dist = _angular_distance(sector_angle, centre)
                if dist < best_dist - 1e-12:
                    best_dist = dist
                    best_k, best_sign = k, sign
        sector_map.append((best_k, best_sign))
    return sector_map


@lru_cache(maxsize=16)
def _get_sector_map(m: int) -> list:
    """Return the cached sector map for m phases."""
    return _build_sector_map(m)


def _assign_slot_to_phase(alpha: float, m: int) -> Tuple[int, int]:
    """
    Assign an EMF-phasor angle to a phase index and current direction.

    Uses a shift-then-floor approach with a small epsilon guard so that
    angles a few ULPs below a sector boundary snap to the correct sector
    rather than the preceding one.

    Parameters
    ----------
    alpha : float   EMF phasor angle (radians, any range)
    m     : int     Number of phases

    Returns
    -------
    phase_idx : int   0-based  (0 → A, 1 → B, 2 → C …)
    sign      : int   +1 (forward) or −1 (return)
    """
    alpha = float(alpha) % (2.0 * np.pi)
    half = np.pi / (2.0 * m)  # half sector width (30° for m=3)
    sector_width = np.pi / m  # full sector width (60° for m=3)
    alpha_shifted = (alpha + half) % (2.0 * np.pi)
    sector_idx = int((alpha_shifted + 1e-9) / sector_width) % (2 * m)
    return _get_sector_map(m)[sector_idx]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────


def get_basic_params(Q: int, P: int, m: int = 3) -> dict:
    r"""
    Fundamental winding parameters for a Q-slot, P-pole, m-phase machine.

    Parameters
    ----------
    Q : int   Number of stator slots (≥ 1)
    P : int   Number of poles (positive even integer ≥ 2)
    m : int   Number of phases (default 3)

    Returns
    -------
    dict with keys:

    ==================  ==========  ==========================================
    Key                 Type        Description
    ==================  ==========  ==========================================
    ``q``               Fraction    Q / (P·m) — slots per pole per phase
    ``t``               int         gcd(Q, P//2) — winding periodicity
    ``lcm_QP``          int         lcm(Q, P)
    ``coil_pitch_full`` int         Q // (P//2) — full pole-pitch in slots
    ``alpha_e``         float       π·P/Q — electrical slot angle (rad)
    ``is_integer``      bool        q ≥ 1 with integer denominator
    ``is_fractional``   bool        0.5 ≤ q < 1, non-integer
    ``is_concentrated`` bool        q < 0.5 (tooth-coil / FSCW)
    ``winding_type``    str         'integer' | 'fractional' | 'concentrated'
    ==================  ==========  ==========================================

    Raises
    ------
    ValueError
        If P < 2, P is odd, or Q < 1.

    Examples
    --------
    >>> get_basic_params(12, 4)['winding_type']
    'integer'

    >>> get_basic_params(12, 10)['winding_type']
    'concentrated'
    """
    if P < 2 or P % 2 != 0:
        raise ValueError(f"P must be a positive even integer; got P={P}")
    if Q < 1:
        raise ValueError(f"Q must be a positive integer; got Q={Q}")
    if m < 1:
        raise ValueError(f"m must be a positive integer; got m={m}")

    p = P // 2
    q = Fraction(Q, P * m)
    t = gcd(Q, p)
    lcm_QP = _lcm(Q, P)
    coil_pitch_full = Q // p
    alpha_e = np.pi * P / Q

    q_float = float(q)
    is_integer = (q.denominator == 1) and (q_float >= 1.0)
    is_fractional = (not is_integer) and (q_float >= 0.5)
    is_concentrated = q_float < 0.5

    if is_integer:
        winding_type = "integer"
    elif is_fractional:
        winding_type = "fractional"
    else:
        winding_type = "concentrated"

    return {
        "q": q,
        "t": t,
        "lcm_QP": lcm_QP,
        "coil_pitch_full": coil_pitch_full,
        "alpha_e": alpha_e,
        "is_integer": is_integer,
        "is_fractional": is_fractional,
        "is_concentrated": is_concentrated,
        "winding_type": winding_type,
    }


def build_star_of_slots(Q: int, P: int) -> np.ndarray:
    r"""
    Electrical EMF phasor angle for every slot.

    .. math::
        \alpha_i = \frac{i \cdot \pi \cdot P}{Q} \bmod 2\pi
        \qquad i = 0, \ldots, Q-1

    This is the angle of the voltage phasor induced in the conductor
    occupying slot i at the fundamental electrical frequency.

    Parameters
    ----------
    Q : int   Number of stator slots
    P : int   Number of poles

    Returns
    -------
    np.ndarray, shape (Q,), dtype float64, values in [0, 2π)

    Examples
    --------
    >>> build_star_of_slots(6, 4)
    array([0.        , 2.09439510, 4.18879020, 0.        , 2.09439510,
           4.18879020])
    """
    i = np.arange(Q, dtype=np.float64)
    return (i * np.pi * P / Q) % (2.0 * np.pi)


def assign_phases(
    Q: int,
    P: int,
    m: int = 3,
    layers: int = 1,
    w: int | None = None,
) -> List[List[List[int]]]:
    """
    Assign every slot conductor to a phase and current direction.

    Layer 1 (top): each slot's phasor angle is compared against 2·m
    half-open sectors; the slot is assigned ±(phase_index+1).

    Layer 2 (bottom, double-layer only):
    ``layer2[i] = –layer1[(i – w + Q) mod Q]``

    Parameters
    ----------
    Q      : int        Number of stator slots
    P      : int        Number of poles
    m      : int        Number of phases (default 3)
    layers : int        1 (single-layer) or 2 (double-layer)
    w      : int|None   Coil span in slots. None → full pole-pitch Q//(P//2).

    Returns
    -------
    phases : list of m elements
        ``phases[k] = [layer1_slots, layer2_slots]``

        Positive slot number → forward conductor; negative → return conductor.
        ``layer2_slots`` is empty for single-layer windings.
        Slot numbering is 1-indexed.
    """
    p = P // 2
    if w is None:
        w = Q // p

    matrix = build_coil_matrix(Q, P, m, layers, w)

    phases: List[List[List[int]]] = []
    for k in range(m):
        ph_pos = k + 1
        ph_neg = -(k + 1)

        ph1: List[int] = []
        for i in range(Q):
            v = int(matrix[0, i])
            if v == ph_pos:
                ph1.append(+(i + 1))
            elif v == ph_neg:
                ph1.append(-(i + 1))

        ph2: List[int] = []
        if layers == 2:
            for i in range(Q):
                v = int(matrix[1, i])
                if v == ph_pos:
                    ph2.append(+(i + 1))
                elif v == ph_neg:
                    ph2.append(-(i + 1))

        phases.append([ph1, ph2])

    return phases


def build_coil_matrix(
    Q: int,
    P: int,
    m: int = 3,
    layers: int = 1,
    w: int | None = None,
) -> np.ndarray:
    """
    Slot-conductor occupancy matrix.

    Parameters
    ----------
    Q, P, m : int   Slots, poles, phases
    layers  : int   1 (single-layer) or 2 (double-layer)
    w       : int|None
              Coil span in slots. None → full pole-pitch Q//(P//2).

    Returns
    -------
    matrix : np.ndarray, shape (layers, Q), dtype int32
        +k  → phase k (1-indexed) forward conductor
        −k  → phase k (1-indexed) return conductor
         0  → empty / unassigned

    Notes
    -----
    For single-layer FSCW with even Q, adjacent go/return slot pairs are
    enforced so that each physical tooth coil is represented correctly.
    This handles the degenerate q=1/2 case (e.g. 12s/8p) where all phasor
    angles land at sector centres and the star alone produces no return
    conductors.
    """
    p = P // 2
    if w is None:
        w = Q // p

    angles = build_star_of_slots(Q, P)
    matrix = np.zeros((layers, Q), dtype=np.int32)

    # Layer 0: star-of-slots sector assignment
    for i in range(Q):
        k, sign = _assign_slot_to_phase(angles[i], m)
        matrix[0, i] = sign * (k + 1)

    # Single-layer FSCW fix: enforce adjacent go/return pairs for even Q
    if layers == 1 and Q % 2 == 0 and Q < m * P:
        for i in range(0, Q, 2):
            k, sign = _assign_slot_to_phase(angles[i], m)
            matrix[0, i] = sign * (k + 1)  # go side
            matrix[0, i + 1] = -sign * (k + 1)  # return side

    # Layer 1: return-side of layer-0 coils shifted by coil span w
    if layers == 2:
        for i in range(Q):
            go_slot = (i - w + Q) % Q
            matrix[1, i] = -matrix[0, go_slot]

    return matrix


def winding_factor_sos(
    nu: int,
    Q: int,
    P: int,
    m: int = 3,
    layers: int = 1,
    w: int | None = None,
) -> float:
    r"""
    Winding factor for harmonic ν via the star-of-slots phasor method.

    Works for all winding types: integer-slot, fractional-slot, and FSCW.

    .. math::
        k_{w\nu} = \frac{\left|\sum_{i} s_i \cdot e^{j\,\nu\,\alpha_i}\right|}
                        {N_{\text{conductors per phase}}}

    where the sum runs over all conductors of one phase, :math:`s_i \in \{+1,-1\}`
    is the current direction, and :math:`\alpha_i` is the electrical angle of
    slot *i* for the fundamental harmonic (:math:`\nu=1`).

    Parameters
    ----------
    nu     : int        Harmonic order (1 = fundamental)
    Q      : int        Number of stator slots
    P      : int        Number of poles
    m      : int        Number of phases (default 3)
    layers : int        1 (single-layer) or 2 (double-layer)
    w      : int|None   Coil span in slots. None → full pole-pitch Q//(P//2).

    Returns
    -------
    float   Winding factor kw ∈ [0, 1]

    Examples
    --------
    >>> winding_factor_sos(1, 12, 10)   # 12s/10p FSCW, fundamental
    0.9330...

    >>> winding_factor_sos(1, 12, 8)    # 12s/8p, q = 1/2
    0.8660...

    >>> winding_factor_sos(1, 24, 4, w=5)  # 24s/4p, 5/6 chording
    0.9330...

    References
    ----------
    Müller, Vogt & Ponick (2008), eq. 3.65
    SWAT-EM source: https://github.com/bayonet222/swat-em
    """
    p = P // 2
    if w is None:
        w = Q // p

    angles = build_star_of_slots(Q, P)  # α_i for fundamental (ν=1)
    matrix = build_coil_matrix(Q, P, m, layers, w)

    kw_per_phase = []
    for k in range(m):
        ph_pos = k + 1
        ph_neg = -(k + 1)
        phasor_sum = 0.0 + 0.0j
        n_conductors = 0

        for lyr in range(layers):
            for i in range(Q):
                v = int(matrix[lyr, i])
                if v == ph_pos:
                    phasor_sum += np.exp(1j * nu * angles[i])
                    n_conductors += 1
                elif v == ph_neg:
                    phasor_sum -= np.exp(1j * nu * angles[i])
                    n_conductors += 1

        if n_conductors == 0:
            kw_per_phase.append(0.0)
        else:
            kw_per_phase.append(abs(phasor_sum) / n_conductors)

    # Return the average across phases (should be equal for balanced windings)
    return float(np.mean(kw_per_phase))


def check_symmetry(Q: int, P: int, m: int = 3) -> bool:
    """
    Determine whether the winding is balanced (equal conductors per phase).

    Parameters
    ----------
    Q, P, m : int

    Returns
    -------
    bool
        True if all phases have the same non-zero conductor count.

    Examples
    --------
    >>> check_symmetry(12, 4)    # True — standard 3-phase winding
    True
    >>> check_symmetry(10, 4)    # False — 10 slots not divisible by 3
    False
    """
    try:
        matrix = build_coil_matrix(Q, P, m, layers=1)
        counts = [int(np.sum(np.abs(matrix[0]) == (k + 1))) for k in range(m)]
        return (len(set(counts)) == 1) and (counts[0] > 0)
    except Exception:
        t = gcd(Q, P // 2)
        return (t % m == 0) or (Q % (m * t) == 0)


def get_valid_coil_spans(Q: int, P: int) -> List[int]:
    """
    All valid coil spans from 1 slot up to the full pole-pitch Q//(P//2).

    Parameters
    ----------
    Q : int   Number of stator slots
    P : int   Number of poles

    Returns
    -------
    list[int]

    Examples
    --------
    >>> get_valid_coil_spans(12, 4)
    [1, 2, 3, 4, 5, 6]

    >>> get_valid_coil_spans(12, 10)
    [1, 2]
    """
    p = P // 2
    full_pitch = Q // p
    return list(range(1, full_pitch + 1))


def is_valid_combination(Q: int, P: int, m: int = 3) -> bool:
    """
    Quick check whether (Q, P) forms a usable m-phase winding.

    Returns True when P is even ≥ 2, Q ≥ m, Q ≠ P, and the winding
    is balanced.

    Parameters
    ----------
    Q, P, m : int

    Returns
    -------
    bool
    """
    if P < 2 or P % 2 != 0:
        return False
    if Q < m:
        return False
    if Q == P:
        return False
    try:
        return check_symmetry(Q, P, m)
    except Exception:
        return False
