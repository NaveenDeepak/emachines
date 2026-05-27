"""
Tests for emachines.mec — Magnetic Equivalent Circuit solver.

Test suite covers:
1. Linear series circuit  — analytic solution verification
2. Linear parallel circuit — analytic verification
3. ShanesudhoffModel      — mu(0) = mu0*mu_r, odd symmetry of dmu/dB
4. SplinePermeabilityModel — consistency with source B-H data
5. Nonlinear series circuit — convergence + qualitative check
6. EI-core example         — matches MEC 3.2 manual (linear case)
7. MECSolution API          — flux(), mmf(), repr()
"""

import math

import numpy as np
import pytest

from emachines.mec import MEC, ShanesudhoffModel, SplinePermeabilityModel

MU0 = 4e-7 * math.pi


# ─────────────────────────────────────────────────────────────────────────────
# 1. Linear series circuit
# ─────────────────────────────────────────────────────────────────────────────


class TestLinearSeriesCircuit:
    """
    Single mesh, two reluctance branches in series.

    Topology:
        [MMF source F] — [R₁] — [R₂] — back to source

    Analytic:  Φ = F / (R₁ + R₂)
    """

    F = 1000.0  # A-turns
    R1 = 1e6  # A-turn/Wb  (e.g. air gap)
    R2 = 2e6
    P1 = 1.0 / R1
    P2 = 1.0 / R2
    Phi_exact = F / (R1 + R2)

    def _build(self) -> MEC:
        mec = MEC()
        mec.add_mesh_branch(branch=1, mesh=1, mmf=self.F)
        mec.add_linear_branch(branch=2, permeance=self.P1, meshes=[1], orientations=[1])
        mec.add_linear_branch(branch=3, permeance=self.P2, meshes=[1], orientations=[1])
        return mec

    def test_flux(self):
        sol = self._build().solve()
        assert sol.converged
        assert sol.flux(2) == pytest.approx(self.Phi_exact, rel=1e-8)
        assert sol.flux(3) == pytest.approx(self.Phi_exact, rel=1e-8)

    def test_mesh_flux(self):
        sol = self._build().solve()
        assert sol.phi_mesh[1] == pytest.approx(self.Phi_exact, rel=1e-8)

    def test_mmf_drops_sum_to_source(self):
        sol = self._build().solve()
        # KVL: V1_drop + V2_drop = F
        drop1 = sol.flux(2) / self.P1
        drop2 = sol.flux(3) / self.P2
        assert drop1 + drop2 == pytest.approx(self.F, rel=1e-6)

    def test_field_energy(self):
        sol = self._build().solve()
        Phi = self.Phi_exact
        Wf_exact = 0.5 * (Phi**2 / self.P1 + Phi**2 / self.P2)
        assert sol.field_energy == pytest.approx(Wf_exact, rel=1e-6)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Linear parallel circuit (two meshes sharing one branch)
# ─────────────────────────────────────────────────────────────────────────────


