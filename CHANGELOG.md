# Changelog

All notable changes to `emachines` will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]
### Added
- `emachines.gears.helical` — single-stage external helical gear pair, from requirements to a
  manufacturing package (mm, N, MPa). `geometry`: `HelicalGear` (normal/transverse module and
  pressure angle, base helix, lead, axial pitch, virtual tooth count, transverse spur equivalent with
  exact root form diameter), pair centre distance and shift sum, helix angle for a centre distance,
  `helical_mesh_check` (ε_α, ε_β, ε_γ, active profile, interference, clearance), span W_k in the normal
  plane and dimension over balls. `layout`: tooth counts, helix angle by design priority
  ('quiet', 'balanced', 'low_thrust'), Niemann / ISO TR 4467 shift split, `HelicalPair` with tidy centre
  distance, tip shortening, speeds and tooth forces. `rating`: ISO 6336 contact and bending with Z_H(β_b),
  Z_ε(ε_β), Z_β, Y_β, Y_ε(ε_αn), helical K_v and K_Hα, form factors on the virtual gear, static peak check.
  `components`: hub joints with axial force (key + retaining ring, press fit, adhesive, pinion cut on the
  shaft), bearing reactions with the axial moment, deep groove ball bearing selection (C_req, L10h),
  shaft minimum diameter and deflection, housing axis tolerances (ISO/TR 10064-3). `manufacturing`:
  ISO 1328-1 tolerances, backlash → normal thickness allowances, ISO 1340 data tables with hand and lead,
  transverse DXF outline and CAD twist angle. `design`: `design_helical_pair(HelicalRequirements)` and
  `write_package` (report, data tables, parts list, component dimensions, layout SVG, DXF).
### Fixed
- Slot-leakage notebook: the "layers rotated pole by pole" variant of the EP 2 237 392 B1 winding
  overfilled some slot positions and cannot be built; the example now shows why and checks the fill.

### Added
- `emachines.inductance.endwinding` — `EndTurn` (straight extension, axial tier offset per slot
  position, arc factor, empirical end-winding factor λ_w), `coil_end_length`, `mean_turn_length`,
  `phase_resistance` (DC, per phase, from copper area or fill factor, at temperature) and
  `end_winding_inductance` (empirical, 2 μ0 N_s² l_end λ_w / p). Worked example: resistance spread
  of the EP 2 237 392 B1 winding for three end-turn stackings.
- `emachines.inductance.stator` — `StatorInductances` (magnetising, harmonic, slot, tooth-tip and
  end-winding matrices, resistance; total, leakage, positive and zero sequence, imbalance, summary),
  `stator_inductances` and `compare_windings` (side-by-side table with an even-fill check).
- `emachines.gears` — single-stage planetary gear train design, from requirements to a
  manufacturing package (ring fixed, sun in, carrier out; spur gears; mm, N, MPa).
  `involute`: `GearGeometry` (external/internal, profile shift, tip reduction, root form
  diameter), span and over-ball measurements, operating pressure angle, centre distance,
  contact ratio, interference and tip-clearance checks. `layout`: tooth-count search with
  coaxial, assembly and neighbour conditions (also ±1-tooth rings via profile shift),
  `PlanetarySet` with automatic shifts and ring tip reduction, module window from envelope
  diameter and sun shaft/key. `rating`: ISO 6336 pitting and tooth-root safety for both meshes
  (Y_F/Y_S by the 30° tangent, rim factor, K_v, K_Hβ, K_γ, life factors, planet Y_M).
  `components`: DIN 6885 key, planet needle bearing (C_req, ISO 281 estimate, L10h), pin
  bending/deflection, double-plate carrier with posts or single-plate carrier with cantilevered pins,
  ring fixing, axial stack; sun–shaft joints: key, DIN 5480 spline (sliding or tight), press/shrink
  fit (Lamé, fit selection), retaining adhesive, or sun cut on the shaft.
  `manufacturing`: ISO 286 fit limits, ISO 1328-1:2013 tolerances, backlash → tooth thickness
  allowances, ISO 1340 / DIN 3966-1 gear data tables, DXF tooth outlines. `design`:
  `design_planetary(PlanetaryRequirements)` search (carrier type, minimum module) and `write_package` (report, data tables,
  parts list, component dimensions, layout SVG, DXF).
- `emachines.inductance.slot` — slot and tooth-tip leakage by conductor position.
  `slot_permeance(stator, layout, n, part)` gives the specific permeance matrix between slot
  positions, Λ_rs = ∫ A_r A_s / b dy over the conductor body (any taper), plus the opening and
  tooth-tip transition and the tooth-tip leakage; `slot_leakage_inductance(pattern, stator, part)`
  gives the m × m phase matrix, to add to `airgap_inductance`. Validated against the exact
  three-layer matrix (self 1 : 4 : 7) and Pyrhönen's short-pitch factors k1, k2. Worked example:
  the one-phase-per-layer winding of EP 2 237 392 B1, its imbalance and the effect of slot taper.
  Labelled slot-field and taper figures.
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
