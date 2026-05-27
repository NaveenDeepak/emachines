# emachines Project Guidelines

## Quick Context

**Project Goal:** A collaborative, Docker-based electric motor simulation library using nbdev for notebook-driven development.

**Current State (as of May 27, 2026):**
- Motors module ✅ COMPLETE (nbs/02_dc_motors.ipynb + nbs/02_pmsm.ipynb + emachines/motors/motors.py)
- Winding module ✅ COMPLETE (nbs/01_winding.ipynb + emachines/winding/factors.py + sos.py)
- Magnetics module ✅ COMPLETE (4 focused notebooks)
- Mec module ✅ COMPLETE + VERIFIED (3 notebooks, NR solver fixed)
- CI/CD ✅ FULLY NBDEV-NATIVE — export + nbtest + mypy, all checks green on main

**Key User Intent:** Establish a collaborative development environment with Docker consistency and nbdev notebook-driven development. The user plans to invite a collaborator.

---

## Development Workflow

### 1. **nbdev Pattern (Established & Required)**

All modules follow this exact structure in Jupyter notebooks:

```
1. Theory/Math Section
   - Equations, physics foundations
   - Define dataclasses for parameters
   
2. Implementation Code
   - Functions marked with #| export
   - Type hints on all parameters/returns
   - Docstrings with Args/Returns sections
   
3. Examples/Usage
   - Concrete examples showing how to use functions
   - Numerical validation of theory
   
4. Tests
   - Assertions validating correctness
   - Edge case coverage
```

**CRITICAL:** Theory is placed **immediately adjacent** to implementation code, NOT upfront in a separate "Theory" section. This creates tight coupling between explanation and code.

**Example structure:**
```
### Winding Factor
[Theory: define α_p, α_d equations]
[Implementation: def calculate_pitch_factor(...)]
[Examples: compute for specific motors]
[Tests: assert calculations match expectations]
```

### 2. **File Organization**

```
emachines/
├── motors/
│   ├── __init__.py              (imports from motors.py)
│   └── motors.py                (auto-generated from notebook)
├── winding/
│   ├── __init__.py              (imports from winding.py)
│   └── winding.py               (auto-generated from notebook)
├── magnetics/                   (PENDING CONVERSION)
│   ├── __init__.py
│   ├── bh_models.py
│   ├── electrical_steel.py
│   ├── iron_loss.py
│   └── pm_materials.py
├── mec/                         (PENDING CONVERSION)
│   ├── __init__.py
│   ├── material.py
│   ├── solver.py
│   └── result.py

nbs/
├── 01_winding.ipynb             (32K, complete)
├── 02_motors.ipynb              (24K, complete)
├── 03_magnetics.ipynb           (PENDING)
├── 04_mec.ipynb                 (PENDING)
```

### 3. **Creating/Converting a Module (Step-by-Step)**

#### Option A: Converting existing Python modules to nbdev

1. **Examine the existing .py files**
   - Read through each file to understand structure
   - Identify dataclasses, functions, tests
   - Note mathematical relationships

2. **Create the notebook** (e.g., `nbs/03_magnetics.ipynb`)
   - Use Jupyter (local or Docker)
   - Create sections for each .py file's content
   - Structure as: Theory → Implementation → Examples → Tests
   - Mark all functions/classes with `#| export` directive

3. **Use nbdev to generate the Python module**
   ```bash
   # Inside Docker container or local nbdev environment:
   nbdev_build_lib
   ```
   This generates `emachines/magnetics/magnetics.py` from the notebook.

4. **Update __init__.py**
   - Change imports to reference new combined module
   - Update `__all__` list with all exports
   
5. **Verify in Docker**
   ```bash
   docker-compose up -d emachines-dev
   docker exec emachines-dev python -c "from emachines.magnetics import *; print('Success')"
   ```

#### Option B: Creating from scratch (new module)

- Create notebook in `nbs/` with same structure
- Build, generate .py, update __init__.py
- Same verification steps

### 4. **Docker Workflow**

**Why:** Ensures Python 3.10 consistency across macOS, Windows, Linux.

**Quick commands:**
```bash
# Start development environment
docker-compose up -d emachines-dev

# Enter container to run nbdev commands
docker exec -it emachines-dev bash

# Inside container, rebuild Python module from notebook
nbdev_build_lib

# Run tests
python -m pytest nbs/02_motors.ipynb

# View Jupyter
# Open http://localhost:8888 in browser
# Token shown in: docker logs emachines-dev
```

