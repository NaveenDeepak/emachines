"""
Tests for winding factor calculations.

Reference values validated against emetor.com and SWAT-EM.
"""

import numpy as np
import pytest

from emachines.winding.factors import distribution_factor, pitch_factor, winding_factor


class TestPitchFactor:
    def test_full_pitch_fundamental(self):
        """Full-pitch coil: kp1 = 1.0"""
        assert np.isclose(pitch_factor(1, 3, 3.0), 1.0)

    def test_chorded_coil(self):
        """5/6 chording: kp1 = sin(5π/12) ≈ 0.9659"""
        assert np.isclose(pitch_factor(1, 5, 6.0), np.sin(5 * np.pi / 12), atol=1e-4)

    def test_third_harmonic_elimination(self):
        """2/3 chording eliminates 3rd harmonic: kp3 = 0"""
        assert np.isclose(pitch_factor(3, 4, 6.0), 0.0, atol=1e-10)


class TestDistributionFactor:
    def test_q1_concentrated(self):
        """q=1: kd1 = 1.0"""
        assert np.isclose(distribution_factor(1, 6, 1, m=3), 1.0)

    def test_q2_distributed(self):
        """q=2: kd1 ≈ 0.9659"""
        assert np.isclose(distribution_factor(1, 12, 1, m=3), 0.9659, atol=1e-3)

    def test_fscw_raises(self):
        """FSCW (q < 1) raises ValueError — use winding_factor() for dispatch."""
        with pytest.raises(ValueError, match="star-of-slots"):
            distribution_factor(1, 12, 5, m=3)


class TestWindingFactorIntegerSlot:
    @pytest.mark.parametrize(
        "Q,p,coil_span,expected_kw1",
        [
            (24, 2, 5, 0.9330),  # 24s/4p, 5/6 chording: kp=0.9659, kd=0.9659
            (36, 3, 5, 0.9330),  # 36s/6p, 5/6 chording: same q=2, same result
            (12, 1, 6, 0.9659),  # 12s/2p, full pitch: kp=1.0, kd=0.9659
        ],
    )
    def test_integer_slot_kw1(self, Q, p, coil_span, expected_kw1):
        kw = winding_factor(1, Q, p, coil_span)
        assert np.isclose(
            kw, expected_kw1, atol=0.001
        ), f"Q={Q}, p={p}, coil_span={coil_span}: kw1={kw:.4f}, expected≈{expected_kw1}"


class TestWindingFactorFSCW:
    """FSCW winding factors via star-of-slots — validated against emetor.com."""

    @pytest.mark.parametrize(
        "Q,P,coil_span,expected_kw1",
        [
            (12, 10, 1, 0.933),  # 12s/10p — most common FSCW
            (12, 8, 1, 0.866),  # 12s/8p  — q = 1/2
            (9, 8, 1, 0.945),  # 9s/8p
            (12, 14, 1, 0.933),  # 12s/14p
        ],
    )
    def test_fscw_kw1(self, Q, P, coil_span, expected_kw1):
        """FSCW fundamental winding factors match emetor reference values."""
        p = P // 2
        kw = winding_factor(1, Q, p, coil_span)
        assert np.isclose(
            kw, expected_kw1, atol=0.01
        ), f"Q={Q}, P={P}: kw1={kw:.4f}, expected≈{expected_kw1}"
