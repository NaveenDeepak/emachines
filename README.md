# emachines

**Analytical electromechanical machine design library.**

`emachines` is the core physics and mathematics engine behind [emdesignlabs.com](https://emdesignlabs.com). It provides well-documented, tested, and citable implementations of the analytical models used in electric motor design.

## Scope

- **Winding analysis** — winding factors (kp, kd, kw), MMF harmonic spectra, slot/pole geometry
- **Magnetics** — BH curve models (Fröhlich), iron loss (Steinmetz, Modified Steinmetz, Bertotti), electrical steel database
- **Motor models** — PMSM dq-frame, DC motor, surface-PM analytical design

Every function documents the equation it implements and its bibliographic source.

## Installation

```bash
pip install emachines
```

For development (editable install alongside emdesignlabs):

```bash
pip install -e path/to/emachines
```

## Quick Start

```python
from emachines.winding.factors import winding_factor
from emachines.magnetics.iron_loss import bertotti, fit_loss_model
from emachines.magnetics.electrical_steel import SteelDatabase, SAMPLE_LOSS
from emachines.motors.pmsm import PMSMParams, torque

# Winding factor for 12s/10p, fundamental harmonic
kw1 = winding_factor(nu=1, Q=12, p=5, coil_span=1)
print(f"kw1 = {kw1:.4f}")  # → 0.9330

# Bertotti iron loss at 400 Hz, 1.5 T
loss = bertotti(f=400, B_peak=1.5, k_h=0.02, k_e=1e-4, k_a=1e-3)
print(f"Total loss = {loss['total']:.2f} W/kg")

# Fit Bertotti coefficients from measured data
import numpy as np
f_arr = np.array([50, 100, 200, 400])
B_arr = np.array([1.0, 1.0, 1.0, 1.0])
loss_arr = np.array([1.2, 2.8, 6.5, 15.1])
result = fit_loss_model(f_arr, B_arr, loss_arr, model="Bertotti")
print(f"k_h={result['k_h']:.4f}, k_e={result['k_e']:.2e}, R²={result['r2']:.4f}")

# Load electrical steel database (data_dir points to your datasheet folder)
db = SteelDatabase("path/to/datasheets")
grade = db.load("M270-50A")
print(grade.loss_at(freq=200, B=1.5))

# Use built-in reference data (no files needed)
print(SAMPLE_LOSS["M-19"])

# PMSM torque from dq currents
motor = PMSMParams(p=3, Ld=5e-3, Lq=8e-3, psi_m=0.15)
Te = torque(motor, id=-3.0, iq=10.0)
print(f"Torque = {Te:.2f} N·m")
```

## Modules

### `emachines.winding`
| Module | Contents |
|---|---|
| `winding.factors` | `pitch_factor`, `distribution_factor`, `winding_factor` — integer-slot windings |

> FSCW (q < 1) winding factors via star-of-slots phasor method — in progress

### `emachines.magnetics`
| Module | Contents |
|---|---|
| `magnetics.bh_models` | Fröhlich analytical BH model and curve fitting |
| `magnetics.iron_loss` | `steinmetz`, `modified_steinmetz`, `bertotti` forward models; `fit_steinmetz`, `fit_modified_steinmetz`, `fit_bertotti`, `fit_loss_model` fitting |
| `magnetics.electrical_steel` | `SteelGrade` dataclass, `SteelDatabase` loader (Voestalpine Excel + ThyssenKrupp/SURA pickles), `SAMPLE_BH` and `SAMPLE_LOSS` reference data |

### `emachines.motors`
| Module | Contents |
|---|---|
| `motors.pmsm` | `PMSMParams`, `back_emf`, `torque`, `dq_currents` |

## Design Philosophy

- **Equations first** — every function documents the formula it implements with LaTeX notation
- **Cited** — every formula traces back to a specific reference (textbook, paper, standard)
- **Tested** — validated against published datasets and reference tools (emetor, SWAT-EM)
- **Dependency-light** — only numpy, scipy, and pandas required

## Changelog

### [0.2.0] — 2026-05-09
- `magnetics.electrical_steel`: `SteelGrade`, `SteelDatabase`, `SAMPLE_BH`, `SAMPLE_LOSS`
- `magnetics.iron_loss`: `fit_bertotti`, `fit_steinmetz`, `fit_modified_steinmetz`, `fit_loss_model`
- `pandas>=1.5` added as runtime dependency
- 36 passing tests, 4 xfailed (FSCW — pending)

### [0.1.0] — 2026-05-07
- `winding.factors`: `pitch_factor`, `distribution_factor`, `winding_factor`
- `magnetics.bh_models`: Fröhlich BH model
- `magnetics.iron_loss`: `steinmetz`, `modified_steinmetz`, `bertotti`
- `motors.pmsm`: `PMSMParams`, `back_emf`, `torque`, `dq_currents`
- 18 passing tests, 4 xfailed

## Status

`0.2.x` — Alpha. API may change between minor versions.

## License

MIT
