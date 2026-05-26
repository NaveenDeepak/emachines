"""Tests for PMSM dq-model."""

import numpy as np
import pytest

from emachines.motors.pmsm import PMSMParams, back_emf, dq_currents, torque


@pytest.fixture
def spm():
    """Typical SPM parameters (Ld = Lq)."""
    return PMSMParams(p=3, Ld=5e-3, Lq=5e-3, psi_m=0.15, Rs=0.5)


@pytest.fixture
def ipm():
    """Typical IPM parameters (Ld < Lq)."""
    return PMSMParams(p=4, Ld=3e-3, Lq=8e-3, psi_m=0.12, Rs=0.3)


def test_back_emf(spm):
    """E = omega_e * psi_m"""
    omega_e = 2 * np.pi * 50 * spm.p  # electrical rad/s at 50 Hz mechanical
    E = back_emf(omega_e, spm.psi_m)
    assert E > 0
    assert np.isclose(E, omega_e * spm.psi_m)


def test_spm_torque_no_reluctance(spm):
    """SPM: reluctance torque = 0, Te depends only on iq."""
    Te_1 = torque(spm, id=0.0, iq=10.0)
    Te_2 = torque(spm, id=-5.0, iq=10.0)
    # For SPM (Ld=Lq), id has no effect on torque
    assert np.isclose(Te_1, Te_2, atol=1e-10)


def test_ipm_reluctance_torque(ipm):
    """IPM: negative id adds reluctance torque (MTPA region)."""
    Te_id0 = torque(ipm, id=0.0, iq=10.0)
    Te_mtpa = torque(ipm, id=-5.0, iq=10.0)
    assert Te_mtpa > Te_id0  # reluctance torque boosts total torque


def test_torque_sign(spm):
    """Positive iq → positive torque (motoring)."""
    assert torque(spm, id=0.0, iq=5.0) > 0
    assert torque(spm, id=0.0, iq=-5.0) < 0


def test_dq_currents_steady_state(spm):
    """Steady-state currents should satisfy voltage equations."""
    omega_e = 2 * np.pi * 100.0
    Vd, Vq = 0.0, 100.0
    id_, iq_ = dq_currents(spm, omega_e, Vd, Vq)

    # Verify voltage equations
    Vd_check = spm.Rs * id_ - omega_e * spm.Lq * iq_
    Vq_check = spm.Rs * iq_ + omega_e * (spm.Ld * id_ + spm.psi_m)
    assert np.isclose(Vd_check, Vd, atol=1e-6)
    assert np.isclose(Vq_check, Vq, atol=1e-6)