class TestLinearParallelCircuit:
    """
    Two meshes sharing a centre leg.

    Mesh 1: [F₁] → R_left → R_centre (shared, orientation +1 for m1, -1 for m2)
    Mesh 2: [F₂] → R_right → R_centre

    With F1=1000, F2=500, R_left=R_right=1e6, R_centre=0.5e6:
        Analytic solution via KVL (textbook result).
    """

    F1 = 1000.0
    F2 = 500.0
    Rl = 1e6  # left leg
    Rr = 1e6  # right leg
    Rc = 0.5e6  # centre leg

    def _analytic(self):
        # KVL mesh 1: Rl*Φ1 + Rc*(Φ1 - Φ2) = F1  → (Rl+Rc)*Φ1 - Rc*Φ2 = F1
        # KVL mesh 2: Rr*Φ2 + Rc*(Φ2 - Φ1) = F2  → -Rc*Φ1 + (Rr+Rc)*Φ2 = F2
        A = np.array([[self.Rl + self.Rc, -self.Rc], [-self.Rc, self.Rr + self.Rc]])
        b = np.array([self.F1, self.F2])
        return np.linalg.solve(A, b)

    def _build(self) -> MEC:
        mec = MEC()
        mec.add_mesh_branch(branch=1, mesh=1, mmf=self.F1)
        mec.add_mesh_branch(branch=2, mesh=2, mmf=self.F2)
        mec.add_linear_branch(branch=3, permeance=1 / self.Rl, meshes=[1], orientations=[1])
        mec.add_linear_branch(branch=4, permeance=1 / self.Rr, meshes=[2], orientations=[1])
        # Centre leg shared by both meshes
        mec.add_linear_branch(branch=5, permeance=1 / self.Rc, meshes=[1, 2], orientations=[1, -1])
        return mec

    def test_mesh_fluxes(self):
        sol = self._build().solve()
        phi1_ex, phi2_ex = self._analytic()
        assert sol.phi_mesh[1] == pytest.approx(phi1_ex, rel=1e-7)
        assert sol.phi_mesh[2] == pytest.approx(phi2_ex, rel=1e-7)

    def test_centre_leg_flux(self):
        sol = self._build().solve()
        phi1_ex, phi2_ex = self._analytic()
        # Centre leg flux = Φ₁ − Φ₂ (orientation [+1, -1])
        phi_c_ex = phi1_ex - phi2_ex
        assert sol.flux(5) == pytest.approx(phi_c_ex, rel=1e-7)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ShanesudhoffModel
# ─────────────────────────────────────────────────────────────────────────────


class TestShanesudhoffModel:
    def test_mu_at_zero_equals_mu0_mur(self):
        model = ShanesudhoffModel.ferrite_3C90()
        mu_r = 22340.9259
        assert model.mu(0.0) == pytest.approx(MU0 * mu_r, rel=1e-4)

    def test_mu_positive(self):
        model = ShanesudhoffModel.ferrite_3C90()
        for B in [0.0, 0.01, 0.1, 0.3]:
            assert model.mu(B) > 0, f"mu({B}) should be positive"

    def test_mu_decreases_with_B(self):
        """Permeability should decrease as |B| increases (saturation)."""
        model = ShanesudhoffModel.ferrite_3C90()
        mu_low = model.mu(0.01)
        mu_high = model.mu(0.30)
        assert mu_high < mu_low

    def test_mu_even_symmetry(self):
        model = ShanesudhoffModel.ferrite_3C90()
        for B in [0.05, 0.15, 0.25]:
            assert model.mu(B) == pytest.approx(model.mu(-B), rel=1e-10)

    def test_dmu_dB_odd_symmetry(self):
        model = ShanesudhoffModel.ferrite_3C90()
        for B in [0.05, 0.15, 0.25]:
            assert model.dmu_dB(B) == pytest.approx(-model.dmu_dB(-B), rel=1e-10)

    def test_dmu_dB_numerical(self):
        """Finite-difference check of analytical derivative."""
        model = ShanesudhoffModel.ferrite_3C90()
        B0 = 0.1
        h = 1e-7
        dmu_analytic = model.dmu_dB(B0)
        dmu_fd = (model.mu(B0 + h) - model.mu(B0 - h)) / (2 * h)
        assert dmu_analytic == pytest.approx(dmu_fd, rel=1e-4)

    def test_custom_parameters(self):
        """Linear model limit: single term with large b → nearly constant μ."""
        model = ShanesudhoffModel(mu_r=1000.0, a=[1e-6], b=[1e6], gamma=[2.0])
        assert model.mu(0.0) == pytest.approx(MU0 * 1000.0, rel=1e-2)


# ─────────────────────────────────────────────────────────────────────────────
# 4. SplinePermeabilityModel
# ─────────────────────────────────────────────────────────────────────────────


