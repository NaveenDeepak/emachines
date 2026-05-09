# Changelog

All notable changes to `emachines` will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]
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
