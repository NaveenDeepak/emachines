"""
Tests for the star-of-slots winding analysis module.

Reference values validated against emetor.com and SWAT-EM.

Convention note
---------------
emetor.com and the emdesigner winding tool report kw for the **double-layer**
tooth-coil FSCW configuration (w=1, layers=2).  That is the standard industry
convention and the values used in the parametrised FSCW tests below.

For integer-slot windings the standard full pitch is τp = Q/P (one magnetic
pole pitch in slots), NOT Q/p = Q/(P//2) (one electrical cycle).  Using
coil_span = Q/P gives kp1 = 1; using Q/p gives kp1 = sin(π) = 0 (degenerate).
"""

from fractions import Fraction

import numpy as np
import pytest

from emachines.winding.sos import (
    assign_phases,
    build_coil_matrix,
    build_star_of_slots,
    check_symmetry,
    get_basic_params,
    get_valid_coil_spans,
    is_valid_combination,
    winding_factor_sos,
)

# ─────────────────────────────────────────────────────────────────────────────
# get_basic_params
# ─────────────────────────────────────────────────────────────────────────────


class TestGetBasicParams:
    def test_integer_slot(self):
        p = get_basic_params(12, 4)
        assert p["winding_type"] == "integer"
        assert p["q"] == Fraction(1, 1)
        assert p["t"] == 2
        assert p["is_integer"] is True
        assert p["is_fractional"] is False
        assert p["is_concentrated"] is False

    def test_concentrated_fscw(self):
        p = get_basic_params(12, 10)
        assert p["winding_type"] == "concentrated"
        assert p["q"] == Fraction(2, 5)
        assert p["is_concentrated"] is True

    def test_half_slot_fractional(self):
        # 12s/8p: q = 12/(8*3) = 1/2 — fractional, not concentrated
        p = get_basic_params(12, 8)
        assert p["winding_type"] == "fractional"
        assert p["q"] == Fraction(1, 2)
        assert p["is_fractional"] is True

    def test_large_integer_slot(self):
        p = get_basic_params(36, 6)
        assert p["winding_type"] == "integer"
        assert p["q"] == Fraction(2, 1)

    def test_invalid_P_odd(self):
        with pytest.raises(ValueError, match="even"):
            get_basic_params(12, 3)

    def test_invalid_P_zero(self):
        with pytest.raises(ValueError):
            get_basic_params(12, 0)

    def test_coil_pitch_full(self):
        assert get_basic_params(12, 4)["coil_pitch_full"] == 6
        assert get_basic_params(12, 10)["coil_pitch_full"] == 2

    def test_alpha_e(self):
        p = get_basic_params(12, 4)
        assert np.isclose(p["alpha_e"], np.pi / 3)


# ─────────────────────────────────────────────────────────────────────────────
# build_star_of_slots
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildStarOfSlots:
    def test_shape(self):
        assert build_star_of_slots(12, 4).shape == (12,)

    def test_range(self):
        angles = build_star_of_slots(12, 10)
        assert np.all(angles >= 0) and np.all(angles < 2 * np.pi)

    def test_slot_zero_is_zero(self):
        assert np.isclose(build_star_of_slots(12, 4)[0], 0.0)

    def test_6slot_4pole(self):
        angles = build_star_of_slots(6, 4)
        expected = (np.array([0, 2, 4, 0, 2, 4]) * np.pi / 3) % (2 * np.pi)
        assert np.allclose(angles, expected)

    def test_periodicity(self):
        # 12s/4p: angles repeat with period 6 slots (t=2 pole pairs)
        angles = build_star_of_slots(12, 4)
        assert np.allclose(angles[:6], angles[6:])


# ─────────────────────────────────────────────────────────────────────────────
# build_coil_matrix
# ─────────────────────────────────────────────────────────────────────────────


