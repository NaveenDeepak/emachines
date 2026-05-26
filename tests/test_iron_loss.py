"""Tests for iron loss models and fitting functions."""

import numpy as np
import pytest

from emachines.magnetics.iron_loss import (
    MODEL_NAMES,
    bertotti,
    fit_bertotti,
    fit_loss_model,
    fit_modified_steinmetz,
    fit_steinmetz,
    modified_steinmetz,
    steinmetz,
)

# ─── Forward model tests ──────────────────────────────────────────────────────


def test_steinmetz_scales_with_frequency():
    assert steinmetz(100, 1.0, 0.01, 1.5, 2.0) > steinmetz(50, 1.0, 0.01, 1.5, 2.0)


def test_steinmetz_scales_with_flux():
    assert steinmetz(50, 1.5, 0.01, 1.5, 2.0) > steinmetz(50, 1.0, 0.01, 1.5, 2.0)


def test_modified_steinmetz_positive():
    assert modified_steinmetz(400, 1.5, 0.01, 1.5, 2.0) > 0


def test_modified_steinmetz_scales_with_frequency():
    assert modified_steinmetz(400, 1.0, 0.01, 1.5, 2.0) > modified_steinmetz(
        50, 1.0, 0.01, 1.5, 2.0
    )


def test_bertotti_total_equals_sum():
    result = bertotti(50, 1.5, k_h=0.02, k_e=1e-4, k_a=1e-3)
    assert np.isclose(result["total"], result["hysteresis"] + result["eddy"] + result["excess"])


def test_bertotti_all_components_positive():
    result = bertotti(400, 1.0, k_h=0.01, k_e=5e-5, k_a=5e-4)
    assert result["hysteresis"] > 0
    assert result["eddy"] > 0
    assert result["excess"] > 0


# ─── Fitting tests ────────────────────────────────────────────────────────────


@pytest.fixture
def sample_data():
    """Synthetic loss data generated from known Bertotti coefficients."""
    k_h, k_e, k_a = 0.02, 1e-4, 1e-3
    freqs = np.array([50, 50, 50, 100, 100, 100, 400, 400, 400], dtype=float)
    B_vals = np.array([0.5, 1.0, 1.5, 0.5, 1.0, 1.5, 0.5, 1.0, 1.5], dtype=float)
    loss = bertotti(freqs, B_vals, k_h, k_e, k_a)["total"]
    return freqs, B_vals, loss, (k_h, k_e, k_a)


def test_fit_bertotti_recovers_coefficients(sample_data):
    freqs, B_vals, loss, (k_h, k_e, k_a) = sample_data
    result = fit_bertotti(freqs, B_vals, loss)
    assert np.isclose(result["k_h"], k_h, rtol=1e-3)
    assert np.isclose(result["k_e"], k_e, rtol=1e-3)
    assert np.isclose(result["k_a"], k_a, rtol=1e-3)
    assert result["r2"] > 0.999
    assert result["model"] == "Bertotti"


def test_fit_steinmetz_returns_valid(sample_data):
    freqs, B_vals, loss, _ = sample_data
    result = fit_steinmetz(freqs, B_vals, loss)
    assert "k" in result and "alpha" in result and "beta" in result
    assert 0 < result["r2"] <= 1.0
    assert result["model"] == "Steinmetz"


def test_fit_modified_steinmetz_returns_valid(sample_data):
    freqs, B_vals, loss, _ = sample_data
    result = fit_modified_steinmetz(freqs, B_vals, loss)
    assert "k" in result and "alpha" in result and "beta" in result
    assert result["model"] == "Modified Steinmetz"


def test_fit_loss_model_dispatch(sample_data):
    freqs, B_vals, loss, _ = sample_data
    for model in MODEL_NAMES:
        result = fit_loss_model(freqs, B_vals, loss, model=model)
        assert result["model"] == model
        assert result["r2"] > 0.0


def test_fit_loss_model_unknown_raises(sample_data):
    freqs, B_vals, loss, _ = sample_data
    with pytest.raises(ValueError, match="Unknown model"):
        fit_loss_model(freqs, B_vals, loss, model="SomeUnknownModel")