**Files:**
- `Dockerfile`: Python 3.10, nbdev, JupyterLab, all dependencies
- `docker-compose.yml`: emachines-dev service with workspace mount
- `.dockerignore`: Excludes git, caches, IDE files

---

## Completed Modules (Reference)

### Motors (nbs/02_motors.ipynb)
**Content:** DC motors + PMSM (Permanent Magnet Synchronous Motors)

**DC Motor Functions:**
- `calculate_carter_coefficient()` — Slot effect correction
- `calculate_magnetic_circuit()` — Reluctance network analysis
- `calculate_armature_resistance()` — Wire resistance
- `calculate_motor_constants()` — Torque constant K
- `calculate_rotor_inertia()` — Mechanical inertia
- `calculate_lumped_parameters()` — Composite DC model
- `calculate_steady_state_performance()` — Torque-speed
- `calculate_losses_and_efficiency()` — Copper, iron, mechanical
- `plot_efficiency_map()` — 2D contour visualization

**PMSM Functions:**
- `back_emf()` — Back-EMF voltage
- `torque()` — Electromagnetic torque
- `dq_currents()` — Steady-state dq-frame currents
- `SPM.motor_profile()` — Constant-torque & flux-weakening regions

**Key Classes:**
- `GeometricParams` — Motor geometry
- `MaterialProperties` — Copper, steel, magnet properties
- `OperatingConditions` — Terminal voltage, brush effects
- `LumpedParams` — Aggregated DC motor parameters
- `PMSMParams` — PMSM state container

### Winding (nbs/01_winding.ipynb)
**Content:** Winding factors for AC machines

**Functions:**
- `calculate_pitch_factor()` — Accounts for coil pitch ≠ pole pitch
- `calculate_distribution_factor()` — Multiple slots per pole
- `calculate_winding_factor()` — Combined effect
- `plot_star_of_slots()` — Phase diagram visualization

**Key Classes:**
- `WindingConfig` — Slots, poles, layers configuration

---

## Pending Modules (What to Convert Next)

### Magnetics (4 focused notebooks) — ✅ COMPLETE
**Notebooks created:**
- `nbs/03_bh_models.ipynb` — B-H curve models (Fröhlich, linear approximation)
- `nbs/03_iron_loss.ipynb` — Core loss models (Steinmetz, Bertotti)
- `nbs/03_electrical_steel.ipynb` — Steel properties database
- `nbs/03_pm_materials.ipynb` — Permanent magnet (NdFeB) materials

**Auto-generated module:**
- `emachines/magnetics/magnetics.py` — Combined Python module (18 exports)

**What was accomplished:**
- ✅ Split monolithic notebook into 4 focused notebooks (user request)
- ✅ Fixed notebook formatting and rendering issues
- ✅ Verified all functionality with comprehensive tests
- ✅ All 18 exports import and execute correctly
- ✅ Material databases (SAMPLE_BH, SAMPLE_LOSS, MAGNET_LIBRARY) working
- ✅ All classes (SteelGrade, MagnetGrade, MagnetData) instantiate properly

### Mec (nbs/04_mec.ipynb) — SUBSEQUENT
**Source files to convert:**
- `emachines/mec/material.py` — Material definitions
- `emachines/mec/solver.py` — FEM solver interface
- `emachines/mec/result.py` — Result post-processing

---

## Git/GitHub Workflow

### Branch Protection Rules
- Main branch requires PR review (CODEOWNERS: NaveenDeepak)
- No direct pushes to main
- All PRs must:
  - Run Docker setup & verify (SETUP.md)
  - Run nbdev_build_lib (notebooks properly formatted)
  - Include auto-generated .py files in commit
  - Pass pre-commit hooks

### Commit Pattern
```bash
git checkout -b feature/module-name
# ... make changes ...
git add nbs/*.ipynb emachines/*/*.py
git commit -m "Convert [module_name] to nbdev format

- Add theory sections with mathematical foundations
- Implement functions with #| export directives
- Include examples and comprehensive tests
- Auto-generated: emachines/[module_name]/[module_name].py"
git push origin feature/module-name
# Create PR, request review from CODEOWNERS
```

### Files to Include in Commit
- `nbs/XX_module_name.ipynb` — The notebook (source of truth)
- `emachines/module_name/module_name.py` — Auto-generated (DO NOT edit directly)
- `emachines/module_name/__init__.py` — Updated imports
- Any new test files or documentation

