"""
Winding analysis: factors, star-of-slots, slot/pole geometry.

Modules
-------
factors
    pitch_factor, distribution_factor, winding_factor
    (integer-slot: closed-form; FSCW: auto-dispatch to star-of-slots)
sos
    build_star_of_slots, build_coil_matrix, assign_phases,
    winding_factor_sos, get_basic_params, check_symmetry,
    get_valid_coil_spans, is_valid_combination
"""

from .factors import distribution_factor, pitch_factor, winding_factor
from .sos import (
    assign_phases,
    build_coil_matrix,
    build_star_of_slots,
    check_symmetry,
    get_basic_params,
    get_valid_coil_spans,
    is_valid_combination,
    winding_factor_sos,
)

__all__ = [
    # factors
    "pitch_factor",
    "distribution_factor",
    "winding_factor",
    # sos
    "get_basic_params",
    "build_star_of_slots",
    "assign_phases",
    "build_coil_matrix",
    "winding_factor_sos",
    "check_symmetry",
    "get_valid_coil_spans",
    "is_valid_combination",
]
