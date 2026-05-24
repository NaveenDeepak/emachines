"""Magnetics module - Magnetic circuit analysis, iron loss models, and magnet properties.

This module provides:
- BH curve models (Fröhlich, linear) and fitting
- Iron loss models (Steinmetz, Modified Steinmetz, Bertotti)
- Electrical steel material database
- Permanent magnet (NdFeB) grade library
"""

from .magnetics import (
    # BH Models
    frolich,
    linear_region,
    fit_frolich,
    # Iron Loss Models
    steinmetz,
    modified_steinmetz,
    bertotti,
    fit_steinmetz,
    fit_modified_steinmetz,
    fit_bertotti,
    fit_loss_model,
    # Steel Database
    SteelGrade,
    SteelDatabase,
    SAMPLE_BH,
    SAMPLE_LOSS,
    # Magnet Materials
    MagnetGrade,
    MagnetData,
    MAGNET_LIBRARY,
)

__all__ = [
    # BH Models
    "frolich",
    "linear_region",
    "fit_frolich",
    # Iron Loss Models
    "steinmetz",
    "modified_steinmetz",
    "bertotti",
    "fit_steinmetz",
    "fit_modified_steinmetz",
    "fit_bertotti",
    "fit_loss_model",
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
