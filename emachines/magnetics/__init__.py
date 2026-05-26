"""Magnetics module - Magnetic circuit analysis, iron loss models, and magnet properties.

This module provides:
- BH curve models (Fröhlich, linear) and fitting
- Iron loss models (Steinmetz, Modified Steinmetz, Bertotti)
- Electrical steel material database
- Permanent magnet (NdFeB) grade library
"""

from .magnetics import (  # BH Models; Iron Loss Models; Steel Database; Magnet Materials
    MAGNET_LIBRARY,
    SAMPLE_BH,
    SAMPLE_LOSS,
    MagnetData,
    MagnetGrade,
    SteelDatabase,
    SteelGrade,
    bertotti,
    fit_bertotti,
    fit_frolich,
    fit_loss_model,
    fit_modified_steinmetz,
    fit_steinmetz,
    frolich,
    linear_region,
    modified_steinmetz,
    steinmetz,
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
