# Changelog

All notable changes to `emachines` will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- `emachines.winding.pattern` — `WindingPattern`: any stator winding as signed turns per
  phase, slot and named slot position (`slot_turns[phase, slot, position]`), with the coils
  that made it. Builders: `from_star_of_slots`, `distributed` (integer-slot lap, full or short
  pitch), `concentrated` (tooth coils on all teeth, side-by-side or over-under, or on alternate
  teeth), `from_slot_table` and `custom` (a list of `Coil`). Balance check, winding factors,
  series turns, parallel paths and a developed slot plot. `slot_positions` names the positions
  of each layout (`single`, `over_under` with 2 or n layers, `side_by_side`).
- `emachines.inductance.geometry` — `SlotGeometry` (open or semi-closed slot, conductor body
  tapered by `t` from parallel slot to parallel tooth, optional layer separator) and
  `StatorGeometry` (bore, air gap, stack, yoke, end-winding overhang; slot pitch, tooth width,
  outer radius). `regions()` maps each named position to its part of the slot: equal-copper-area
  radial layers, or side-by-side halves. Labelled stator and slot figures in the notebook.
- `nbs/inductance/00_theory.ipynb` — inductance theory page: flux linkage, self and mutual
  inductance, the flux paths that make up a winding's inductance (magnetising, harmonic, slot,
  tooth-tip and end-winding leakage), synchronous, zero-sequence and dq inductances, what each
  standstill measurement reads, and a map from each part to the function that computes it.
  The air-gap notebook's theory is now a labelled step-by-step derivation (winding function,
  flux per tooth, flux linkage, harmonic split, Carter). Figures from
  `nbs/inductance/images/make_theory_figs.py`.
- `emachines.inductance.airgap` — `winding_function` (turns around each tooth, zero mean) and
  its exact Fourier coefficients; `airgap_inductance(pattern, stator, part)` gives the m × m
  air-gap inductance matrix, its magnetising part (ν = p) or the air-gap harmonic leakage,
  with a Carter-corrected gap or a given `g_eff`; `phase_imbalance(L)` reports self and mutual
  spread and positive-to-other-sequence coupling. Validated against the closed-form L_m for
  distributed, fractional-slot and tooth-coil windings and the tabulated σ_δ for q = 1 … 5.
- `emachines.winding.mmf`: MMF harmonic spectrum (pure function, no UI dependency)
- `emachines.magnetics.pm_materials`: permanent magnet material database
- `emachines.motors.dc_motor`: DC motor analytical model

## [0.3.0] — 2026-05-09
### Added
- `emachines.winding.sos` — complete star-of-slots (slot-voltage-phasor) module:
  - `build_star_of_slots(Q, P)` — EMF phasor angles for all slots
  - `build_coil_matrix(Q, P, m, layers, w)` — slot-conductor occupancy matrix;
    includes adjacent go/return fix for degenerate single-layer FSCW (q = 1/2)
  - `assign_phases(Q, P, m, layers, w)` — per-phase signed slot lists (1-indexed)
  - `winding_factor_sos(nu, Q, P, m, layers, w)` — phasor-sum kw for any harmonic ν,
    any winding type (integer-slot, fractional-slot, FSCW)
  - `get_basic_params(Q, P, m)` — q, t, lcm, coil_pitch_full, winding_type classification
  - `check_symmetry(Q, P, m)` — balanced phase check
  - `get_valid_coil_spans(Q, P)` — list of valid spans 1 … Q//(P//2)
  - `is_valid_combination(Q, P, m)` — quick validity check
- `emachines.winding.__init__` — all sos symbols now exported at package level
- 42 new tests in `tests/test_sos.py`

### Changed
- `winding.factors.winding_factor()` — now dispatches to `winding_factor_sos` for
  FSCW (q < 1), using the double-layer convention that matches emetor.com reference values.
  Previously raised `ValueError` for FSCW.
- `winding.factors.distribution_factor()` — `ValueError` for FSCW retained but
  error message updated to point to `winding_factor()` for automatic dispatch.

### Validated
- 12s/10p: kw1 = 0.933 ✓ (emetor)
- 12s/8p:  kw1 = 0.866 ✓ (emetor)
- 9s/8p:   kw1 = 0.945 ✓ (emetor)
- 12s/14p: kw1 = 0.933 ✓ (emetor)
- 24s/4p, 5/6 chording: kw1 = 0.933 ✓ (emetor)
- 92 passing tests, 0 xfailed

## [0.2.0] — 2026-05-08
### Added
- `emachines.magnetics.electrical_steel`:
  - `SteelGrade` dataclass — name, manufacturer, bh_data, loss_data; `.frequencies`,
    `.bh_points`, `.loss_at(freq, B)` methods
  - `SteelDatabase` — loads Voestalpine Excel + ThyssenKrupp/SURA pickle caches
    from a runtime data directory; `.load(grade)` with LRU cache; `.grades`,
    `.manufacturers` properties
  - `SAMPLE_BH`, `SAMPLE_LOSS` — built-in M-19 / M-36 reference data (no files needed)
- `emachines.magnetics.iron_loss` fitting functions:
  - `fit_bertotti(f_arr, B_arr, loss_arr)` — recovers k_h, k_e, k_a; returns r2, rmse
  - `fit_steinmetz(f_arr, B_arr, loss_arr)`
  - `fit_modified_steinmetz(f_arr, B_arr, loss_arr)`
  - `fit_loss_model(f_arr, B_arr, loss_arr, model)` — dispatcher ("Bertotti" | "Steinmetz" | "Modified Steinmetz")
- `pandas>=1.5` added as explicit runtime dependency

### Changed
- `emdesigner/pages/electrical_steel.py` refactored to consume `emachines` —
  ~450 lines of inline math and material loading removed from the web app

## [0.1.0] — 2026-05-07
### Added
- `emachines.winding.factors`:
  - `pitch_factor(nu, coil_span, pole_pitch)` — kp for harmonic ν
  - `distribution_factor(nu, Q, p, m)` — kd for integer-slot windings (q ≥ 1)
  - `winding_factor(nu, Q, p, coil_span, m)` — combined kw
- `emachines.magnetics.bh_models`: Fröhlich analytical BH model and curve fitting
- `emachines.magnetics.iron_loss`:
  - `steinmetz(f, B_peak, k, alpha, beta)`
  - `modified_steinmetz(f, B_peak, k, alpha, beta)` — iGSE form
  - `bertotti(f, B_peak, k_h, k_e, k_a, alpha, beta)` — three-term separation
- `emachines.motors.pmsm`:
  - `PMSMParams` dataclass (p, Ld, Lq, psi_m, Rs, J)
  - `back_emf(omega_e, psi_m)`
  - `torque(params, id, iq)` — excitation + reluctance torque
  - `dq_currents(params, omega_e, Vd, Vq)` — steady-state solver
- `pyproject.toml` — hatchling build, PyPI metadata, Python ≥ 3.9
- MIT License

### Fixed
- Corrected GitHub username in project URLs (`vnaveendeepak` → `NaveenDeepak`)
- Lowered minimum Python from 3.10 to 3.9 to match emdesigner Docker environment