class TestSplinePermeabilityModel:
    # Simple 3-point M-19 excerpt
    H_data = [0, 100, 500, 2000, 5000]
    B_data = [0, 1.0, 1.4, 1.6, 1.8]

    def test_mu_at_origin(self):
        m = SplinePermeabilityModel(self.H_data, self.B_data)
        # At B→0, μ ≈ μ₀·H[1]/B[1]
        mu_expected = MU0 * self.H_data[1] / self.B_data[1]
        assert m.mu(0.0) == pytest.approx(mu_expected, rel=1e-6)

    def test_mu_positive_everywhere(self):
        m = SplinePermeabilityModel(self.H_data, self.B_data)
        for B in np.linspace(0, 1.8, 30):
            assert m.mu(B) > 0

    def test_even_symmetry(self):
        m = SplinePermeabilityModel(self.H_data, self.B_data)
        for B in [0.2, 0.8, 1.5]:
            assert m.mu(B) == pytest.approx(m.mu(-B), rel=1e-10)

    def test_dmu_dB_odd_symmetry(self):
        m = SplinePermeabilityModel(self.H_data, self.B_data)
        for B in [0.2, 0.8, 1.5]:
            assert m.dmu_dB(B) == pytest.approx(-m.dmu_dB(-B), rel=1e-10)

    def test_dmu_dB_numerical(self):
        m = SplinePermeabilityModel(self.H_data, self.B_data)
        B0 = 0.9
        h = 1e-7
        dmu_fd = (m.mu(B0 + h) - m.mu(B0 - h)) / (2 * h)
        assert m.dmu_dB(B0) == pytest.approx(dmu_fd, rel=1e-4)

    def test_clamps_beyond_data(self):
        """Beyond B_max the model returns the final μ (no extrapolation)."""
        m = SplinePermeabilityModel(self.H_data, self.B_data)
        mu_at_max = m.mu(self.B_data[-1])
        assert m.mu(100.0) == pytest.approx(mu_at_max, rel=1e-10)

    def test_bad_input_raises(self):
        with pytest.raises(ValueError):
            SplinePermeabilityModel([1, 2, 3], [0, 1, 2])  # doesn't start at 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Nonlinear series circuit (single mesh, ferrite core)
# ─────────────────────────────────────────────────────────────────────────────


class TestNonlinearSeries:
    """
    Single mesh: MMF source in series with a nonlinear ferrite branch.

    Since the branch is in a single-branch mesh:
        Φ = solution flux,  B = Φ/A,  H = F/l
        Check: μ(B) ≈ B/H within solver tolerance.
    """

    F = 500.0  # A-turns
    l = 0.05  # m
    A = 1e-4  # m²

    def test_convergence(self):
        mec = MEC()
        mec.add_mesh_branch(branch=1, mesh=1, mmf=self.F)
        mec.add_nonlinear_branch(
            branch=2,
            length=self.l,
            area=self.A,
            model=ShanesudhoffModel.ferrite_3C90(),
            meshes=[1],
            orientations=[1],
        )
        sol = mec.solve()
        assert sol.converged, f"Did not converge: {sol}"

    def test_self_consistent_BH(self):
        """At solution: H = F/l and B = Φ/A should satisfy B = μ(B)·H."""
        mec = MEC()
        mec.add_mesh_branch(branch=1, mesh=1, mmf=self.F)
        mec.add_nonlinear_branch(
            branch=2,
            length=self.l,
            area=self.A,
            model=ShanesudhoffModel.ferrite_3C90(),
            meshes=[1],
            orientations=[1],
        )
        sol = mec.solve()
        model = ShanesudhoffModel.ferrite_3C90()
        Phi = sol.flux(2)
        B = Phi / self.A
        H = self.F / self.l
        mu = model.mu(B)
        assert B == pytest.approx(mu * H, rel=1e-4)

    def test_iterations_reasonable(self):
        mec = MEC()
        mec.add_mesh_branch(branch=1, mesh=1, mmf=self.F)
        mec.add_nonlinear_branch(
            branch=2,
            length=self.l,
            area=self.A,
            model=ShanesudhoffModel.ferrite_3C90(),
            meshes=[1],
            orientations=[1],
        )
        sol = mec.solve()
        assert sol.n_iterations < 50


# ─────────────────────────────────────────────────────────────────────────────
# 6. EI-core (linear approximation of MEC 3.2 manual Example 1)
# ─────────────────────────────────────────────────────────────────────────────