class TestBuildCoilMatrix:
    def test_shape_single_layer(self):
        assert build_coil_matrix(12, 4, 3, layers=1).shape == (1, 12)

    def test_shape_double_layer(self):
        assert build_coil_matrix(12, 4, 3, layers=2).shape == (2, 12)

    def test_no_zeros_double_layer(self):
        for Q, P in [(12, 4), (12, 10), (9, 8), (36, 6)]:
            m = build_coil_matrix(Q, P, 3, layers=2)
            assert np.all(m != 0), f"Zero found for Q={Q}, P={P}"

    def test_phase_values_in_range(self):
        m = build_coil_matrix(12, 10, 3, layers=2)
        assert set(np.abs(m.flatten()).tolist()).issubset({1, 2, 3})

    def test_balanced_conductors(self):
        for Q, P in [(12, 4), (12, 10), (9, 8)]:
            mat = build_coil_matrix(Q, P, 3, layers=1)
            counts = [int(np.sum(np.abs(mat[0]) == k)) for k in [1, 2, 3]]
            assert len(set(counts)) == 1, f"Unbalanced for Q={Q}, P={P}: counts={counts}"

    def test_layer2_is_negated_shifted_layer1(self):
        Q, P, w = 12, 4, 3  # standard full pitch w = Q/P = 3
        mat = build_coil_matrix(Q, P, 3, layers=2, w=w)
        for i in range(Q):
            go_slot = (i - w + Q) % Q
            assert mat[1, i] == -mat[0, go_slot], f"Layer 2 mismatch at slot {i}"


# ─────────────────────────────────────────────────────────────────────────────
# assign_phases
# ─────────────────────────────────────────────────────────────────────────────


class TestAssignPhases:
    def test_returns_m_phases(self):
        assert len(assign_phases(12, 4, 3, layers=1)) == 3

    def test_each_phase_has_two_layer_lists(self):
        for ph in assign_phases(12, 4, 3, layers=2):
            assert len(ph) == 2

    def test_single_layer_layer2_empty(self):
        for ph in assign_phases(12, 4, 3, layers=1):
            assert ph[1] == []

    def test_slot_indices_in_range(self):
        for ph in assign_phases(12, 10, 3, layers=2):
            for layer in ph:
                for slot in layer:
                    assert 1 <= abs(slot) <= 12

    def test_all_slots_covered_double_layer(self):
        Q, P = 12, 4
        phases = assign_phases(Q, P, 3, layers=2)
        for lyr_idx in range(2):
            slots = [abs(s) for ph in phases for s in ph[lyr_idx]]
            assert sorted(slots) == list(
                range(1, Q + 1)
            ), f"Layer {lyr_idx} doesn't cover all slots"


# ─────────────────────────────────────────────────────────────────────────────
# winding_factor_sos
# ─────────────────────────────────────────────────────────────────────────────


