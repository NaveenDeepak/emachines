"""
Deprecated: this module has been renamed to winding_factors.py.

Kept as a compatibility shim so any code that still imports from
emachines.winding.factors continues to work. Import from
emachines.winding.winding_factors directly going forward.
"""
from .winding_factors import (  # noqa: F401
    distribution_factor,
    pitch_factor,
    winding_factor,
    winding_factor_spectrum,
)