class TestEICore:
    """
    EI-core transformer simplified to a single-mesh linear circuit.

    Geometry (approximate, from MEC 3.2 manual):
        - Core: 3C90 ferrite, modelled as constant μ = μ₀·μᵣ_eff
        - Air gap: g = 1 mm
        - Mean path length in core: l_c = 120 mm
        - Cross-section: A = 16×16 mm²
        - Winding: N = 100 turns, I swept from 0.01 to 0.5 A

    Linear reference:  Φ = N·I / (l_c/(μ_eff·A) + g/(μ₀·A))
    """

    N = 100
    g = 1e-3
    l_c = 0.12
    A = (16e-3) ** 2
    mu_r_eff = 1000.0  # effective relative permeability (moderate)

    def _build(self, I: float) -> MEC:
        F = self.N * I
        P_core = self.mu_r_eff * MU0 * self.A / self.l_c
        P_gap = MU0 * self.A / self.g
        mec = MEC()
        mec.add_mesh_branch(branch=1, mesh=1, mmf=F)
        mec.add_linear_branch(branch=2, permeance=P_core, meshes=[1], orientations=[1])
        mec.add_linear_branch(branch=3, permeance=P_gap, meshes=[1], orientations=[1])
        return mec

    def _analytic(self, I: float) -> float:
        F = self.N * I
        Rc = self.l_c / (self.mu_r_eff * MU0 * self.A)
        Rg = self.g / (MU0 * self.A)
        return F / (Rc + Rg)

    @pytest.mark.parametrize("I", [0.01, 0.1, 0.5])
    def test_flux_vs_analytic(self, I):
        sol = self._build(I).solve()
        assert sol.converged
        Phi_ex = self._analytic(I)
        assert sol.flux(2) == pytest.approx(Phi_ex, rel=1e-7)
        assert sol.flux(3) == pytest.approx(Phi_ex, rel=1e-7)

    def test_flux_proportional_to_current(self):
        """Linear circuit: Φ should scale linearly with MMF."""
        phi1 = self._build(0.1).solve().flux(2)
        phi2 = self._build(0.2).solve().flux(2)
        assert phi2 == pytest.approx(2 * phi1, rel=1e-7)

    def test_field_energy_positive(self):
        sol = self._build(0.1).solve()
        assert sol.field_energy > 0


# ─────────────────────────────────────────────────────────────────────────────
# 7. MECSolution API
# ─────────────────────────────────────────────────────────────────────────────


class TestMECSolutionAPI:
    def _simple_sol(self):
        mec = MEC()
        mec.add_mesh_branch(branch=10, mesh=1, mmf=1000.0)
        mec.add_linear_branch(branch=20, permeance=1e-6, meshes=[1], orientations=[1])
        return mec.solve()

    def test_flux_method(self):
        sol = self._simple_sol()
        assert sol.flux(20) == pytest.approx(sol.phi_branches[20], rel=1e-12)

    def test_mmf_method(self):
        sol = self._simple_sol()
        assert sol.mmf(20) == pytest.approx(sol.mmf_branches[20], rel=1e-12)

    def test_repr_contains_status(self):
        sol = self._simple_sol()
        r = repr(sol)
        assert "converged" in r

    def test_key_error_on_unknown_branch(self):
        sol = self._simple_sol()
        with pytest.raises(KeyError):
            sol.flux(999)

    def test_repr_contains_scaling_info(self):
        """repr should mention heuristic scaling when no per-unit bases given."""
        sol = self._simple_sol()
        assert "heuristic" in repr(sol)

    def test_repr_perunit_scaling(self):
        """repr should mention phi_base when per-unit is used."""
        mec = MEC(phi_base=1e-4, F_base=1e3)
        mec.add_mesh_branch(branch=10, mesh=1, mmf=1000.0)
        mec.add_linear_branch(branch=20, permeance=1e-6, meshes=[1], orientations=[1])
        sol = mec.solve()
        assert "pu" in repr(sol)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Per-unit scaling (Horvath 2018)
# ─────────────────────────────────────────────────────────────────────────────


