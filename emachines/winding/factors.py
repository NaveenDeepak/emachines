"""
Winding factor calculations.

Covers pitch factor (kp), distribution factor (kd), and combined
winding factor kw = kp · kd for integer-slot windings, and the
star-of-slots phasor method for all winding types including FSCW.

References:
    Hanselman, D.C. (2003). Brushless Permanent Magnet Motor Design. 2nd ed.
    Pyrhönen, J., Jokinen, T., Hrabovcová, V. (2008). Design of Rotating
        Electrical Machines. Wiley.
    Müller, G., Vogt, K., Ponick, B. (2008). Berechnung elektrischer
        Maschinen. Wiley-VCH.
"""

import numpy as np

from .sos import winding_factor_sos

__all__ = ["pitch_factor", "distribution_factor", "winding_factor"]


def pitch_factor(nu: int, coil_span: int, pole_pitch: float) -> float:
    r"""
    Pitch (chording) factor kp for the ν-th harmonic.

    .. math::
        k_{p\nu} = \left|\sin\!\left(\nu \cdot \frac{\pi}{2}
                   \cdot \frac{y}{\tau_p}\right)\right|

    Parameters
    ----------
    nu         : int    Harmonic order ν (1 = fundamental)
    coil_span  : int    Coil span in slots (y)
    pole_pitch : float  Pole pitch in slots (τp = Q / P = Q / (2p))

    Returns
    -------
    float   Pitch factor kp ∈ [0, 1]

    Notes
    -----
    ``pole_pitch`` is the **standard** pole pitch τp = Q/P (one magnetic
    pole), not the electrical cycle Q/p.  Full-pitch coil: coil_span = pole_pitch → kp1 = 1.

    References
    ----------
    Hanselman (2003), eq. 4.5
    """
    return float(np.abs(np.sin(nu * np.pi / 2 * coil_span / pole_pitch)))


def distribution_factor(nu: int, Q: int, p: int, m: int = 3) -> float:
    r"""
    Distribution (belt) factor kd for the ν-th harmonic.

    Valid for integer-slot windings (q = Q/(2mp) ≥ 1). For FSCW (q < 1)
    use :func:`winding_factor` which dispatches automatically to the
    star-of-slots phasor method.

    .. math::
        k_{d\nu} = \frac{\sin(\nu \cdot \pi / (2m))}
                        {q \cdot \sin(\nu \cdot \pi / (2mq))}

    Parameters
    ----------
    nu : int   Harmonic order ν
    Q  : int   Total number of slots
    p  : int   Number of pole pairs
    m  : int   Number of phases (default 3)

    Returns
    -------
    float   Distribution factor kd ∈ (0, 1]

    Raises
    ------
    ValueError
        If q < 1. Use :func:`winding_factor` for FSCW.

    References
    ----------
    Pyrhönen et al. (2008), eq. 2.15
    """
    q = Q / (2 * m * p)
    if q < 1.0 - 1e-9:
        raise ValueError(
            f"distribution_factor() requires q ≥ 1 (integer-slot winding). "
            f"Got q = {q:.4f} (Q={Q}, p={p}, m={m}). "
            f"For FSCW use winding_factor() — it dispatches to the "
            f"star-of-slots phasor method automatically."
        )
    num = np.sin(nu * np.pi / (2 * m))
    den = q * np.sin(nu * np.pi / (2 * m * q))
    if np.abs(den) < 1e-12:
        return 1.0
    return float(np.abs(num / den))


def winding_factor(
    nu: int,
    Q: int,
    p: int,
    coil_span: int,
    m: int = 3,
) -> float:
    r"""
    Combined winding factor kw for harmonic ν.

    Dispatches automatically based on winding type:

    - **Integer-slot** (q = Q/(2mp) ≥ 1): kw = kp · kd using the
      closed-form pitch and distribution factor formulas.
    - **Fractional-slot / FSCW** (q < 1): kw computed via the
      star-of-slots phasor method (double-layer convention), which
      matches emetor.com reference values.

    Parameters
    ----------
    nu        : int   Harmonic order ν (1 = fundamental)
    Q         : int   Total number of slots
    p         : int   Number of pole pairs
    coil_span : int   Coil span in slots
                      For FSCW tooth-coils: coil_span=1 (standard).
                      For integer-slot: coil_span = Q/P for full-pitch (kp=1).
    m         : int   Number of phases (default 3)

    Returns
    -------
    float   Winding factor kw ∈ [0, 1]

    Notes
    -----
    For FSCW the double-layer configuration is used for the phasor calculation,
    consistent with the standard industry convention and emetor.com reference
    values.  To compute single-layer FSCW winding factors, call
    :func:`emachines.winding.sos.winding_factor_sos` directly with ``layers=1``.

    Examples
    --------
    >>> winding_factor(1, 24, 2, coil_span=6)   # 24s/4p, full pitch (kp=kd=1)
    1.0

    >>> winding_factor(1, 24, 2, coil_span=5)   # 24s/4p, 5/6 chording
    0.9330...

    >>> winding_factor(1, 12, 5, coil_span=1)   # 12s/10p FSCW (double-layer)
    0.9330...

    >>> winding_factor(1, 12, 4, coil_span=1)   # 12s/8p FSCW, q=1/2
    0.8660...
    """
    P = 2 * p
    pole_pitch = Q / (2 * p)  # standard pole pitch τp = Q/P
    q = Q / (2 * m * p)

    if q >= 1.0 - 1e-9:
        # Integer-slot: closed-form kp × kd
        kp = pitch_factor(nu, coil_span, pole_pitch)
        kd = distribution_factor(nu, Q, p, m)
        return kp * kd
    else:
        # Fractional-slot / FSCW: star-of-slots phasor method, double-layer
        # Double-layer with w=coil_span is the canonical FSCW convention and
        # matches emetor.com reference winding factors.
        return winding_factor_sos(nu, Q, P, m, layers=2, w=coil_span)