class TestWindingFactorSos:
    """
    Winding factors validated against emetor.com.

    FSCW cases: double-layer (layers=2), w=1 — the standard industry convention.
    Integer-slot cases: double-layer, w = Q/P (standard pole pitch, kp=1).
    """

    @pytest.mark.parametrize(
        "Q,P,w,layers,expected_kw1",
        [
            # FSCW — double-layer tooth-coil (emetor reference values)
            (12, 10, 1, 2, 0.933),
            (12, 8, 1, 2, 0.866),
            (9, 8, 1, 2, 0.945),
            (12, 14, 1, 2, 0.933),
            # Integer-slot — double-layer, standard full pitch w = Q/P
            (12, 4, 3, 2, 1.000),  # q=1, w=Q/P=3: kp=1, kd=1
            (24, 4, 6, 2, 0.966),  # q=2, w=Q/P=6: kp=1, kd1≈0.9659 for q=2
        ],
    )
    def test_kw1_vs_emetor(self, Q, P, w, layers, expected_kw1):
        kw = winding_factor_sos(1, Q, P, m=3, layers=layers, w=w)
        assert np.isclose(
            kw, expected_kw1, atol=0.01
        ), f"Q={Q}, P={P}, w={w}, layers={layers}: kw1={kw:.4f}, expected≈{expected_kw1}"

    def test_fundamental_le_one(self):
        for Q, P in [(12, 10), (12, 8), (9, 8), (12, 14), (12, 4), (36, 6)]:
            kw = winding_factor_sos(1, Q, P, layers=2, w=1)
            assert kw <= 1.0 + 1e-9, f"kw1 > 1 for Q={Q}, P={P}: {kw:.4f}"

    def test_fscw_higher_harmonic_le_fundamental(self):
        """For 12s/10p, 3rd harmonic should be well below fundamental."""
        kw1 = winding_factor_sos(1, 12, 10, layers=2, w=1)
        kw3 = winding_factor_sos(3, 12, 10, layers=2, w=1)
        assert kw3 <= kw1 + 1e-9

    def test_symmetry_across_phases(self):
        """All three phases must yield the same kw (balanced winding)."""
        Q, P = 12, 10
        mat = build_coil_matrix(Q, P, 3, layers=2, w=1)
        star = build_star_of_slots(Q, P)
        kw_phases = []
        for k in range(3):
            ph_pos, ph_neg = k + 1, -(k + 1)
            phasor = 0j
            n = 0
            for lyr in range(2):
                for i in range(Q):
                    if mat[lyr, i] == ph_pos:
                        phasor += np.exp(1j * star[i])
                        n += 1
                    elif mat[lyr, i] == ph_neg:
                        phasor -= np.exp(1j * star[i])
                        n += 1
            kw_phases.append(abs(phasor) / n if n > 0 else 0.0)
        assert np.allclose(kw_phases, kw_phases[0], atol=1e-10), f"Phases not balanced: {kw_phases}"

    def test_full_pitch_integer_slot_kw1(self):
        """Full-pitch integer-slot: kw1 = kd1 (kp=1)."""
        # 12s/4p, q=1: kd=1, kp=1 → kw=1.0
        kw = winding_factor_sos(1, 12, 4, m=3, layers=2, w=3)  # w=Q/P=3
        assert np.isclose(kw, 1.0, atol=1e-3)

    def test_chorded_integer_slot_kw1(self):
        """5/6-chorded 24s/4p: kw1 ≈ 0.933."""
        # 24s/4p, q=2, w=5 (5/6 of standard pole pitch Q/P=6)
        kw = winding_factor_sos(1, 24, 4, m=3, layers=2, w=5)
        assert np.isclose(kw, 0.933, atol=0.01)


# ─────────────────────────────────────────────────────────────────────────────
# check_symmetry
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckSymmetry:
    @pytest.mark.parametrize(
        "Q,P,expected",
        [
            (12, 4, True),
            (12, 10, True),
            (9, 8, True),
            (36, 6, True),
            (10, 4, False),
            (6, 4, True),
        ],
    )
    def test_symmetry(self, Q, P, expected):
        assert check_symmetry(Q, P) == expected


# ─────────────────────────────────────────────────────────────────────────────
# get_valid_coil_spans
# ─────────────────────────────────────────────────────────────────────────────


class TestGetValidCoilSpans:
    def test_integer_slot(self):
        assert get_valid_coil_spans(12, 4) == list(range(1, 7))

    def test_fscw(self):
        assert get_valid_coil_spans(12, 10) == [1, 2]

    def test_starts_at_one(self):
        assert get_valid_coil_spans(9, 8)[0] == 1

    def test_ends_at_full_pitch(self):
        Q, P = 36, 6
        assert get_valid_coil_spans(Q, P)[-1] == Q // (P // 2)


# ─────────────────────────────────────────────────────────────────────────────
# is_valid_combination
# ─────────────────────────────────────────────────────────────────────────────


class TestIsValidCombination:
    @pytest.mark.parametrize(
        "Q,P,expected",
        [
            (12, 4, True),
            (12, 10, True),
            (9, 8, True),
            (10, 4, False),
            (2, 4, False),
            (12, 12, False),
            (12, 3, False),
        ],
    )
    def test_combinations(self, Q, P, expected):
        assert is_valid_combination(Q, P) == expected