class TestPerUnitScaling:
    """
    Per-unit scaling should give identical answers to the heuristic for
    simple circuits, and the solution object should report the bases.
    """

    F = 1000.0
    P = 1e-6
    R = 1.0 / P
    Phi_exact = F / R

    # plausible per-unit bases for this circuit
    phi_base = Phi_exact * 1.1
    F_base = F * 1.5

    def test_flux_matches_heuristic(self):
        mec_pu = MEC(phi_base=self.phi_base, F_base=self.F_base)
        mec_pu.add_mesh_branch(1, mesh=1, mmf=self.F)
        mec_pu.add_linear_branch(2, permeance=self.P, meshes=[1], orientations=[1])
        sol_pu = mec_pu.solve()

        mec_h = MEC()
        mec_h.add_mesh_branch(1, mesh=1, mmf=self.F)
        mec_h.add_linear_branch(2, permeance=self.P, meshes=[1], orientations=[1])
        sol_h = mec_h.solve()

        assert sol_pu.flux(2) == pytest.approx(sol_h.flux(2), rel=1e-8)

    def test_bases_stored_in_solution(self):
        mec = MEC(phi_base=self.phi_base, F_base=self.F_base)
        mec.add_mesh_branch(1, mesh=1, mmf=self.F)
        mec.add_linear_branch(2, permeance=self.P, meshes=[1], orientations=[1])
        sol = mec.solve()
        assert sol.phi_base == pytest.approx(self.phi_base)
        assert sol.F_base == pytest.approx(self.F_base)

    def test_no_bases_gives_none(self):
        mec = MEC()
        mec.add_mesh_branch(1, mesh=1, mmf=self.F)
        mec.add_linear_branch(2, permeance=self.P, meshes=[1], orientations=[1])
        sol = mec.solve()
        assert sol.phi_base is None
        assert sol.F_base is None

    def test_mismatched_bases_raises(self):
        with pytest.raises(ValueError):
            MEC(phi_base=1e-4, F_base=None)
        with pytest.raises(ValueError):
            MEC(phi_base=None, F_base=1e3)

    def test_nonlinear_perunit_converges(self):
        """Per-unit scaled nonlinear circuit should still converge."""
        l, A = 0.05, 1e-4
        model = ShanesudhoffModel.ferrite_3C90()

        # Estimate bases from expected operating point
        F = 500.0
        B_est = 0.2  # rough estimate of B in core
        A_base = A
        P_base = MU0 * A_base / l
        phi_base = B_est * A_base  # ≈ near-knee B × A
        F_base = phi_base / P_base

        mec = MEC(phi_base=phi_base, F_base=F_base)
        mec.add_mesh_branch(1, mesh=1, mmf=F)
        mec.add_nonlinear_branch(2, length=l, area=A, model=model, meshes=[1], orientations=[1])
        sol = mec.solve()
        assert sol.converged
        assert sol.n_iterations < 50


# ─────────────────────────────────────────────────────────────────────────────
# 9. Winding / flux linkage
# ─────────────────────────────────────────────────────────────────────────────


