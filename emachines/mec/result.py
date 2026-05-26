"""
MECSolution — result container returned by :meth:`MEC.solve`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

__all__ = ["MECSolution"]


@dataclass
class MECSolution:
    """
    Solution of a Magnetic Equivalent Circuit.

    All branch quantities are stored in dictionaries keyed by branch number
    (the integer assigned when the branch was added to the MEC).

    Attributes
    ----------
    phi_mesh : dict[int, float]
        Mesh flux variables Φₘ [Wb].  One entry per mesh branch.
    phi_nodal : dict[int, float]
        Nodal flux variables Φₙ [Wb].  One entry per nodal branch.
    phi_branches : dict[int, float]
        Net flux through every branch [Wb].
    mmf_branches : dict[int, float]
        MMF drop across every branch [A-turns].
    flux_linkages : dict[Any, float]
        Winding flux linkages [Wb-turns].  Keys are winding IDs registered
        via :meth:`MEC.add_winding`.  Empty if no windings were defined.
        λ = Σ_k  Nₖ · αₖ · Φ_branch_k
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
        Base flux used for per-unit scaling [Wb].  ``None`` if the heuristic
        scaling was used.
    F_base : float or None
        Base MMF used for per-unit scaling [A-turns].  ``None`` if the
        heuristic scaling was used.
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

    # ── convenience ───────────────────────────────────────────────────────

    def flux(self, branch: int) -> float:
        """Return the net flux through *branch* [Wb]."""
        return self.phi_branches[branch]

    def mmf(self, branch: int) -> float:
        """Return the MMF drop across *branch* [A-turns]."""
        return self.mmf_branches[branch]

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

    def __repr__(self) -> str:  # noqa: D105
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
