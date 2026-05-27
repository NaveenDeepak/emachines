"""
Electrical steel material database.

Provides a unified interface for loading, caching and querying
BH curve and core loss data from Voestalpine, ThyssenKrupp (PowerCore),
and SURA manufacturer datasheets.

Data files (Excel/PDF-derived pickle caches) live in the consuming
application (emdesigner). This module provides the loading API;
the data directory is passed at runtime.

References:
    Voestalpine isovac product datasheets (voestalpine.com)
    ThyssenKrupp PowerCore product datasheets (thyssenkrupp-steel.com)
    SURA electrical steel datasheets (sura.se)
"""

import functools
import os
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

__all__ = ["SteelGrade", "SteelDatabase", "SAMPLE_BH", "SAMPLE_LOSS"]


# ─────────────────────────────────────────────────────────────────────────────
# Sample data (fallback / tutorial use)
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SteelGrade:
    """
    Container for a single electrical steel grade.

    Attributes:
        name:         Grade identifier (e.g. 'ISOVAC310 50A')
        manufacturer: One of 'voestalpine', 'thyssenkrupp', 'sura'
        bh_data:      DataFrame with columns including 'field strength H [A/m]' and 'B [T]'
        loss_data:    DataFrame with columns 'frequency [Hz]', 'B [T]', 'core loss P [W/kg]'
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
        """
        Interpolate core loss at a given frequency and flux density.

        Args:
            freq: Frequency (Hz) — must match an available frequency
            B:    Flux density (T)

        Returns:
            Core loss (W/kg), interpolated from measured data

        Raises:
            ValueError: If frequency not available in dataset
        """
        if freq not in self.frequencies:
            raise ValueError(f"Frequency {freq} Hz not in dataset. Available: {self.frequencies}")
        b_col = next((c for c in ("B [T]", "J [T]") if c in self.loss_data.columns), None)
        loss_col = next(
            (c for c in ("core loss P [W/kg]", "Core Loss [W/kg]") if c in self.loss_data.columns),
            None,
        )
        if not b_col or not loss_col:
            raise ValueError("Loss data missing expected columns.")
        subset = self.loss_data[self.loss_data["frequency [Hz]"] == freq].sort_values(b_col)
        return float(np.interp(B, subset[b_col].values, subset[loss_col].values))


# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────


class SteelDatabase:
    """
    Unified loader for electrical steel manufacturer data.

    Supports Voestalpine (isovac), ThyssenKrupp (PowerCore), and SURA grades.
    Data is loaded from pickle caches (pre-processed from Excel/PDF) on first
    access and cached in memory.

    Args:
        data_dir: Path to the datasheets root directory.
                  Expected structure:
                      data_dir/
                      ├── Voelstapine Electrical Steel/*.xlsx
                      └── steel_data_cache/*.pkl

    Example:
        db = SteelDatabase("literature/datasheets")
        print(db.manufacturers)
        grade = db.load("ISOVAC310 50A")
        print(grade.frequencies)
        print(grade.loss_at(freq=400, B=1.5))
    """

    _CACHE_SUBDIR = "steel_data_cache"
    _VOEST_SUBDIR = "Voelstapine Electrical Steel"

    def __init__(self, data_dir: str):
        self._data_dir = Path(data_dir)
        self._cache_dir = self._data_dir / self._CACHE_SUBDIR
        self._voest_dir = self._data_dir / self._VOEST_SUBDIR
        self._index: dict[str, tuple[str, str]] | None = None  # grade → (manufacturer, path)

    def _build_index(self) -> dict[str, tuple[str, str]]:
        """Scan data directories and build grade → (manufacturer, path) index."""
        index: dict[str, tuple[str, str]] = {}

        # Voestalpine — Excel files
        if self._voest_dir.exists():
            for f in os.listdir(self._voest_dir):
                if f.endswith(".xlsx") and f.startswith("Simulation-data-isovac"):
                    parts = f.replace("Simulation-data-", "").replace("-voestalpine", "").split("-")
                    if len(parts) >= 2:
                        grade = f"ISOVAC{parts[0]} {parts[1]}"
                        index[grade] = ("voestalpine", str(self._voest_dir / f))

        # ThyssenKrupp + SURA — pickle caches
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
        """Grade → (manufacturer, path) mapping, built on first access."""
        if self._index is None:
            self._index = self._build_index()
        return self._index

    @property
    def grades(self) -> list[str]:
        """Sorted list of all available grade names."""
        return sorted(self.index.keys())

    @property
    def manufacturers(self) -> dict[str, list[str]]:
        """Dict mapping manufacturer name → list of grade names."""
        result: dict[str, list[str]] = {}
        for grade, (mfr, _) in self.index.items():
            result.setdefault(mfr, []).append(grade)
        return {k: sorted(v) for k, v in result.items()}

    @functools.lru_cache(maxsize=64)
    def load(self, grade: str) -> SteelGrade:
        """
        Load a grade by name. Results are cached in memory.

        Args:
            grade: Grade name as returned by .grades

        Returns:
            SteelGrade instance

        Raises:
            KeyError: If grade is not in the database
        """
        if grade not in self.index:
            raise KeyError(f"Grade '{grade}' not found. Available: {self.grades}")

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
        """Load BH and loss DataFrames from pickle or Excel."""
        path_obj = Path(path)

        # Try pickle cache first
        if path_obj.suffix == ".pkl":
            return self._from_pickle(path_obj)

        # Check if a pickle cache exists for this Excel file
        cache_path = self._cache_dir / (path_obj.stem + ".pkl")
        if cache_path.exists():
            return self._from_pickle(cache_path)

        # Fall back to Excel
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
