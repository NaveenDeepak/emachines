"""Tests for the electrical steel database and SteelGrade."""

import numpy as np
import pandas as pd
import pytest

from emachines.magnetics.electrical_steel import SAMPLE_BH, SAMPLE_LOSS, SteelDatabase, SteelGrade

# ─── Sample data tests ────────────────────────────────────────────────────────


def test_sample_bh_has_expected_grades():
    assert "M-19 Steel" in SAMPLE_BH
    assert "M-36 Steel" in SAMPLE_BH


def test_sample_loss_has_expected_grades():
    assert "M-19 Steel" in SAMPLE_LOSS
    assert "M-36 Steel" in SAMPLE_LOSS


def test_sample_bh_arrays_same_length():
    for grade, d in SAMPLE_BH.items():
        assert len(d["H (A/m)"]) == len(d["B (T)"]), f"{grade}: H and B arrays length mismatch"


def test_sample_loss_is_dataframe():
    for grade, df in SAMPLE_LOSS.items():
        assert isinstance(df, pd.DataFrame)
        assert "Frequency (Hz)" in df.columns
        assert "Core Loss (W/kg)" in df.columns


# ─── SteelGrade tests ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_grade():
    """SteelGrade with synthetic data."""
    bh = pd.DataFrame(
        {
            "field strength H [A/m]": [0, 100, 500, 1000, 5000],
            "B [T]": [0.0, 0.8, 1.2, 1.5, 1.8],
        }
    )
    loss = pd.DataFrame(
        {
            "frequency [Hz]": [50, 50, 50, 400, 400, 400],
            "B [T]": [0.5, 1.0, 1.5, 0.5, 1.0, 1.5],
            "core loss P [W/kg]": [0.5, 1.2, 2.5, 4.0, 12.0, 28.0],
        }
    )
    return SteelGrade(name="TEST-50A", manufacturer="test", bh_data=bh, loss_data=loss)


def test_grade_frequencies(mock_grade):
    assert mock_grade.frequencies == [50.0, 400.0]


def test_grade_bh_points(mock_grade):
    assert mock_grade.bh_points == 5


def test_grade_loss_at_interpolation(mock_grade):
    """Interpolated loss at 50 Hz, 1.0 T should match tabulated value."""
    assert np.isclose(mock_grade.loss_at(50, 1.0), 1.2)


def test_grade_loss_at_invalid_frequency(mock_grade):
    with pytest.raises(ValueError, match="not in dataset"):
        mock_grade.loss_at(200, 1.0)


# ─── SteelDatabase tests ─────────────────────────────────────────────────────


def test_database_empty_dir(tmp_path):
    """Database with no data files returns empty grades list."""
    db = SteelDatabase(str(tmp_path))
    assert db.grades == []
    assert db.manufacturers == {}


def test_database_load_missing_grade(tmp_path):
    """Loading a non-existent grade raises KeyError."""
    db = SteelDatabase(str(tmp_path))
    with pytest.raises(KeyError, match="not found"):
        db.load("NonExistentGrade")


def test_database_load_from_pickle(tmp_path):
    """Loading from a valid pickle file returns correct SteelGrade."""
    import pickle

    cache_dir = tmp_path / "steel_data_cache"
    cache_dir.mkdir()

    bh = pd.DataFrame(
        {
            "field strength H [A/m]": [0, 100, 1000],
            "B [T]": [0.0, 0.8, 1.5],
        }
    )
    loss = pd.DataFrame(
        {
            "frequency [Hz]": [50, 50, 400, 400],
            "B [T]": [0.5, 1.0, 0.5, 1.0],
            "core loss P [W/kg]": [0.5, 1.2, 4.0, 12.0],
        }
    )
    pkl = {"grade": "SURA M310-50A", "bh_data": bh, "loss_data": loss}

    pkl_path = cache_dir / "sura_m310-50a.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump(pkl, f)

    db = SteelDatabase(str(tmp_path))
    assert "SURA M310-50A" in db.grades
    grade = db.load("SURA M310-50A")
    assert grade.name == "SURA M310-50A"
    assert grade.bh_points == 3
    assert grade.frequencies == [50.0, 400.0]
