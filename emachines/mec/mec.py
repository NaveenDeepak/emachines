"""emachines MEC solver module.

Auto-generated from nbdev notebooks:
- nbs/04_material_models.ipynb
- nbs/04_mec_solver.ipynb
- nbs/04_results.ipynb
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy.interpolate import CubicSpline

__all__ = [
    "PermeabilityModel",
    "LinearPermeabilityModel",
    "SplinePermeabilityModel",
    "ShanesudhoffModel",
    "BranchType",
    "MEC",
    "MECSolution",
]


MU0 = 4e-7 * np.pi  # H/m


class PermeabilityModel(ABC):
    """Abstract interface for permeability models used by the MEC solver."""

    @abstractmethod
    def mu(self, B: float) -> float:
        r"""Return permeability μ [H/m] at flux density *B* [T]."""

    @abstractmethod
    def dmu_dB(self, B: float) -> float:
        r"""Return dμ/dB [H/m·T⁻¹] at flux density *B* [T]."""
        pass


class LinearPermeabilityModel(PermeabilityModel):
    """
    Constant permeability μ = μ₀ · μᵣ.

    Parameters
    ----------
    mu_r:
        Relative permeability (dimensionless). Default is 1 (free space).
    """

    def __init__(self, mu_r: float = 1.0) -> None:
        if mu_r <= 0:
            raise ValueError(f"mu_r must be positive, got {mu_r}")
        self._mu = MU0 * mu_r

    def mu(self, B: float) -> float:
        """Return constant permeability."""
        return self._mu

    def dmu_dB(self, B: float) -> float:
        """Derivative is zero for linear model."""
        return 0.0


class SplinePermeabilityModel(PermeabilityModel):
    """
    Permeability model built from tabulated B-H data via a cubic spline.

    The data are assumed to start at (H=0, B=0). Negative-B evaluation
    uses odd symmetry: μ(−|B|) = μ(|B|), dμ/dB(−|B|) = −dμ/dB(|B|).

    Parameters
    ----------
    H_data:
        Array of field strengths [A/m], monotonically increasing from 0.
    B_data:
        Corresponding flux densities [T].

    Class methods
    -------------
    from_steel_grade(grade)
        Convenience constructor that reads the ``bh_data`` DataFrame of an
        :class:`emachines.magnetics.SteelGrade` instance.
    """

    def __init__(
        self,
        H_data,  # Sequence[float]
        B_data,  # Sequence[float]
    ) -> None:
        H = np.asarray(H_data, dtype=float)
        B = np.asarray(B_data, dtype=float)

        if H.shape != B.shape:
            raise ValueError("H_data and B_data must have the same length.")
        if H[0] != 0.0 or B[0] != 0.0:
            raise ValueError("B-H data must start at (H=0, B=0).")
        if not np.all(np.diff(H) > 0):
            raise ValueError("H_data must be strictly increasing.")

        # μ(B) = μ₀ * H/B — defined for B > 0 only
        B_pos = B[1:]
        H_pos = H[1:]
        mu_pos = MU0 * H_pos / B_pos

        # Prepend B=0 using initial linear slope
        mu_at_0 = MU0 * H_pos[0] / B_pos[0]
        B_knots = np.concatenate([[0.0], B_pos])
        mu_knots = np.concatenate([[mu_at_0], mu_pos])

        self._B_max = B_knots[-1]
        self._mu_min = mu_knots[-1]
        self._cs = CubicSpline(B_knots, mu_knots)
        self._cs_deriv = self._cs.derivative()

    @classmethod
    def from_steel_grade(cls, grade) -> "SplinePermeabilityModel":
        """
        Create a SplinePermeabilityModel from a
        :class:`emachines.magnetics.SteelGrade`.
        """
        df = grade.bh_data
        # Find H and B columns by substring match
        h_col = next(c for c in df.columns if "H" in c.upper() and "B" not in c.upper())
        b_col = next(c for c in df.columns if c.upper().startswith("B"))
        H = df[h_col].to_numpy(dtype=float)
        B = df[b_col].to_numpy(dtype=float)
        # Sort and ensure starts at origin
        order = np.argsort(H)
        H, B = H[order], B[order]
        if H[0] != 0:
            H = np.concatenate([[0.0], H])
            B = np.concatenate([[0.0], B])
        return cls(H, B)

    def mu(self, B: float) -> float:
        """Return permeability at flux density B."""
        absB = abs(B)
        if absB >= self._B_max:
            return self._mu_min
        return float(self._cs(absB))

    def dmu_dB(self, B: float) -> float:
        """Return derivative dμ/dB at flux density B."""
        absB = abs(B)
        if absB >= self._B_max:
            return 0.0
        sign = 1.0 if B >= 0 else -1.0
        return sign * float(self._cs_deriv(absB))


class ShanesudhoffModel(PermeabilityModel):
    """
    Shane-Sudhoff (2010) analytical permeability model.

    Parameters
    ----------
    mu_r:
        Initial relative permeability.
    a, b, gamma:
        Sequences of equal length, one entry per term.
    mu0:
        Permeability of free space [H/m]. Default: 4π×10⁻⁷.

    Class methods
    -------------
    ferrite_3C90()
        Returns a ShanesudhoffModel with the 3C90 ferrite parameters from
        the MEC 3.2 toolbox example (Sudhoff, 2014).
    """

    def __init__(
        self,
        mu_r: float,
        a,  # Sequence[float]
        b,  # Sequence[float]
        gamma,  # Sequence[float]
        mu0: Optional[float] = None,
    ) -> None:
        if mu0 is None:
            mu0 = MU0
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        gamma = np.asarray(gamma, dtype=float)
        if not (len(a) == len(b) == len(gamma)):
            raise ValueError("a, b, gamma must all have the same length.")

        self._mu_r = float(mu_r)
        self._a = a
        self._b = b
        self._mu0 = float(mu0)

        # Pre-compute derived constants
        self._d = a / b
        self._z = (gamma - 1.0) / gamma
        self._e = 1.0 - self._z
        self._h = self._mu0 * a * self._z * b

    def _f_and_df(self, absB: float):
        """Return (f, df/d|B|) at |B|."""
        eb = np.exp(-self._b * absB)
        arg = self._e + self._z * eb

        sum_terms = np.sum(self._a * absB + self._d * np.log(arg))
        f = self._mu_r / (self._mu_r - 1.0) + sum_terms

        dlog_dabs = -self._d * self._z * self._b * eb / arg
        df = np.sum(self._a + dlog_dabs)

        return f, df

    def mu(self, B: float) -> float:
        """Return permeability at flux density B."""
        absB = abs(float(B))
        f, _ = self._f_and_df(absB)
        return self._mu0 * f / (f - 1.0)

    def dmu_dB(self, B: float) -> float:
        """Return derivative dμ/dB at flux density B."""
        absB = abs(float(B))
        f, df = self._f_and_df(absB)
        fm1 = f - 1.0
        sign = 1.0 if B >= 0 else -1.0
        return -self._mu0 * df / (fm1 * fm1) * sign

    @classmethod
    def ferrite_3C90(cls) -> "ShanesudhoffModel":
        """
        3C90 ferrite parameters from MEC 3.2 toolbox (Sudhoff, 2014).

        μᵣ = 22 340.9259
        """
        return cls(
            mu_r=22340.9259,
            a=[1.1542, 0.049742, 0.049644, 0.041155],
            b=[431.1763, 2.29503, 15.04824, 74.28908],
            gamma=[0.4742, 2.7955, 0.59862, 0.43996],
        )


class BranchType:
    """Branch type identifiers for the MEC."""

    MESH = "mesh"
    RELUCTANCE = "reluctance"
    NODAL = "nodal"


@dataclass
class _Branch:
    """Internal representation of a single MEC branch."""

    branch_id: int
    btype: str
    mesh_id: Optional[int] = None
    mmf: float = 0.0
    length: float = 0.0
    area: float = 0.0
    model: Optional[Any] = None
    phi_source: float = 0.0
    meshes: List[int] = field(default_factory=list)
    orientations: List[int] = field(default_factory=list)
    permeance: Optional[float] = None
    node_from: Optional[int] = None
    node_to: Optional[int] = None


@dataclass
class _Winding:
    """Internal descriptor of a multi-turn winding."""

    winding_id: Any
    branch_turns: Dict[int, float] = field(default_factory=dict)


MU0 = 4e-7 * math.pi


class MEC:
    """
    Magnetic Equivalent Circuit builder and Newton-Raphson solver.

    Parameters
    ----------
    phi_base : float, optional
        Base flux [Wb] for per-unit scaling (Horvath 2018).
        Typically ``B_base * A_base`` where ``B_base ≈ 1.6 T``.
        If *None*, a heuristic scale is used instead.
    F_base : float, optional
        Base MMF [A-turns] for per-unit scaling.
        Must be supplied together with *phi_base* or not at all.
    rtol, atol : float
        Newton-Raphson convergence tolerances on ‖ΔΦ‖:
        ``‖ΔΦ‖ ≤ rtol·½‖Φₖ + Φₖ₋₁‖ + atol``
    max_iter : int
        Maximum Newton-Raphson iterations.
    """

    def __init__(
        self,
        phi_base: Optional[float] = None,
        F_base: Optional[float] = None,
        rtol: float = 1e-6,
        atol: float = 1e-9,
        max_iter: int = 20,
    ) -> None:
        if (phi_base is None) != (F_base is None):
            raise ValueError("phi_base and F_base must both be specified or both be None.")

        self.phi_base = phi_base
        self.F_base = F_base
        self.rtol = rtol
        self.atol = atol
        self.max_iter = max_iter

        self._branches: Dict[int, _Branch] = {}
        self._windings: Dict[Any, _Winding] = {}
        self._next_branch_id = 0
        self._mesh_count = 0
        self._node_count = 0

    def add_mesh_branch(
        self,
        branch: int,
        mesh: int = 1,
        mmf: float = 0.0,
    ) -> int:
        """Add a mesh (loop current) branch with an explicit branch ID.

        Parameters
        ----------
        branch : int
            User-assigned branch ID (must be unique).
        mesh : int
            Mesh number label (informational; branch ID is used for topology).
        mmf : float
            Magnetomotive force source [A-turns].

        Returns
        -------
        branch_id : int
            The branch ID assigned (same as *branch*).
        """
        self._branches[branch] = _Branch(
            branch_id=branch,
            btype=BranchType.MESH,
            mesh_id=mesh,
            mmf=mmf,
        )
        self._mesh_count += 1
        return branch

    def add_linear_branch(
        self,
        branch: int,
        permeance: float,
        meshes: Sequence[int] = (),
        orientations: Sequence[int] = (),
        mmf: float = 0.0,
    ) -> int:
        """Add a linear (fixed permeance) branch with an explicit branch ID.

        Parameters
        ----------
        branch : int
            User-assigned branch ID (must be unique).
        permeance : float
            Fixed permeance P = μA/l [Wb/A-turns].
        meshes : sequence of int
            Branch IDs of the mesh branches this branch belongs to.
        orientations : sequence of int
            +1 or -1 for each mesh (flux direction relative to mesh).
        mmf : float
            Magnetomotive force source [A-turns].

        Returns
        -------
        branch_id : int
        """
        self._branches[branch] = _Branch(
            branch_id=branch,
            btype=BranchType.RELUCTANCE,
            permeance=permeance,
            mmf=mmf,
            meshes=list(meshes),
            orientations=list(orientations),
        )
        return branch

    def add_nonlinear_branch(
        self,
        branch: int,
        length: float,
        area: float,
        model: Any,
        meshes: Sequence[int] = (),
        orientations: Sequence[int] = (),
        mmf: float = 0.0,
        phi_source: float = 0.0,
    ) -> int:
        """Add a nonlinear (model-based) reluctance branch with an explicit branch ID.

        Parameters
        ----------
        branch : int
            User-assigned branch ID (must be unique).
        length : float
            Core length [m].
        area : float
            Cross-sectional area [m²].
        model : PermeabilityModel
            Permeability model with mu() and dmu_dB() methods.
        meshes : sequence of int
            Branch IDs of mesh branches this branch belongs to.
        orientations : sequence of int
            +1 or -1 for each mesh.
        mmf : float
            Magnetomotive force source [A-turns].
        phi_source : float
            PM flux source [Wb].

        Returns
        -------
        branch_id : int
        """
        self._branches[branch] = _Branch(
            branch_id=branch,
            btype=BranchType.RELUCTANCE,
            length=length,
            area=area,
            model=model,
            mmf=mmf,
            phi_source=phi_source,
            meshes=list(meshes),
            orientations=list(orientations),
        )
        return branch

    def add_reluctance_branch(
        self,
        length: float,
        area: float,
        model: Any,
        meshes: Sequence[int] = (),
        orientations: Sequence[int] = (),
        mmf: float = 0.0,
        phi_source: float = 0.0,
    ) -> int:
        """Add a reluctance (nonlinear magnetic) branch.

        Parameters
        ----------
        length : float
            Core length [m].
        area : float
            Cross-sectional area [m²].
        model : PermeabilityModel
            Permeability model (must have mu() and dmu_dB() methods).
        meshes : sequence of int
            Mesh IDs that cross this branch (±1).
        orientations : sequence of int
            +1 or -1 for each mesh (orientation relative to branch flux).
        mmf : float
            Magnetomotive force source [A-turns].
        phi_source : float
            PM (Norton equivalent) flux source [Wb].

        Returns
        -------
        branch_id : int
        """
        bid = self._next_branch_id
        self._branches[bid] = _Branch(
            branch_id=bid,
            btype=BranchType.RELUCTANCE,
            length=length,
            area=area,
            model=model,
            mmf=mmf,
            phi_source=phi_source,
            meshes=list(meshes),
            orientations=list(orientations),
        )
        self._next_branch_id += 1
        return bid

    def add_nodal_branch(
        self,
        permeance: float,
        node_from: int,
        node_to: int,
        mmf: float = 0.0,
    ) -> int:
        """Add a nodal (linear permeance) branch.

        Parameters
        ----------
        permeance : float
            Fixed permeance P = A/μℓ [Wb/A-turns].
        node_from : int
            Starting magnetic node.
        node_to : int
            Ending magnetic node.
        mmf : float
            Magnetomotive force source.

        Returns
        -------
        branch_id : int
        """
        bid = self._next_branch_id
        self._branches[bid] = _Branch(
            branch_id=bid,
            btype=BranchType.NODAL,
            node_from=node_from,
            node_to=node_to,
            permeance=permeance,
            mmf=mmf,
        )
        self._node_count = max(self._node_count, node_from + 1, node_to + 1)
        self._next_branch_id += 1
        return bid

    def add_winding(
        self,
        winding_id: Any,
        branch_turns: Dict[int, float],
    ) -> None:
        """Register a winding for flux linkage calculation.

        Parameters
        ----------
        winding_id : Any
            Unique identifier for this winding.
        branch_turns : dict
            Mapping {branch_id: signed_turn_count}.
            Positive = aligned with branch flux direction.
        """
        self._windings[winding_id] = _Winding(
            winding_id=winding_id,
            branch_turns=dict(branch_turns),
        )

    def solve(self) -> Any:  # Returns MECSolution
        """Solve the MEC using Newton-Raphson iteration.

        Returns
        -------
        solution : MECSolution
            Solution object with flux, MMF, convergence info.
        """
        # Separate branches by type
        mesh_b = [b for b in self._branches.values() if b.btype == BranchType.MESH]
        reluctance_b = [b for b in self._branches.values() if b.btype == BranchType.RELUCTANCE]

        # Initialize
        n_mesh = len(mesh_b)
        n_nodal = self._node_count
        n_vars = n_mesh + n_nodal

        # Index mappings
        mesh_idx = {b.branch_id: i for i, b in enumerate(mesh_b)}

        Phi = np.zeros(n_vars)

        # Newton-Raphson loop
        converged = False
        residual = float("inf")

        for n_iter in range(self.max_iter):
            # Assemble system matrix and RHS
            J = np.zeros((n_vars, n_vars))
            F_vec = np.zeros(n_vars)

            R_eff_map = {}  # For post-processing
            Fs_eff_map = {}  # For post-processing

            # Mesh equations: one equation per mesh
            for i, mesh_branch in enumerate(mesh_b):
                # Sum MMF drops around mesh loop
                mmf_sum = mesh_branch.mmf

                for reluctance in reluctance_b:
                    if mesh_branch.branch_id in reluctance.meshes:
                        # This reluctance crosses this mesh
                        idx_in_mesh = reluctance.meshes.index(mesh_branch.branch_id)
                        orientation = reluctance.orientations[idx_in_mesh]

                        # Compute flux through this reluctance
                        phi_b = self._branch_flux_simple(reluctance, Phi, mesh_idx)

                        # Linear branch (fixed permeance) or nonlinear (model-based)
                        if reluctance.model is None and reluctance.permeance is not None:
                            R_eff = (
                                1.0 / reluctance.permeance
                                if reluctance.permeance > 0
                                else float("inf")
                            )
                            Fs_eff = reluctance.mmf
                        elif reluctance.model is not None:
                            B = phi_b / reluctance.area if reluctance.area > 0 else 0
                            mu = reluctance.model.mu(B)
                            dmu_dB = reluctance.model.dmu_dB(B)
                            R0 = (
                                reluctance.length / (mu * reluctance.area)
                                if mu > 0 and reluctance.area > 0
                                else float("inf")
                            )
                            S0 = (dmu_dB * B / mu) if mu > 0 and abs(mu) > 1e-15 else 0
                            R_eff = R0 * (1 - S0) if R0 < float("inf") else float("inf")
                            Fs_eff = reluctance.mmf - R0 * (S0 * phi_b - reluctance.phi_source)
                        else:
                            R_eff = float("inf")
                            Fs_eff = reluctance.mmf

                        R_eff_map[reluctance.branch_id] = R_eff
                        Fs_eff_map[reluctance.branch_id] = Fs_eff

                        # MMF drop in this mesh's direction = orientation * R * phi_b
                        mmf_sum -= orientation * R_eff * phi_b - Fs_eff

                        # Full Jacobian: accounts for off-diagonal coupling
                        # ∂(orientation_i * R * phi_b) / ∂Phi_j = orientation_i * R * orientation_j
                        if R_eff < float("inf"):
                            for m_id, o_j in zip(reluctance.meshes, reluctance.orientations):
                                if m_id in mesh_idx:
                                    J[i, mesh_idx[m_id]] -= orientation * R_eff * o_j

                F_vec[i] = mmf_sum

            # Solve for flux update
            try:
                dPhi = np.linalg.solve(J + np.eye(n_vars) * 1e-12, F_vec)
            except np.linalg.LinAlgError:
                # Singular matrix, use pseudoinverse
                dPhi = np.linalg.pinv(J) @ F_vec

            # Update flux
            Phi_old = Phi.copy()
            Phi -= dPhi

            # Check convergence
            norm_Phi: float = float(0.5 * (np.linalg.norm(Phi) + np.linalg.norm(Phi_old)))
            residual = float(np.linalg.norm(dPhi))

            tol = self.rtol * norm_Phi + self.atol
            if residual <= tol:
                converged = True
                break

        # Extract results
        phi_mesh = {b.branch_id: Phi[mesh_idx[b.branch_id]] for b in mesh_b}
        phi_nodal: Dict[int, float] = {}
        phi_branches = {}
        mmf_branches = {}

        # Reconstruct branch fluxes and MMF drops
        for b in mesh_b:
            phi_branches[b.branch_id] = phi_mesh[b.branch_id]
            mmf_branches[b.branch_id] = b.mmf

        for b in reluctance_b:
            phi_b = self._branch_flux_simple(b, Phi, mesh_idx)
            phi_branches[b.branch_id] = phi_b
            R_eff = R_eff_map.get(b.branch_id, 0.0)
            Fs_eff = Fs_eff_map.get(b.branch_id, b.mmf)
            mmf_branches[b.branch_id] = Fs_eff - R_eff * phi_b

        # Calculate flux linkages
        flux_linkages = {}
        for wid, winding in self._windings.items():
            lam = sum(N * phi_branches.get(bid, 0.0) for bid, N in winding.branch_turns.items())
            flux_linkages[wid] = lam

        # Field energy
        Wf = sum(
            0.5 * R_eff_map.get(b.branch_id, 0.0) * phi_branches[b.branch_id] ** 2
            for b in reluctance_b
        )

        # Import here to avoid circular dependency
        from .result import MECSolution

        return MECSolution(
            phi_mesh=phi_mesh,
            phi_nodal=phi_nodal,
            phi_branches=phi_branches,
            mmf_branches=mmf_branches,
            flux_linkages=flux_linkages,
            converged=converged,
            n_iterations=n_iter + 1,
            residual=residual,
            field_energy=Wf,
            phi_base=self.phi_base,
            F_base=self.F_base,
        )

    def _branch_flux_simple(self, branch, Phi, mesh_idx):
        """Compute flux through a branch from mesh variables."""
        phi = 0.0
        for mesh_id, orientation in zip(branch.meshes, branch.orientations):
            if mesh_id in mesh_idx:
                phi += orientation * Phi[mesh_idx[mesh_id]]
        return phi


from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MECSolution:
    """
    Solution of a Magnetic Equivalent Circuit.

    All branch quantities are stored in dictionaries keyed by branch number
    (the integer assigned when the branch was added to the MEC).

    Attributes
    ----------
    phi_mesh : dict[int, float]
        Mesh flux variables Φₘ [Wb]. One entry per mesh branch.
    phi_nodal : dict[int, float]
        Nodal flux variables Φₙ [Wb]. One entry per nodal branch.
    phi_branches : dict[int, float]
        Net flux through every branch [Wb].
    mmf_branches : dict[int, float]
        MMF drop across every branch [A-turns].
    flux_linkages : dict[Any, float]
        Winding flux linkages [Wb-turns]. Keys are winding IDs registered
        via :meth:`MEC.add_winding`. Empty if no windings were defined.
    converged : bool
        True if Newton-Raphson converged within the iteration limit.
    n_iterations : int
        Number of Newton-Raphson iterations performed.
    residual : float
        Final convergence residual ‖ΔΦ‖ (absolute, [Wb]).
    field_energy : float
        Stored magnetic field energy [J]
        Wf = ½ Σ R_eff · Φ²  (sum over reluctance branches).
    phi_base : float or None
        Base flux used for per-unit scaling [Wb].
    F_base : float or None
        Base MMF used for per-unit scaling [A-turns].
    """

    phi_mesh: Dict[int, float] = field(default_factory=dict)
    phi_nodal: Dict[int, float] = field(default_factory=dict)
    phi_branches: Dict[int, float] = field(default_factory=dict)
    mmf_branches: Dict[int, float] = field(default_factory=dict)
    flux_linkages: Dict[Any, float] = field(default_factory=dict)
    converged: bool = False
    n_iterations: int = 0
    residual: float = float("inf")
    field_energy: float = 0.0
    phi_base: Optional[float] = None
    F_base: Optional[float] = None

    def flux(self, branch: int) -> float:
        """Return the net flux through *branch* [Wb]."""
        return self.phi_branches.get(branch, 0.0)

    def mmf(self, branch: int) -> float:
        """Return the MMF drop across *branch* [A-turns]."""
        return self.mmf_branches.get(branch, 0.0)

    def flux_linkage(self, winding_id: Any) -> float:
        """
        Return the flux linkage of *winding_id* [Wb-turns].

        The winding must have been registered with :meth:`MEC.add_winding`
        before calling :meth:`MEC.solve`.

        Parameters
        ----------
        winding_id:
            The identifier used when the winding was added.

        Raises
        ------
        KeyError
            If *winding_id* was not registered.
        """
        return self.flux_linkages[winding_id]

    def __repr__(self) -> str:
        """Return string representation of solution."""
        status = "converged" if self.converged else "NOT converged"
        scaling = (
            f"pu(φ_base={self.phi_base:.3g})" if self.phi_base is not None else "heuristic-scaled"
        )
        return (
            f"MECSolution({status}, "
            f"iter={self.n_iterations}, "
            f"residual={self.residual:.3e}, "
            f"Wf={self.field_energy:.6g} J, "
            f"{scaling})"
        )
