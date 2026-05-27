"""
Magnetic Equivalent Circuit (MEC) solver.

Architecture
------------
Implements the scaled mixed mesh/nodal formulation described in:

    Horvath, D.C., Pekarek, S.D. & Sudhoff, S.D. (2018).
    "A Scaled Mesh/Nodal Formulation of Magnetic Equivalent Circuits
    with Motion." *IEEE Trans. Energy Convers.*, DOI 10.1109/TEC.2018.2855100

based on the MEC 3.2 MATLAB toolbox (Sudhoff, Purdue, 2014).

Branch types
~~~~~~~~~~~~
* **Mesh branch**       – one per independent loop; carries mesh flux Φₘ
  and an optional MMF source (coil winding).
* **Reluctance branch** – linear or nonlinear; crossed by one or more mesh
  fluxes; permeability updated each Newton-Raphson iteration.
* **Nodal branch**      – linear; connects two magnetic nodes via a fixed
  permeance; introduces a node-potential variable u.

Scaling
~~~~~~~
Two modes:

1. **Per-unit** (Horvath 2018, recommended for motion / high-saturation):
   User supplies ``phi_base`` and ``F_base``. All reluctances are
   normalised by ``R_base = F_base / phi_base``, all permeances by
   ``P_base = phi_base / F_base``. The scaling factor is fixed for the
   entire Newton-Raphson iteration, keeping κ(J) ≈ 10².

2. **Heuristic** (default fallback): ``s = √(mean|A₁₁| / mean|A₂₂|)``,
   computed once from the *initial* assembled matrix and held fixed for
   all subsequent NR iterations.

Newton-Raphson linearisation (per nonlinear branch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Given operating-point flux Φ₀ and material B₀ = (Φ₀ − Φs)/A:

    R₀     = l / (μ(B₀)·A)
    S₀     = (dμ/dB)·B₀ / μ
    R_eff  = R₀·(1 − S₀)          [incremental reluctance → into matrix]
    Fs_eff = Fs − R₀·(S₀·Φ₀ − Φs) [corrected source → into RHS]

At convergence R₀·(Φ* − Φs) = Fs, the physical branch equation.

Flux linkage
~~~~~~~~~~~~
Register windings with :meth:`add_winding`:

    mec.add_winding('a', {branch_id: N_turns, ...})

After :meth:`solve`, the result carries ``sol.flux_linkages['a']``:

    λ = Σ_k  sign(Nₖ) · |Nₖ| · Φ_branch_k

where ``N_turns`` is signed (positive = aligned with assumed flux direction).

References
----------
    Horvath, Pekarek & Sudhoff (2018). IEEE TEC. DOI 10.1109/TEC.2018.2855100
    Sudhoff, S.D. (2014). MEC 3.2 Toolbox Manual. Purdue University.
    Bash & Pekarek (2010). IEEE Trans. Energy Convers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .material import LinearPermeabilityModel, PermeabilityModel
from .result import MECSolution

__all__ = ["MEC", "BranchType"]

MU0 = 4e-7 * math.pi


# ─────────────────────────────────────────────────────────────────────────────
# Internal branch descriptors
# ─────────────────────────────────────────────────────────────────────────────


class BranchType:
    MESH = "mesh"
    RELUCTANCE = "reluctance"
    NODAL = "nodal"


@dataclass
class _Branch:
    """Internal representation of a single MEC branch."""

    branch_id: int
    btype: str

    # Mesh branch
    mesh_id: Optional[int] = None
    mmf: float = 0.0

    # Reluctance branch
    length: float = 0.0
    area: float = 0.0
    model: Optional[PermeabilityModel] = None
    phi_source: float = 0.0  # PM Norton flux source [Wb]
    meshes: List[int] = field(default_factory=list)
    orientations: List[int] = field(default_factory=list)
    permeance: Optional[float] = None  # pre-computed constant permeance

    # Nodal branch
    node_from: Optional[int] = None
    node_to: Optional[int] = None


@dataclass
class _Winding:
    """Internal descriptor of a multi-turn winding."""

    winding_id: Any
    # branch_id → signed turn count (positive = aligned with positive flux)
    branch_turns: Dict[int, float]


# ─────────────────────────────────────────────────────────────────────────────
# MEC builder / solver
# ─────────────────────────────────────────────────────────────────────────────


class MEC:
    """
    Magnetic Equivalent Circuit builder and Newton-Raphson solver.

    Parameters
    ----------
    phi_base : float, optional
        Base flux [Wb] for per-unit scaling (Horvath 2018).
        Typically ``B_base * A_base`` where ``B_base ≈ 1.6 T`` and
        ``A_base`` is the maximum air-gap cross-sectional area.
        If *None*, a heuristic scale is used instead.
    F_base : float, optional
        Base MMF [A-turns] for per-unit scaling.
        Typically ``phi_base / P_base`` where ``P_base = µ₀·A_base/g``.
        Must be supplied together with *phi_base* or not at all.
    rtol, atol : float
        Newton-Raphson convergence tolerances on ‖ΔΦ‖:
        ``‖ΔΦ‖ ≤ rtol·½‖Φₖ + Φₖ₋₁‖ + atol``
    max_iter : int
        Maximum Newton-Raphson iterations.

    Notes
    -----
    **Motion / position-dependent analysis** (Horvath 2018 pattern):
    Pre-define *all* air-gap branches (including those that will become
    zero at certain rotor positions).  At each mechanical step call
    ``update_permeance(branch, new_value)`` on the relevant air-gap
    branches and call ``solve()`` again.  Because air-gap permeances
    → 0 (not ∞) as alignment decreases, the circuit topology never
    needs to be restructured.
    """

    def __init__(
        self,
        phi_base: Optional[float] = None,
        F_base: Optional[float] = None,
        rtol: float = 1e-6,
        atol: float = 1e-12,
        max_iter: int = 200,
    ) -> None:
        if (phi_base is None) != (F_base is None):
            raise ValueError("phi_base and F_base must both be supplied or both omitted.")
        self.phi_base = phi_base
        self.F_base = F_base
        self.rtol = rtol
        self.atol = atol
        self.max_iter = max_iter

        self._branches: Dict[int, _Branch] = {}
        self._windings: Dict[Any, _Winding] = {}

    # ── branch registration ───────────────────────────────────────────────

    def add_mesh_branch(
        self,
        branch: int,
        mesh: int,
        mmf: float = 0.0,
    ) -> "MEC":
        """
        Add a *mesh* branch — the primary loop variable for mesh *mesh*.

        There must be exactly one mesh branch per independent mesh.

        Parameters
        ----------
        branch : int
            Unique branch identifier.
        mesh : int
            Index of the mesh this branch drives (1-based).
        mmf : float
            MMF source in this branch [A-turns].
        """
        self._check_new(branch)
        self._branches[branch] = _Branch(
            branch_id=branch,
            btype=BranchType.MESH,
            mesh_id=mesh,
            mmf=mmf,
        )
        return self

    def add_linear_branch(
        self,
        branch: int,
        permeance: float,
        mmf: float = 0.0,
        meshes: Sequence[int] = (),
        orientations: Sequence[int] = (),
        phi_source: float = 0.0,
    ) -> "MEC":
        """
        Add a linear reluctance branch with a fixed permeance [Wb/A-turns].

        Parameters
        ----------
        branch : int
            Unique branch identifier.
        permeance : float
            Magnetic permeance P = 1/R [Wb/A-turns].
        mmf : float
            MMF source within this branch [A-turns].
        meshes : sequence of int
            Mesh indices whose fluxes pass through this branch.
        orientations : sequence of int
            +1 or −1 per mesh (sign convention).
        phi_source : float
            Permanent-magnet Norton flux source [Wb].
        """
        self._check_new(branch)
        self._branches[branch] = _Branch(
            branch_id=branch,
            btype=BranchType.RELUCTANCE,
            permeance=permeance,
            mmf=mmf,
            meshes=list(meshes),
            orientations=list(orientations),
            phi_source=phi_source,
        )
        return self

    def add_nonlinear_branch(
        self,
        branch: int,
        length: float,
        area: float,
        model: Optional[PermeabilityModel] = None,
        mmf: float = 0.0,
        meshes: Sequence[int] = (),
        orientations: Sequence[int] = (),
        phi_source: float = 0.0,
    ) -> "MEC":
        """
        Add a nonlinear reluctance branch (electrical steel / ferrite core).

        Parameters
        ----------
        branch : int
            Unique branch identifier.
        length : float
            Mean flux path length [m].
        area : float
            Cross-sectional area [m²].
        model : PermeabilityModel, optional
            Permeability model.  Defaults to free-space (μ = μ₀).
        mmf : float
            MMF source within this branch [A-turns].
        meshes, orientations : sequences
            Mesh fluxes passing through this branch with their signs.
        phi_source : float
            PM Norton flux source [Wb].
        """
        self._check_new(branch)
        if model is None:
            model = LinearPermeabilityModel(mu_r=1.0)
        self._branches[branch] = _Branch(
            branch_id=branch,
            btype=BranchType.RELUCTANCE,
            length=length,
            area=area,
            model=model,
            mmf=mmf,
            meshes=list(meshes),
            orientations=list(orientations),
            phi_source=phi_source,
        )
        return self

    def add_nodal_branch(
        self,
        branch: int,
        permeance: float,
        mmf: float = 0.0,
        node_from: int = 0,
        node_to: int = 0,
        meshes: Sequence[int] = (),
        orientations: Sequence[int] = (),
    ) -> "MEC":
        """
        Add a nodal branch connecting two magnetic nodes.

        Nodal branches introduce node-potential unknowns (magnetic scalar
        potentials) to enforce flux-continuity at T-junctions and
        pole-symmetric boundaries.  All nodal branches are linear.

        Parameters
        ----------
        branch : int
            Unique branch identifier.
        permeance : float
            Magnetic permeance [Wb/A-turns].
        mmf : float
            MMF source [A-turns].
        node_from, node_to : int
            Node numbers (0 = reference / ground).
        meshes, orientations : sequences
            Mesh fluxes that also flow through this branch.
        """
        self._check_new(branch)
        self._branches[branch] = _Branch(
            branch_id=branch,
            btype=BranchType.NODAL,
            permeance=permeance,
            mmf=mmf,
            node_from=node_from,
            node_to=node_to,
            meshes=list(meshes),
            orientations=list(orientations),
        )
        return self

    # ── winding registration ──────────────────────────────────────────────

    def add_winding(
        self,
        winding_id: Any,
        branch_turns: Dict[int, float],
    ) -> "MEC":
        """
        Register a multi-turn winding for flux-linkage computation.

        After :meth:`solve`, ``sol.flux_linkages[winding_id]`` contains:

            λ = Σ_k  Nₖ · Φ_branch_k   [Wb-turns]

        where the sum runs over all branches in *branch_turns* and ``Nₖ``
        is the signed turn count (positive = winding aligned with the
        assumed positive branch flux direction).

        Parameters
        ----------
        winding_id : any hashable
            Identifier for this winding (e.g. ``'phase_a'``, ``1``).
        branch_turns : dict[int, float]
            Mapping ``{branch_id: N_turns}`` where N_turns is signed.

        Example
        -------
        A 100-turn coil linking branch 3 in the positive direction and
        branch 7 in the negative direction::

            mec.add_winding('coil', {3: +100, 7: -100})
        """
        self._windings[winding_id] = _Winding(
            winding_id=winding_id,
            branch_turns=dict(branch_turns),
        )
        return self

    # ── state mutation (update between solves) ────────────────────────────

    def update_mmf(self, branch: int, mmf: float) -> None:
        """Update the MMF source of an existing branch [A-turns]."""
        self._branches[branch].mmf = mmf

    def update_permeance(self, branch: int, permeance: float) -> None:
        """
        Update the permeance of a linear/nodal branch [Wb/A-turns].

        This is the primary mechanism for motion simulation (Horvath 2018):
        pre-define all possible air-gap connections, then sweep rotor
        position by calling ``update_permeance`` followed by ``solve()``.
        Air-gap permeances approach zero (not infinity) as parts move out
        of alignment, so the circuit topology never changes.
        """
        self._branches[branch].permeance = permeance

    # ── solve ─────────────────────────────────────────────────────────────

    def solve(self, phi0: Optional[Dict[int, float]] = None) -> MECSolution:
        """
        Solve the MEC via Newton-Raphson iteration.

        Parameters
        ----------
        phi0 : dict[int, float], optional
            Initial guess ``{branch_id: flux_Wb}`` for mesh branches.

        Returns
        -------
        MECSolution
        """
        mesh_b, reluctance_b, nodal_b = self._classify()

        Nem = len(mesh_b)
        Nen = len(nodal_b)
        Ntot = Nem + Nen

        mesh_ids = sorted(b.branch_id for b in mesh_b)
        nodal_ids = sorted(b.branch_id for b in nodal_b)

        mesh_idx = {bid: i for i, bid in enumerate(mesh_ids)}
        nodal_idx = {bid: i + Nem for i, bid in enumerate(nodal_ids)}

        # ── initial flux vector ──────────────────────────────────────────
        Phi = np.zeros(Ntot)
        if phi0:
            for bid, val in phi0.items():
                if bid in mesh_idx:
                    Phi[mesh_idx[bid]] = val

        # ── compute scale factor once from the initial (linear) assembly ──
        # This follows Horvath (2018): fix s before the NR loop so the
        # coordinate system is consistent across all iterations.
        s = self._compute_scale(
            mesh_b, reluctance_b, nodal_b, mesh_ids, nodal_ids, mesh_idx, nodal_idx
        )

        # ── Newton-Raphson ───────────────────────────────────────────────
        converged = False
        n_iter = 0
        residual = float("inf")
        R_eff_map: Dict[int, float] = {}
        Fs_eff_map: Dict[int, float] = {}

        for iteration in range(self.max_iter):
            Phi_prev = Phi.copy()

            # Linearise nonlinear reluctance branches at current Phi
            for b in reluctance_b:
                phi_b = self._branch_flux(b, Phi, mesh_idx, nodal_idx)
                R_eff, Fs_corr = self._linearise_branch(b, phi_b)
                R_eff_map[b.branch_id] = R_eff
                Fs_eff_map[b.branch_id] = b.mmf + Fs_corr

            # Nodal branches are linear — constant R
            for b in nodal_b:
                P = b.permeance or 0.0
                R_eff_map[b.branch_id] = 1.0 / P if P != 0 else 1e18
                Fs_eff_map[b.branch_id] = b.mmf

            # Assemble and solve
            A, rhs = self._assemble(
                Nem,
                Nen,
                mesh_ids,
                nodal_ids,
                mesh_idx,
                nodal_idx,
                mesh_b,
                reluctance_b,
                nodal_b,
                R_eff_map,
                Fs_eff_map,
                s,
            )
            try:
                x = np.linalg.solve(A, rhs)
            except np.linalg.LinAlgError:
                x = np.linalg.lstsq(A, rhs, rcond=None)[0]

            # Unscale
            Phi_new = np.empty(Ntot)
            Phi_new[:Nem] = x[:Nem]
            if Nen > 0:
                Phi_new[Nem:] = x[Nem:] / s

            # Convergence check (MEC 3.2 criterion applied to scaled vars)
            dPhi = Phi_new - Phi_prev
            norm_dPhi = float(np.linalg.norm(dPhi))
            norm_avg = 0.5 * float(np.linalg.norm(Phi_new + Phi_prev))
            residual = norm_dPhi - (self.rtol * norm_avg + self.atol)

            Phi = Phi_new
            n_iter = iteration + 1

            if residual <= 0.0:
                converged = True
                break

        # ── post-process ──────────────────────────────────────────────────
        return self._build_solution(
            Phi,
            mesh_ids,
            nodal_ids,
            mesh_idx,
            nodal_idx,
            mesh_b,
            reluctance_b,
            nodal_b,
            R_eff_map,
            Fs_eff_map,
            converged,
            n_iter,
            abs(residual),
        )

    # ── internal: classification ──────────────────────────────────────────

    def _check_new(self, branch: int) -> None:
        if branch in self._branches:
            raise ValueError(f"Branch {branch} already exists.")

    def _classify(self):
        mesh_b = [b for b in self._branches.values() if b.btype == BranchType.MESH]
        reluctance_b = [b for b in self._branches.values() if b.btype == BranchType.RELUCTANCE]
        nodal_b = [b for b in self._branches.values() if b.btype == BranchType.NODAL]
        return mesh_b, reluctance_b, nodal_b

    # ── internal: scale factor ────────────────────────────────────────────

    def _compute_scale(
        self,
        mesh_b,
        reluctance_b,
        nodal_b,
        mesh_ids,
        nodal_ids,
        mesh_idx,
        nodal_idx,
    ) -> float:
        """
        Return the scaling factor *s* for the nodal block.

        If ``phi_base`` / ``F_base`` are set, use the per-unit approach
        (Horvath 2018):  s = F_base / phi_base  (= R_base).

        Otherwise compute ``s = √(mean|A₁₁| / mean|A₂₂|)`` from the
        *initial* (all-linear) assembly and hold it fixed for the entire
        Newton-Raphson sequence.
        """
        Nem = len(mesh_b)
        Nen = len(nodal_b)

        if Nen == 0:
            return 1.0

        # ── per-unit (physics-based, preferred) ──────────────────────────
        if self.phi_base is not None:
            assert self.F_base is not None
            return self.F_base / self.phi_base  # = R_base

        # ── heuristic from initial linear assembly ───────────────────────
        # Use R0 (not R_eff) for all reluctance branches at zero flux
        R_eff_init: Dict[int, float] = {}
        Fs_eff_init: Dict[int, float] = {}
        for b in reluctance_b:
            R0, _ = self._linearise_branch(b, 0.0)
            R_eff_init[b.branch_id] = R0
            Fs_eff_init[b.branch_id] = b.mmf
        for b in nodal_b:
            P = b.permeance or 0.0
            R_eff_init[b.branch_id] = 1.0 / P if P != 0 else 1e18
            Fs_eff_init[b.branch_id] = b.mmf

        A_init, _ = self._assemble(
            Nem,
            Nen,
            mesh_ids,
            nodal_ids,
            mesh_idx,
            nodal_idx,
            mesh_b,
            reluctance_b,
            nodal_b,
            R_eff_init,
            Fs_eff_init,
            s=1.0,  # un-scaled assembly to measure block magnitudes
        )
        a11 = A_init[:Nem, :Nem]
        a22 = A_init[Nem:, Nem:]
        mean11 = np.mean(np.abs(a11[a11 != 0])) if np.any(a11 != 0) else 1.0
        mean22 = np.mean(np.abs(a22[a22 != 0])) if np.any(a22 != 0) else 1.0
        return math.sqrt(mean11 / mean22) if mean22 != 0 else 1.0

    # ── internal: branch flux ─────────────────────────────────────────────

    def _branch_flux(
        self,
        b: _Branch,
        Phi: np.ndarray,
        mesh_idx: Dict[int, int],
        nodal_idx: Dict[int, int],
    ) -> float:
        """Net flux through branch *b* from the current Φ vector."""
        phi_b = 0.0
        for m, o in zip(b.meshes, b.orientations):
            for bid, idx in mesh_idx.items():
                if self._branches[bid].mesh_id == m:
                    phi_b += o * Phi[idx]
                    break
        if b.branch_id in nodal_idx:
            phi_b += Phi[nodal_idx[b.branch_id]]
        return phi_b

    # ── internal: NR linearisation ────────────────────────────────────────

    def _linearise_branch(self, b: _Branch, phi_b: float) -> Tuple[float, float]:
        """
        Return *(R_eff, Fs_corr)* for Newton-Raphson linearisation.

        The corrected system is:  ``R_eff·Φ_new = Fs_coil + Fs_corr``

        For a pre-computed linear branch ``Fs_corr = 0``.

        For a nonlinear branch (Horvath 2018 / MEC 3.2):

            B₀     = (Φ₀ − Φs) / A
            R₀     = l / (μ(B₀)·A)
            S₀     = (dμ/dB·B₀) / μ
            R_eff  = R₀·(1 − S₀)
            Fs_corr = −R₀·(S₀·Φ₀ − Φs)

        which at convergence (Φ* = Φ₀) satisfies R₀·(Φ* − Φs) = Fs.
        """
        if b.permeance is not None:
            R0 = 1.0 / b.permeance if b.permeance != 0.0 else 1e18
            return R0, 0.0

        # Nonlinear branch
        B0 = (phi_b - b.phi_source) / b.area if b.area != 0 else 0.0
        assert b.model is not None, "Reluctance branch must have a permeability model"
        mu_val = b.model.mu(B0)

        if mu_val <= 0 or b.length == 0 or b.area == 0:
            return 0.0, 0.0

        R0 = b.length / (mu_val * b.area)
        dmu = b.model.dmu_dB(B0)
        S0 = dmu * (phi_b - b.phi_source) / (mu_val * b.area)

        R_eff = R0 * (1.0 - S0)
        Fs_corr = -R0 * (S0 * phi_b - b.phi_source)
        return R_eff, Fs_corr

    # ── internal: assembly ────────────────────────────────────────────────

    def _assemble(
        self,
        Nem: int,
        Nen: int,
        mesh_ids: List[int],
        nodal_ids: List[int],
        mesh_idx: Dict[int, int],
        nodal_idx: Dict[int, int],
        mesh_b: List[_Branch],
        reluctance_b: List[_Branch],
        nodal_b: List[_Branch],
        R_eff_map: Dict[int, float],
        Fs_eff_map: Dict[int, float],
        s: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build the (Nem+Nen)×(Nem+Nen) scaled system and RHS.

        Block structure (Horvath 2018, Eq. 7):

            ⎡ Â_R   D₁/s ⎤ ⎡ φ̂   ⎤   ⎡ F̂ ⎤
            ⎢             ⎥ ⎢     ⎥ = ⎢   ⎥
            ⎣ D₂·s  Â_P  ⎦ ⎣ û·s ⎦   ⎣ 0  ⎦

        Mesh rows (KVL): Σ R_eff·Φ = F_source + Σ Fs_eff
        Nodal rows (KCL): Σ P·u = 0  (linear, Horvath eq. 5)

        The scaling factor *s* is applied to the nodal columns and rows
        so that the two diagonal blocks have comparable magnitudes.
        """
        Ntot = Nem + Nen
        A = np.zeros((Ntot, Ntot))
        rhs = np.zeros(Ntot)

        def mesh_col(m: int) -> int:
            for bid in mesh_ids:
                if self._branches[bid].mesh_id == m:
                    return mesh_idx[bid]
            raise KeyError(f"No mesh branch for mesh {m}")

        # ── KVL rows (one per mesh branch) ──────────────────────────────
        for mb in mesh_b:
            row = mesh_idx[mb.branch_id]

            # Mesh branch with reluctance (rare, e.g. coil on a short path)
            if mb.permeance is not None:
                R_mb = 1.0 / mb.permeance if mb.permeance != 0 else 0.0
                A[row, row] += R_mb

            # MMF source on this mesh branch
            rhs[row] += mb.mmf

            # Reluctance branches belonging to this mesh
            for b in reluctance_b:
                if mb.mesh_id not in b.meshes:
                    continue
                R_eff = R_eff_map[b.branch_id]
                Fs_eff = Fs_eff_map[b.branch_id]
                orient_self = b.orientations[b.meshes.index(mb.mesh_id)]

                # Diagonal entry
                A[row, row] += R_eff  # orient² = 1

                # Off-diagonal entries (other meshes sharing this branch)
                for other_m, other_o in zip(b.meshes, b.orientations):
                    if other_m == mb.mesh_id:
                        continue
                    A[row, mesh_col(other_m)] += orient_self * other_o * R_eff

                rhs[row] += orient_self * Fs_eff

        # ── KCL rows (one per nodal branch) ─────────────────────────────
        for nb in nodal_b:
            row = nodal_idx[nb.branch_id]
            P = nb.permeance or 0.0
            R_nb = 1.0 / P if P != 0 else 1e18
            col = nodal_idx[nb.branch_id]

            A[row, col] += R_nb
            rhs[row] += nb.mmf

            for m, o in zip(nb.meshes, nb.orientations):
                A[row, mesh_col(m)] += o * R_nb

        # ── apply scaling to nodal block ─────────────────────────────────
        if Nen > 0 and s != 1.0:
            A[:, Nem:] *= s  # nodal columns → solution is û·s
            A[Nem:, :] *= s  # nodal rows    → equation scaled by s
            rhs[Nem:] *= s

        return A, rhs

    # ── internal: build solution ──────────────────────────────────────────

    def _build_solution(
        self,
        Phi: np.ndarray,
        mesh_ids: List[int],
        nodal_ids: List[int],
        mesh_idx: Dict[int, int],
        nodal_idx: Dict[int, int],
        mesh_b: List[_Branch],
        reluctance_b: List[_Branch],
        nodal_b: List[_Branch],
        R_eff_map: Dict[int, float],
        Fs_eff_map: Dict[int, float],
        converged: bool,
        n_iter: int,
        residual: float,
    ) -> MECSolution:
        phi_mesh = {bid: float(Phi[mesh_idx[bid]]) for bid in mesh_ids}
        phi_nodal = {bid: float(Phi[nodal_idx[bid]]) for bid in nodal_ids}

        phi_branches: Dict[int, float] = {}
        mmf_branches: Dict[int, float] = {}

        # Mesh branches
        for b in mesh_b:
            phi_branches[b.branch_id] = phi_mesh[b.branch_id]
            mmf_branches[b.branch_id] = b.mmf

        # Reluctance branches
        for b in reluctance_b:
            phi_b = self._branch_flux(b, Phi, mesh_idx, nodal_idx)
            phi_branches[b.branch_id] = phi_b
            R_eff = R_eff_map.get(b.branch_id, 0.0)
            Fs_eff = Fs_eff_map.get(b.branch_id, b.mmf)
            mmf_branches[b.branch_id] = Fs_eff - R_eff * phi_b

        # Nodal branches
        for b in nodal_b:
            phi_b = self._branch_flux(b, Phi, mesh_idx, nodal_idx)
            phi_branches[b.branch_id] = phi_b
            Fs_eff = Fs_eff_map.get(b.branch_id, b.mmf)
            R_nb = R_eff_map.get(b.branch_id, 0.0)
            mmf_branches[b.branch_id] = Fs_eff - R_nb * phi_b

        # Field energy: Wf = ½ Σ R_eff · Φ²  (always positive)
        Wf = sum(
            0.5 * R_eff_map.get(b.branch_id, 0.0) * phi_branches[b.branch_id] ** 2
            for b in reluctance_b
        )

        # Flux linkages for registered windings
        flux_linkages: Dict[Any, float] = {}
        for wid, winding in self._windings.items():
            lam = sum(N * phi_branches.get(bid, 0.0) for bid, N in winding.branch_turns.items())
            flux_linkages[wid] = lam

        return MECSolution(
            phi_mesh=phi_mesh,
            phi_nodal=phi_nodal,
            phi_branches=phi_branches,
            mmf_branches=mmf_branches,
            flux_linkages=flux_linkages,
            converged=converged,
            n_iterations=n_iter,
            residual=residual,
            field_energy=Wf,
            phi_base=self.phi_base,
            F_base=self.F_base,
        )