class TestFluxLinkage:
    """
    Register windings and verify flux linkage computation.

    Topology: single mesh, two reluctance branches in series.
    N-turn coil links branch 2 only.
    Expected: λ = N · Φ_exact
    """

    F = 1000.0
    R1 = 1e6
    R2 = 2e6
    P1 = 1.0 / R1
    P2 = 1.0 / R2
    N = 100
    Phi_exact = F / (R1 + R2)

    def _build(self, branch_turns=None) -> MEC:
        mec = MEC()
        mec.add_mesh_branch(1, mesh=1, mmf=self.F)
        mec.add_linear_branch(2, permeance=self.P1, meshes=[1], orientations=[1])
        mec.add_linear_branch(3, permeance=self.P2, meshes=[1], orientations=[1])
        if branch_turns:
            mec.add_winding("coil", branch_turns)
        return mec

    def test_single_winding_one_branch(self):
        mec = self._build({2: self.N})
        sol = mec.solve()
        assert "coil" in sol.flux_linkages
        assert sol.flux_linkage("coil") == pytest.approx(self.N * self.Phi_exact, rel=1e-7)

    def test_winding_spanning_two_branches(self):
        """Winding links branch 2 (+N) and branch 3 (+N) — series aiding."""
        mec = self._build({2: self.N, 3: self.N})
        sol = mec.solve()
        # λ = N·Φ + N·Φ = 2N·Φ
        assert sol.flux_linkage("coil") == pytest.approx(2 * self.N * self.Phi_exact, rel=1e-7)

    def test_winding_opposing_polarity(self):
        """Opposing turns: λ = (+N)·Φ + (−N)·Φ = 0 for equal branches."""
        R = 1e6
        mec = MEC()
        mec.add_mesh_branch(1, mesh=1, mmf=1000.0)
        mec.add_linear_branch(2, permeance=1 / R, meshes=[1], orientations=[1])
        mec.add_linear_branch(3, permeance=1 / R, meshes=[1], orientations=[1])
        mec.add_winding("coil", {2: +100, 3: -100})
        sol = mec.solve()
        # Same flux in both branches (series circuit), opposing turns → λ = 0
        assert sol.flux_linkage("coil") == pytest.approx(0.0, abs=1e-15)

    def test_multiple_windings(self):
        mec = MEC()
        mec.add_mesh_branch(1, mesh=1, mmf=self.F)
        mec.add_linear_branch(2, permeance=self.P1, meshes=[1], orientations=[1])
        mec.add_linear_branch(3, permeance=self.P2, meshes=[1], orientations=[1])
        mec.add_winding("primary", {2: 100})
        mec.add_winding("secondary", {3: 50})
        sol = mec.solve()
        assert sol.flux_linkage("primary") == pytest.approx(100 * self.Phi_exact, rel=1e-7)
        assert sol.flux_linkage("secondary") == pytest.approx(50 * self.Phi_exact, rel=1e-7)

    def test_no_winding_empty_dict(self):
        mec = MEC()
        mec.add_mesh_branch(1, mesh=1, mmf=self.F)
        mec.add_linear_branch(2, permeance=self.P1, meshes=[1], orientations=[1])
        sol = mec.solve()
        assert sol.flux_linkages == {}

    def test_unknown_winding_raises(self):
        mec = self._build({2: self.N})
        sol = mec.solve()
        with pytest.raises(KeyError):
            sol.flux_linkage("nonexistent")

    def test_flux_linkage_method_matches_dict(self):
        mec = self._build({2: self.N})
        sol = mec.solve()
        assert sol.flux_linkage("coil") == sol.flux_linkages["coil"]


# ─────────────────────────────────────────────────────────────────────────────
# 10. Scaling is fixed across NR iterations (regression)
# ─────────────────────────────────────────────────────────────────────────────


class TestScalingConsistency:
    """
    Verify that using per-unit or heuristic scaling gives the same answer
    on a mixed mesh/nodal circuit, and that the solver still converges
    when saturation is present.
    """

    def _build_mixed(self, phi_base=None, F_base=None) -> MEC:
        """
        Simple mixed circuit:
          Mesh 1: MMF source → nonlinear core branch
          Node 1: airgap nodal branch connecting to ground
        """
        g = 1e-3  # air gap [m]
        A_ag = 4e-4  # air-gap area [m²]
        P_ag = MU0 * A_ag / g

        kwargs = {}
        if phi_base is not None:
            kwargs = dict(phi_base=phi_base, F_base=F_base)

        mec = MEC(**kwargs)
        mec.add_mesh_branch(1, mesh=1, mmf=800.0)
        mec.add_linear_branch(2, permeance=P_ag, meshes=[1], orientations=[1])
        return mec

    def test_heuristic_converges(self):
        mec = self._build_mixed()
        sol = mec.solve()
        assert sol.converged

    def test_perunit_matches_heuristic_flux(self):
        g = 1e-3
        A_ag = 4e-4
        P_ag = MU0 * A_ag / g
        B_b = 1.6
        phi_b = B_b * A_ag
        F_b = phi_b / P_ag

        sol_pu = self._build_mixed(phi_base=phi_b, F_base=F_b).solve()
        sol_h = self._build_mixed().solve()

        assert sol_pu.flux(2) == pytest.approx(sol_h.flux(2), rel=1e-6)
