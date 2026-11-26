"""Generate the theory figures for the emachines.inductance notebooks.

Run from the repository root:  python nbs/inductance/images/make_theory_figs.py
Writes SVGs next to this script. The air-gap figures are computed with the library itself.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

from emachines.inductance.airgap import winding_function, winding_function_harmonics
from emachines.winding.pattern import WindingPattern

OUT = Path(__file__).parent
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "svg.fonttype": "path",
                     "axes.spines.top": False, "axes.spines.right": False})

IRON, IRON_EDGE, ROTOR = "#cfd4dc", "#4a5160", "#e3e6eb"
PH = {"A": "#d9534f", "B": "#f0ad4e", "C": "#5b8def"}
MAIN, SLOT, TIP, EW, HARM = "#1f5fbf", "#e07b00", "#2e9d48", "#8e44ad", "#7f7f7f"


def arrow(ax, p0, p1, color, lw=1.6, style="-|>", rad=0.0, ms=12, z=5):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=ms, color=color, lw=lw,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z))


def flux_loop(ax, pts, color, lw=1.8, arrow_at=(0.25, 0.75)):
    """Closed polyline with arrowheads part-way along given segments."""
    pts = np.asarray(pts + [pts[0]], float)
    ax.plot(pts[:, 0], pts[:, 1], color=color, lw=lw, zorder=4, solid_joinstyle="round")
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    for f in arrow_at:
        s = f * seg[-1]
        k = np.searchsorted(seg, s) - 1
        t = (s - seg[k]) / (seg[k + 1] - seg[k])
        p = pts[k] + t * (pts[k + 1] - pts[k])
        d = (pts[k + 1] - pts[k]) / np.hypot(*(pts[k + 1] - pts[k]))
        arrow(ax, p - 0.6 * d, p + 0.6 * d, color, lw=0, ms=14)


# ------------------------------------------------------------------ 1. flux paths
def fig_flux_paths():
    fig = plt.figure(figsize=(11, 5.6))
    ax = fig.add_axes([0.0, 0.0, 0.70, 1.0])
    bx = fig.add_axes([0.70, 0.08, 0.30, 0.84])
    tau, bs, b0 = 10.0, 5.0, 1.6
    y_b, h0, h1, hs, hy = 1.0, 0.7, 1.0, 9.0, 4.0
    y_body, y_sb = y_b + h0 + h1, y_b + h0 + h1 + hs
    y_top = y_sb + hy
    n = 6
    x_end = n * tau
    ax.add_patch(Rectangle((0, -5), x_end, 5, fc=ROTOR, ec=IRON_EDGE, lw=1.0))
    ax.add_patch(Rectangle((0, y_b), x_end, y_top - y_b, fc=IRON, ec=IRON_EDGE, lw=1.0))
    for i in range(n):
        xc = tau * (i + 0.5)
        ax.add_patch(Polygon([(xc - b0 / 2, y_b), (xc - b0 / 2, y_b + h0), (xc - bs / 2, y_body),
                              (xc - bs / 2, y_sb), (xc + bs / 2, y_sb), (xc + bs / 2, y_body),
                              (xc + b0 / 2, y_b + h0), (xc + b0 / 2, y_b)], fc="white", ec=IRON_EDGE, lw=1.0))
        phases = ["A", "A", "B", "B", "C", "C"]
        for k, (y0, y1) in enumerate([(y_body + 0.3, y_body + hs / 2 - 0.15), (y_body + hs / 2 + 0.15, y_sb - 0.3)]):
            ph = phases[(i + k) % 6]
            ax.add_patch(Rectangle((xc - bs / 2 + 0.3, y0), bs - 0.6, y1 - y0, fc=PH[ph], ec="none", alpha=0.35))
            ax.text(xc, (y0 + y1) / 2, ph, ha="center", va="center", fontsize=9, color="#333")
    ax.text(x_end + 0.5, y_b + 0.5 * (y_top - y_b), "stator", rotation=90, va="center", fontsize=9, color="#555")
    ax.text(x_end + 0.5, -2.5, "rotor", rotation=90, va="center", fontsize=9, color="#555")
    ax.annotate("air gap g", (2, 0.5), (-6.5, 0.5), va="center", fontsize=9,
                arrowprops=dict(arrowstyle="-", color="#555", lw=0.8))
    # main flux: down tooth 1, along the rotor, up tooth 4, back through the yoke
    xa, xb = tau * 1.0, tau * 3.0
    flux_loop(ax, [(xa, y_top - 1.8), (xa, -2.8), (xb, -2.8), (xb, y_top - 1.8)], MAIN, arrow_at=(0.12, 0.4, 0.62, 0.9))
    ax.text(1.0, -4.1, "main (air-gap) flux: crosses the gap, links the rotor",
            ha="left", fontsize=9.5, color=MAIN, weight="bold")
    # slot leakage: across slot 5 at two depths, closing through teeth and yoke
    xc = tau * 5.5
    for y, dx in [(y_body + 2.2, 3.4), (y_body + 6.0, 4.1)]:
        flux_loop(ax, [(xc - dx, y), (xc + dx, y), (xc + dx, y_top - 0.8 + (y - y_body) * 0.05),
                       (xc - dx, y_top - 0.8 + (y - y_body) * 0.05)], SLOT, lw=1.4, arrow_at=(0.12,))
    ax.text(xc, y_top + 0.7, "slot leakage", ha="center", fontsize=9.5, color=SLOT, weight="bold")
    # tooth-tip leakage across the opening of slot 2
    xc = tau * 4.5
    ax.plot([xc - b0 / 2 - 1.4, xc + b0 / 2 + 1.4], [y_b + 0.35, y_b + 0.35], color=TIP, lw=1.6, zorder=6)
    ax.plot([xc - b0 / 2 - 1.8, xc + b0 / 2 + 1.8], [y_b + 0.95, y_b + 0.95], color=TIP, lw=1.6, zorder=6)
    arrow(ax, (xc - 0.3, y_b + 0.35), (xc + 0.5, y_b + 0.35), TIP, lw=0, ms=12, z=7)
    arrow(ax, (xc - 0.3, y_b + 0.95), (xc + 0.5, y_b + 0.95), TIP, lw=0, ms=12, z=7)
    ax.annotate("tooth-tip leakage\n(across the slot opening)", (xc + 1.0, y_b + 0.6), (xc - 4.0, -3.6),
                fontsize=9.5, color=TIP, weight="bold", ha="left",
                arrowprops=dict(arrowstyle="-", color=TIP, lw=0.8))
    ax.text(0.3, y_top + 0.7, "(a) cross-section, unrolled (gap and openings exaggerated)", fontsize=10)
    ax.set_xlim(-7, x_end + 2); ax.set_ylim(-5.5, y_top + 2.0); ax.set_aspect("equal"); ax.axis("off")

    # (b) side view with end winding
    L, ov = 10.0, 2.6
    bx.add_patch(Rectangle((0, 0), L, 4, fc=IRON, ec=IRON_EDGE))
    bx.add_patch(Rectangle((0, -3.2), L, 2.6, fc=ROTOR, ec=IRON_EDGE))
    for x0, sgn in [(0, -1), (L, 1)]:
        t = np.linspace(-np.pi / 2, np.pi / 2, 60)
        xs = x0 + sgn * ov * np.cos(t)
        bx.plot(xs, 2.0 + 1.6 * np.sin(t), color=PH["A"], lw=4, alpha=0.6, solid_capstyle="round")
        for r in (0.7, 1.2):
            c = Circle((x0 + sgn * ov, 2.0), r, fc="none", ec=EW, lw=1.3)
            bx.add_patch(c)
        arrow(bx, (x0 + sgn * ov - 0.05, 2.0 + 1.2), (x0 + sgn * ov + 0.05 * sgn, 2.0 + 1.2), EW, lw=0, ms=12)
    bx.text(L / 2, 2.0, "stator stack", ha="center", va="center", fontsize=9, color="#444")
    bx.text(L / 2, -1.9, "rotor", ha="center", va="center", fontsize=9, color="#444")
    bx.annotate("", (0, 4.6), (L, 4.6), arrowprops=dict(arrowstyle="<->", color="#222", lw=0.9))
    bx.text(L / 2, 4.85, r"$l_{stk}$", ha="center", fontsize=10)
    bx.annotate("", (L, -3.8), (L + ov, -3.8), arrowprops=dict(arrowstyle="<->", color="#222", lw=0.9))
    bx.text(L + ov / 2, -4.6, r"$l_{ew}$", ha="center", fontsize=10)
    bx.text(L / 2, 6.3, "end-winding leakage\n(around the end turns, in air)", ha="center", fontsize=9.5,
            color=EW, weight="bold")
    bx.text(-ov - 0.5, 8.0, "(b) side view", fontsize=10)
    bx.set_xlim(-ov - 1.2, L + ov + 1.2); bx.set_ylim(-5.2, 8.6); bx.set_aspect("equal"); bx.axis("off")
    fig.savefig(OUT / "flux_paths.svg", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 2. components tree
def fig_components():
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, 110); ax.axis("off")

    def box(x, y, w, h, title, sub, color, where):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=color + "22", ec=color, lw=1.4))
        ax.text(x + w / 2, y + h - 2.2, title, ha="center", va="top", fontsize=10, weight="bold", color="#222")
        ax.text(x + w / 2, y + h / 2 + (0.3 if where else -1.0), sub, ha="center", va="center", fontsize=8.8, color="#333")
        if where:
            ax.text(x + w / 2, y + 0.9, where, ha="center", va="bottom", fontsize=8, style="italic", color=color)

    def link(p0, p1):
        ax.plot([p0[0], p0[0], p1[0], p1[0]], [p0[1], (p0[1] + p1[1]) / 2, (p0[1] + p1[1]) / 2, p1[1]],
                color="#666", lw=1.0)

    box(33, 42, 44, 9, "Phase self inductance  $L_{aa}$ (what you measure)",
        r"$\lambda_a = L_{aa}\, i_a$ with only phase a excited", "#333333", None)
    box(4, 22, 40, 15, "Air-gap part  $L_{ag}$",
        "flux that crosses the gap\n(depends on the winding function)", MAIN, "03_airgap · airgap_inductance")
    box(50, 22, 56, 15, r"Local leakage  (never reaches the rotor)",
        "flux that closes around the conductors\n(depends on slot shape and conductor position)", SLOT, None)
    link((55, 42), (24, 37)); link((55, 42), (78, 37))
    box(1, 1, 20, 16, "Magnetising $L_m$", "working harmonic\n" + r"$\nu = p$" + "\n(produces torque)",
        MAIN, "part='magnetising'")
    box(23, 1, 22, 16, r"Harmonic leakage $L_\delta$", "all other harmonics\n" + r"$\nu \neq p$" +
        "\n(differential leakage)", HARM, "part='harmonic'")
    box(50, 1, 17, 16, r"Slot  $L_{slot}$", "across the slot,\nby layer", SLOT, "next PR")
    box(69, 1, 17, 16, r"Tooth tip  $L_{tt}$", "across the\nslot opening", TIP, "next PR")
    box(88, 1, 18, 16, r"End winding  $L_{ew}$", "around the\nend turns", EW, "later PR")
    for x in (11, 34):
        link((24, 22), (x, 17))
    for x in (58.5, 77.5, 97):
        link((78, 22), (x, 17))
    ax.plot([23, 106.5], [-0.8, -0.8], color="#444", lw=0.9)
    ax.text(64.5, -2.6, r"total leakage  $L_\sigma = L_\delta + L_{slot} + L_{tt} + L_{ew}$  (+ skew, if skewed)",
            ha="center", va="top", fontsize=9.5)
    ax.set_ylim(-5, 52)
    fig.savefig(OUT / "inductance_components.svg", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 3. self and mutual
def fig_self_mutual():
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    R_o, R_b, R_r = 4.4, 3.0, 2.85
    ax.add_patch(Circle((0, 0), R_o, fc=IRON, ec=IRON_EDGE))
    ax.add_patch(Circle((0, 0), R_b, fc="white", ec=IRON_EDGE))
    ax.add_patch(Circle((0, 0), R_r, fc=ROTOR, ec=IRON_EDGE))
    # flux of phase A: vertical across the rotor, returning round the yoke
    for x in np.linspace(-1.9, 1.9, 5):
        h = np.sqrt(R_b ** 2 - x ** 2)
        ax.plot([x, x], [-h, h], color=MAIN, lw=1.2, zorder=3)
        arrow(ax, (x, -0.2), (x, 0.4), MAIN, lw=0, ms=11)
    for sgn in (-1, 1):
        t = np.linspace(np.pi / 2 + 0.25, 3 * np.pi / 2 - 0.25, 80) if sgn < 0 else \
            np.linspace(-np.pi / 2 + 0.25, np.pi / 2 - 0.25, 80)
        r = (R_b + R_o) / 2
        ax.plot(r * np.cos(t), r * np.sin(t), color=MAIN, lw=1.2)
        arrow(ax, (sgn * r, 0.3), (sgn * r, -0.3), MAIN, lw=0, ms=11)

    def coil(angle_deg, ph, label):
        a = np.radians(angle_deg)
        for k, mark in [(0, "⊗"), (np.pi, "⊙")]:
            p = (R_b + 0.25) * np.array([np.cos(a + k), np.sin(a + k)])
            ax.add_patch(Circle(p, 0.26, fc=PH[ph], ec="#333", lw=0.8, zorder=6))
            ax.text(*p, mark, ha="center", va="center", fontsize=9, zorder=7)
        ax_dir = np.array([np.cos(a + np.pi / 2), np.sin(a + np.pi / 2)])
        arrow(ax, (0, 0), tuple(2.4 * ax_dir), PH[ph], lw=2.4, ms=16, z=8)
        ax.text(*(1.4 * ax_dir + 0.75 * np.array([ax_dir[1], -ax_dir[0]])), label, ha="center", va="center", fontsize=10, color=PH[ph], weight="bold", zorder=8)

    coil(0, "A", "axis A")
    coil(120, "B", "axis B")
    ax.text(0, -R_o - 0.6, "flux of a current in phase A (blue).\n"
            r"It links all of coil A $\Rightarrow L_{aa}$;  coil B sees it at $120^\circ$"
            "\n" r"$\Rightarrow L_{ba} \approx L_m \cos 120^\circ = -L_m/2$ (air-gap part)",
            ha="center", va="top", fontsize=9.5)
    ax.set_xlim(-5, 5); ax.set_ylim(-6.9, 5); ax.set_aspect("equal"); ax.axis("off")
    fig.savefig(OUT / "self_mutual.svg", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 4. winding function, step by step
def fig_winding_function():
    pat = WindingPattern.distributed(12, 2, layers=1, turns=1)
    N = pat.effective_turns()[0].sum(axis=1)          # turns of phase A in each slot (signed)
    W = winding_function(pat)[0]
    Q = pat.Q
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10.5, 5.8), sharex=True,
                                 gridspec_kw=dict(height_ratios=[1, 2.1], hspace=0.08))
    # top: slots with phase-A conductors
    a1.add_patch(Rectangle((-0.5, 0), Q + 0.5, 1.0, fc=IRON, ec=IRON_EDGE))
    for i in range(Q):
        a1.add_patch(Rectangle((i - 0.22, 0), 0.44, 0.8, fc="white", ec=IRON_EDGE, lw=0.8))
        if N[i] != 0:
            a1.add_patch(Circle((i, 0.4), 0.17, fc=PH["A"], ec="#333", lw=0.6, zorder=5))
            a1.text(i, 0.4, "⊙" if N[i] > 0 else "⊗", ha="center", va="center", fontsize=8, zorder=6)
            a1.text(i, -0.33, f"$N_{{{i}}}$={N[i]:+.0f}", ha="center", va="center", fontsize=8.5, color=PH["A"])
        else:
            a1.text(i, -0.33, "0", ha="center", va="center", fontsize=8.5, color="#999")
        a1.text(i + 0.5, 0.9, f"{i}", ha="center", va="center", fontsize=7.5, color="#444")
    a1.text(-0.45, 1.2, "tooth number (between slot i and i+1) ↓", fontsize=8, color="#444")
    a1.text(Q + 0.1, 0.4, "phase-A\nconductors\nper slot", fontsize=8, va="center", color=PH["A"])
    a1.set_ylim(-0.7, 1.5); a1.axis("off")
    # bottom: winding function
    x = np.arange(Q + 1)
    a2.step(x, np.append(W, W[0]), where="post", color=MAIN, lw=2, label=r"winding function $W_{a,i}$ (turns per A)")
    a2.axhline(0, color="#999", lw=0.8)
    a2.bar(np.arange(Q), W, width=1.0, align="edge", color=MAIN, alpha=0.12)
    th = np.linspace(0, 2 * np.pi, 721)
    a = winding_function_harmonics(pat, pat.p)[0]
    a2.plot(th * Q / (2 * np.pi), 2 * np.real(a * np.exp(1j * pat.p * th)), "--", color="#333", lw=1,
            label=r"fundamental ($\nu = p$): gives $L_m$")
    # annotate one step
    i = int(np.flatnonzero(N < 0)[0])
    a2.annotate("", (i, W[i]), (i, W[i - 1]), arrowprops=dict(arrowstyle="->", color=PH["A"], lw=1.4))
    a2.text(i + 0.12, (W[i] + W[i - 1]) / 2, rf"step at slot {i}: $W_{{{i}}} = W_{{{i-1}}} - N_{{{i}}}$",
            fontsize=9, color=PH["A"], va="center")
    j = int(np.argmax(W))
    a2.text(j + 0.5, W[j] + 0.12, f"$W_{{{j}}}$ = {W[j]:+.0f}", ha="center", fontsize=9, color=MAIN)
    a2.text(0.1, -0.12, "zero mean: equal areas above and below\n(no net flux leaves the rotor)", fontsize=8.5,
            color="#555", va="top")
    a2.set_xlim(-0.5, Q + 0.4); a2.set_ylim(W.min() - 0.9, W.max() + 0.9)
    a2.set_ylabel("turns enclosed per ampere")
    a2.set_xlabel(r"slot position around the gap  ($\theta_i = 2\pi i / Q$)")
    a2.legend(loc="lower right", fontsize=8.5, frameon=False)
    a2.text(Q + 0.35, W.max() + 0.5, r"MMF over tooth i = $W_{a,i}\, i_a$" "\n"
            r"$B_i = \mu_0 W_{a,i} i_a / g_e$", fontsize=8.5, ha="right", va="top", color="#333")
    fig.savefig(OUT / "winding_function_steps.svg", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 5. self and mutual as integrals of products
def fig_product():
    pat = WindingPattern.distributed(12, 2, layers=1, turns=1)
    W = winding_function(pat)
    Q = pat.Q
    x = np.arange(Q + 1)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.4), sharey=True)
    for ax, (j, title) in zip(axs, [(0, r"self: $W_a \cdot W_a$  →  $L_{aa}$"),
                                    (1, r"mutual: $W_a \cdot W_b$  →  $L_{ab}$")]):
        prod = W[0] * W[j]
        ax.step(x, np.append(W[0], W[0][0]), where="post", color=PH["A"], lw=1.5, label=r"$W_a$")
        if j:
            ax.step(x, np.append(W[j], W[j][0]), where="post", color=PH["B"], lw=1.5, label=r"$W_b$")
        pv = np.append(prod, prod[0])
        ax.fill_between(x, pv, step="post", where=pv >= 0, color=MAIN, alpha=0.25, label="product > 0")
        ax.fill_between(x, pv, step="post", where=pv < 0, color=SLOT, alpha=0.3, label="product < 0")
        ax.axhline(0, color="#999", lw=0.8)
        ax.set_title(title + f"   (sum = {prod.sum():+.1f})", fontsize=10)
        ax.set_xlabel("slot position"); ax.legend(fontsize=8, frameon=False, loc="lower right", ncol=2)
    axs[0].set_ylabel("turns per ampere")
    fig.text(0.5, -0.1, r"$L_{xy} = \dfrac{\mu_0 r_g l_{stk}}{g_e}\,\dfrac{2\pi}{Q}\sum_i W_{x,i} W_{y,i}$"
             "  — the shaded area, net of sign, times the gap permeance per radian", ha="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "winding_function_product.svg", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 6. harmonic split
def fig_harmonics():
    cases = [("36 slots, 4 poles, double layer, pitch 7/9", WindingPattern.distributed(36, 4, pitch=7)),
             ("12 slots, 10 poles, tooth coils", WindingPattern.concentrated(12, 10))]
    fig, axs = plt.subplots(2, 2, figsize=(11, 5.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
    for row, (name, pat) in enumerate(cases):
        Q, p = pat.Q, pat.p
        W = winding_function(pat)[0]
        th = np.linspace(0, 2 * np.pi, 1441)
        a = winding_function_harmonics(pat, p)[0]
        fund = 2 * np.real(a * np.exp(1j * p * th))
        Wc = W[np.floor(th / (2 * np.pi) * Q).astype(int) % Q]
        ax = axs[row, 0]
        ax.plot(th * Q / (2 * np.pi), Wc, color=MAIN, lw=1.6, label="winding function")
        ax.plot(th * Q / (2 * np.pi), fund, "--", color="#222", lw=1, label=rf"fundamental $\nu=p={p}$ → $L_m$")
        ax.fill_between(th * Q / (2 * np.pi), Wc, fund, color=HARM, alpha=0.3, label=r"remainder → $L_\delta$")
        ax.axhline(0, color="#999", lw=0.6)
        ax.set_xlim(0, Q)
        ax.set_ylabel("turns per A")
        ax.legend(fontsize=8, frameon=False, loc="lower left", bbox_to_anchor=(0, 1.01), ncol=3, borderaxespad=0)
        ax.set_title(name, fontsize=10, loc="left", pad=24, y=1.06)
        nus = np.arange(1, 6 * p + 1)
        a_nu = winding_function_harmonics(pat, nus)        # (m, len(nus))
        Wall = winding_function(pat)
        # contribution of each harmonic to the synchronous inductance L_aa - L_ab (Parseval)
        share = 2 * np.real(a_nu[0] * np.conj(a_nu[0] - a_nu[1])) / np.mean(Wall[0] * (Wall[0] - Wall[1]))
        bx = axs[row, 1]
        bx.bar(nus, 100 * share, color=[MAIN if n == p else HARM for n in nus], width=0.7)
        sig = 1 / share[p - 1] - 1
        bx.set_title(rf"share of synchronous $L_{{aa}}-L_{{ab}}$ by harmonic" "\n" rf"$\sigma_\delta = L_\delta/L_m$ = {sig:.3f}",
                     fontsize=9.5, loc="left")
        bx.set_ylabel("%"); bx.set_xlim(0.3, nus[-1] + 0.7)
    axs[1, 0].set_xlabel("slot position around the gap"); axs[1, 1].set_xlabel(r"harmonic order $\nu$ (pole pairs)")
    fig.tight_layout()
    fig.savefig(OUT / "harmonic_split.svg", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ 7. Carter
def fig_carter():
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(8.5, 5.6), sharex=True, gridspec_kw=dict(height_ratios=[1.3, 1]))
    tau, b0, g = 10.0, 3.0, 1.0
    xc = tau / 2
    ax.add_patch(Rectangle((0, -1.5), tau, 1.5, fc=ROTOR, ec=IRON_EDGE))
    ax.add_patch(Polygon([(0, g), (xc - b0 / 2, g), (xc - b0 / 2, g + 2.5), (0, g + 2.5)], fc=IRON, ec=IRON_EDGE))
    ax.add_patch(Polygon([(xc + b0 / 2, g), (tau, g), (tau, g + 2.5), (xc + b0 / 2, g + 2.5)], fc=IRON, ec=IRON_EDGE))
    for x in np.r_[np.linspace(0.4, xc - b0 / 2 - 0.3, 5), np.linspace(xc + b0 / 2 + 0.3, tau - 0.4, 5)]:
        ax.plot([x, x], [0, g], color=MAIN, lw=1.1)
    for r in (0.5, 1.0, 1.45):
        t = np.linspace(0, np.pi / 2, 40)
        for sgn in (-1, 1):
            ax.plot(xc + sgn * (b0 / 2 - r * np.cos(t)), (g + 0.7 * r) * np.sin(t), color=MAIN, lw=1.1)
    ax.annotate("", (tau + 0.4, 0), (tau + 0.4, g), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(tau + 0.6, g / 2, "g", va="center", fontsize=10, style="italic")
    ax.annotate("", (xc - b0 / 2, g + 2.8), (xc + b0 / 2, g + 2.8), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(xc, g + 3.05, r"$b_0$", ha="center", fontsize=10)
    ax.text(xc, g + 1.2, "slot\nopening", ha="center", fontsize=8.5, color="#555")
    ax.text(1.0, g + 1.5, "tooth", fontsize=9, color="#444"); ax.text(tau - 2.2, g + 1.5, "tooth", fontsize=9, color="#444")
    ax.text(tau / 2, -0.9, "rotor surface", ha="center", fontsize=8.5, color="#555")
    ax.text(0, g + 3.9, "(a) the flux fringes into the sides of the tooth tips over the opening", fontsize=10)
    ax.set_ylim(-1.7, g + 4.4); ax.set_aspect("equal"); ax.axis("off")
    # (b) flux density along one slot pitch
    x = np.linspace(0, tau, 600)
    u = (x - xc) / (b0 / 2)
    dip = 0.55 * np.exp(-(u / 0.85) ** 2 * 1.2)
    B = 1 - dip
    Bavg = B.mean()
    bx.plot(x, B, color=MAIN, lw=2, label=r"actual $B(x)$")
    bx.axhline(1, color="#555", lw=0.8, ls=":")
    bx.axhline(Bavg, color=SLOT, lw=1.4, ls="--", label=r"average $=B_{max}/k_C$")
    bx.text(0.2, 1.03, r"$B_{max} = \mu_0 F / g$ under the teeth", fontsize=9)
    bx.text(tau - 0.2, Bavg - 0.08, r"same average with a smooth gap  $g_e = k_C\, g$", ha="right", va="top",
            fontsize=9, color=SLOT)
    bx.annotate("", (0, 0.3), (tau, 0.3), arrowprops=dict(arrowstyle="<->", lw=0.9))
    bx.text(tau / 2, 0.36, r"slot pitch $\tau_s$", ha="center", fontsize=9)
    bx.set_ylim(0.25, 1.15); bx.set_ylabel(r"$B / B_{max}$"); bx.set_xlabel("position along one slot pitch")
    bx.set_xticks([]); bx.legend(loc="center left", fontsize=8.5, frameon=False)
    bx.set_title(r"(b)  $k_C = \tau_s / (\tau_s - \gamma g)$,  $\gamma = (b_0/g)^2 / (5 + b_0/g)$",
                 fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "carter.svg", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig_flux_paths, fig_components, fig_self_mutual, fig_winding_function, fig_product,
              fig_harmonics, fig_carter):
        f()
        print("wrote", f.__name__)