---

## Technical Foundations (Reference)

### Electric Motor Physics
- **Lumped-parameter models:** Reluctance networks, magnetic circuits
- **Carter's coefficient:** γ = (w_so/g)²/(5+w_so/g), corrects slot effects
- **PMSM dq-frame:** Direct & quadrature axis decomposition
- **SPM profile:** Constant-torque region + flux-weakening region

### nbdev Directives
```python
#| export
def function_name(...):
    """Export this to generated .py file"""
    pass

#| hide
def helper():
    """Keep in notebook, don't export"""
    pass

#| hide_line
sensitive_data = "secret"  # This line not exported
```

### Naming Conventions
- **Dataclasses:** PascalCase (e.g., `GeometricParams`)
- **Functions:** snake_case (e.g., `calculate_motor_constants`)
- **Constants:** UPPER_CASE (e.g., `PI_OVER_2`)
- **Private helpers:** `_snake_case` (e.g., `_reluctance_air_gap`)

---

## Pre-Session Checklist

When starting a new session:

1. **Review this document** — Get context on project state & workflow
2. **Identify the next task**
   - Check "Pending Modules" section
   - Magnetics typically comes after Motors
   - Mec comes after Magnetics
3. **Set up Docker** (if needed)
   ```bash
   docker-compose up -d emachines-dev
   ```
4. **Verify current state**
   ```bash
   python -c "from emachines.motors import *; from emachines.winding import *"
   ```
5. **Proceed with nbdev conversion** following the pattern from completed modules

---

## Key Resources

**Documentation in repo:**
- `SETUP.md` — Docker setup & environment guide
- `CONTRIBUTING.md` — Development standards & workflow
- `.github/pull_request_template.md` — PR checklist
- `.github/BRANCH_PROTECTION_GUIDE.md` — GitHub configuration

**Backup:**
- `emachines.backup/` — Original code before nbdev conversion (May 23, 18:25)

**Notebook files (Source of Truth):**
- `nbs/01_winding.ipynb` — Reference for nbdev pattern
- `nbs/02_motors.ipynb` — Reference for complex module structure

---

## When Stuck

**Issue: "nbdev_build_lib: command not found"**
- Solution: Run inside Docker container: `docker exec -it emachines-dev bash`

**Issue: Auto-generated .py file is out of sync with notebook**
- Solution: In Docker: `nbdev_build_lib`
- Commit both the notebook AND the generated .py file

**Issue: Import errors after module conversion**
- Solution: Verify `__init__.py` has correct imports and `__all__` list
- Check: `python -c "from emachines.module_name import *"`

**Issue: Tests fail when running locally**
- Solution: Use Docker to ensure Python 3.10 consistency
- `docker exec emachines-dev python -m pytest nbs/XX_module.ipynb`

---

## Collaborator Onboarding

When inviting the friend/collaborator:
1. Share this GUIDELINES.md
2. Point them to SETUP.md for Docker setup
3. Reference CONTRIBUTING.md for development workflow
4. Have them create a test PR to verify environment setup

---

## Summary: Project State (May 27, 2026)

| Module | Status | Notebooks | Library files | Notes |
|--------|--------|-----------|---------------|-------|
| Winding | ✅ | `nbs/01_winding.ipynb` | `winding/factors.py`, `winding/sos.py` | Complete, tested |
| Motors | ✅ | `nbs/02_dc_motors.ipynb`, `nbs/02_pmsm.ipynb` | `motors/dc_motor.py`, `motors/pmsm.py` | DC + PMSM |
| Magnetics | ✅ | 4 focused notebooks | `magnetics/*.py` | BH, iron loss, electrical steel, PM |
| MEC | ✅ | `nbs/04_mec_solver.ipynb` + 2 support nbs | `mec/mec.py`, `mec/solver.py`, etc. | NR solver fixed |

**CI/CD (as of May 27, 2026):**
- Pipeline: `nbdev-export` check → `nbdev-test` + `mypy` (parallel)
- All checks green on `main` ✅
- Tests live in notebooks as `#| hide` assertion cells (140 assertions across 5 notebooks)
- No black/isort/flake8/pytest — fully nbdev-native

**Pending (next steps):**
- Add `#| default_exp` to all 10 main notebooks so `nbdev-export` generates library files
  (currently library files are hand-written; export check only guards `test_verify.py`)

