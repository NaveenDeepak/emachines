# emachines

**Analytical electromechanical machine design library.**

`emachines` is an open-source Python library of well-documented, tested, and citable implementations of the analytical models used in electric motor design. It is the physics engine behind [emdesignlabs.com](https://emdesignlabs.com).

[![CI](https://github.com/NaveenDeepak/emachines/actions/workflows/ci.yml/badge.svg)](https://github.com/NaveenDeepak/emachines/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/emachines.svg)](https://pypi.org/project/emachines/)
[![Python](https://img.shields.io/pypi/pyversions/emachines)](https://pypi.org/project/emachines/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What It Does

| Module | Capability |
|--------|-----------|
| `winding` | Winding factors (kp, kd, kw), star-of-slots phasor method, slot/pole geometry, coil matrices |
| `magnetics` | BH curve models, iron loss (Steinmetz, Bertotti), electrical steel database, PM materials |
| `motors` | PMSM dq-frame model, DC motor analytical model |
| `mec` | Magnetic equivalent circuit (MEC) Newton-Raphson solver with nonlinear materials |

Every function documents the equation it implements and its bibliographic source.

---

## Installation

```bash
pip install emachines
```

Requires Python ≥ 3.10.

---

## Quick Start

```python
from emachines.winding.factors import winding_factor
from emachines.winding.sos import winding_factor_sos, get_basic_params
from emachines.magnetics.iron_loss import bertotti, fit_loss_model
from emachines.motors.pmsm import PMSMParams, torque
from emachines.mec import MEC, LinearPermeabilityModel

# Winding factor — integer-slot (24s/4p, 5/6 chording)
kw = winding_factor(nu=1, Q=24, p=2, coil_span=5)
print(f"kw1 = {kw:.4f}")   # → 0.9330

# Winding factor — FSCW (12s/10p tooth-coil, auto-dispatch to star-of-slots)
kw = winding_factor(nu=1, Q=12, p=5, coil_span=1)
print(f"kw1 = {kw:.4f}")   # → 0.9330

# Iron loss — Bertotti forward model
loss = bertotti(f=400, B_peak=1.5, k_h=0.02, k_e=1e-4, k_a=1e-3)
print(f"Total loss = {loss['total']:.2f} W/kg")

# PMSM torque
motor = PMSMParams(p=3, Ld=5e-3, Lq=8e-3, psi_m=0.15, Rs=0.1)
Te = torque(motor, id=-3.0, iq=10.0)
print(f"Torque = {Te:.2f} N·m")

# Magnetic equivalent circuit
import numpy as np
mec = MEC()
mec.add_mesh_branch(branch=1, mesh=1, mmf=1000.0)
mec.add_nonlinear_branch(
    branch=2, length=0.1, area=1e-4,
    model=LinearPermeabilityModel(mu_r=1000),
    meshes=[1], orientations=[1]
)
mec.add_linear_branch(
    branch=3, permeance=4e-7 * np.pi * 1e-4 / 0.001,
    meshes=[1], orientations=[1]
)
sol = mec.solve()
print(f"Flux = {sol.flux(2):.6f} Wb  |  Converged: {sol.converged}")
```

---

## Design Philosophy

- **Equations first** — every function leads with the formula it implements, with LaTeX notation in the docstring
- **Cited** — every formula references a specific textbook, paper, or standard
- **Notebook-driven** — source lives in Jupyter notebooks (`nbs/`); Python modules are auto-generated via [nbdev](https://nbdev.fast.ai/)
- **Tested** — validated against published datasets and reference tools (emetor.com, SWAT-EM)
- **Dependency-light** — only numpy, scipy, pandas, and matplotlib required

---

## Contributing

Contributions are welcome. emachines is built with **nbdev** — you write Jupyter notebooks, and the Python library is generated automatically. This keeps theory, code, examples, and tests together in one place.

**To contribute a new module:**

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/emachines.git
cd emachines

# 2. Start the development environment (Docker recommended)
docker compose up -d
docker compose exec emachines-dev bash

# 3. Copy the template and start writing
cp nbs/00_template.ipynb nbs/XX_your_module.ipynb
jupyter lab   # open http://localhost:8888
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full workflow, notebook standards, and PR checklist. See [LOCAL_SETUP.md](./LOCAL_SETUP.md) for environment setup options (Docker recommended, direct install also supported).

### What We're Looking For

- New motor models (induction motor, SRM, axial flux)
- Thermal models (simplified lumped parameter)
- Winding MMF harmonic spectrum
- Demagnetisation analysis for PM machines
- Loss models for power electronics (switching, conduction)
- Additional steel grade data

Open an [issue](https://github.com/NaveenDeepak/emachines/issues) to discuss scope before writing code.

---

## Status

`0.6.0` — Alpha. API may change between minor versions until 1.0.

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the full history.

---

## License

MIT
