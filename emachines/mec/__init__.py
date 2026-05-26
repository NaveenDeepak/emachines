"""
emachines.mec — Magnetic Equivalent Circuit solver.

Quick start
-----------
.. code-block:: python

    from emachines.mec import MEC, ShanesudhoffModel

    mec = MEC()
    mec.add_mesh_branch(mmf=500.0)
    mec.add_reluctance_branch(
        length=0.05, area=1e-4,
        model=ShanesudhoffModel.ferrite_3C90(),
        meshes=[0], orientations=[1],
    )
    sol = mec.solve()
    print(f"Φ = {sol.flux(1)*1e6:.3f} µWb,  Wf = {sol.field_energy*1e6:.3f} µJ")

Public API
----------
MEC
    Builder / solver class.
MECSolution
    Result container (flux, MMF, field energy, convergence info).
PermeabilityModel
    Abstract base class for permeability models.
LinearPermeabilityModel
    Constant μ = μ₀·μᵣ.
SplinePermeabilityModel
    Cubic-spline fit to tabulated B-H data; integrates with
    :class:`emachines.magnetics.SteelGrade`.
ShanesudhoffModel
    Analytical Shane-Sudhoff (2010) model with 3C90 ferrite class method.
BranchType
    Branch type identifiers (MESH, RELUCTANCE, NODAL).
"""

from .mec import (
    MEC,
    BranchType,
    LinearPermeabilityModel,
    MECSolution,
    PermeabilityModel,
    ShanesudhoffModel,
    SplinePermeabilityModel,
)

__all__ = [
    "MEC",
    "MECSolution",
    "PermeabilityModel",
    "LinearPermeabilityModel",
    "SplinePermeabilityModel",
    "ShanesudhoffModel",
    "BranchType",
]

# ── quick reference ───────────────────────────────────────────────────────────
# Per-unit scaling (Horvath 2018):
#
#   A_base  = max cross-sectional area of any air-gap element  [m²]
#   B_base  = 1.6 T  (near saturation knee)
#   g       = air-gap length  [m]
#   P_base  = µ₀ * A_base / g
#   phi_base = B_base * A_base
#   F_base  = phi_base / P_base
#
#   mec = MEC(phi_base=phi_base, F_base=F_base)
#
# Motion (topology-invariant):
#   Pre-define all possible air-gap branches.
#   At each rotor position:
#       for each airgap branch b:
#           mec.update_permeance(b, µ0 * overlap_area(theta) / g)
#       sol = mec.solve()
#
# Flux linkage:
#   mec.add_winding('a', {3: +100, 7: -50})
#   sol = mec.solve()
#   lam_a = sol.flux_linkage('a')   # [Wb-turns]
