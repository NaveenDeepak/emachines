"""Generate the slot-leakage figures for nbs/inductance/04_slot_leakage.ipynb.

Run from the repository root:  python nbs/inductance/images/make_slot_figs.py
"""
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle

from emachines.inductance import SlotGeometry, StatorGeometry
from emachines.inductance.slot import _below_share, slot_permeance

OUT = Path(__file__).parent
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "svg.fonttype": "path", "svg.hashsalt": "emachines",
                     "axes.spines.top": False, "axes.spines.right": False})
IRON, IRON_EDGE, LEAK = "#cfd4dc", "#4a5160", "#e07b00"
LAYER = ["#d9534f", "#f0ad4e", "#5b8def"]


def fig_field():
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.5, 5.2), gridspec_kw=dict(width_ratios=[1.15, 1.0], wspace=0.2))
    # (a) slot drawn with the air gap at the bottom; depth y grows upwards in the picture
    bs, hs, tw, h_tip = 5.0, 24.0, 6.0, 3.0
    yb = 3.0                                     # top of the conductor body (gap side), in picture units
    ax.add_patch(Rectangle((-bs / 2 - tw, 0), bs + 2 * tw, yb + hs + 6, fc=IRON, ec=IRON_EDGE))
    ax.add_patch(Polygon([(-1.2, 0), (-1.2, 1.4), (-bs / 2, yb), (-bs / 2, yb + hs), (bs / 2, yb + hs), (bs / 2, yb),
                          (1.2, 1.4), (1.2, 0)], fc="white", ec=IRON_EDGE))
    for k in range(3):
        y0, y1 = yb + k * hs / 3, yb + (k + 1) * hs / 3
        ax.add_patch(Rectangle((-bs / 2 + 0.3, y0 + 0.3), bs - 0.6, hs / 3 - 0.6, fc=LAYER[k], alpha=0.35, ec="none"))
        ax.text(0, (y0 + y1) / 2, f"layer {k + 1}", ha="center", va="center", fontsize=9)
    for y in np.linspace(yb + 2, yb + hs - 1.5, 6):
        ax.add_patch(FancyArrowPatch((-bs / 2 - 0.2, y), (bs / 2 + 0.2, y), arrowstyle="-|>", mutation_scale=10,
                                     color=LEAK, lw=1.3, zorder=5))
        ax.plot([bs / 2 + 0.2, bs / 2 + tw * 0.6, bs / 2 + tw * 0.6], [y, y, yb + hs + 4], color=LEAK, lw=0.6, alpha=0.5)
        ax.plot([-bs / 2 - 0.2, -bs / 2 - tw * 0.6, -bs / 2 - tw * 0.6], [y, y, yb + hs + 4], color=LEAK, lw=0.6, alpha=0.5)
    yd = yb + hs / 3 * 1.45
    ax.plot([-bs / 2 - tw, bs / 2 + tw], [yd, yd], "k--", lw=1)
    ax.annotate("flux crossing at depth y\nlinks only the turns\ndeeper than y\n(above the line here)",
                (bs / 2 + tw, yd), (bs / 2 + tw + 1.0, yd + 5), fontsize=8.5, va="center",
                arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.text(0, -1.4, "air gap", ha="center", fontsize=9, color="#555")
    ax.text(-bs / 2 - tw + 0.3, yb + hs + 4.5, "yoke", fontsize=9, color="#444")
    ax.text(-bs / 2 - tw + 0.3, 1.0, "tooth", fontsize=9, color="#444")
    ax.annotate("", (-bs / 2 - tw - 1.0, yb), (-bs / 2 - tw - 1.0, yd), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text(-bs / 2 - tw - 1.5, (yb + yd) / 2, "y", ha="right", va="center", style="italic")
    ax.text(-bs / 2 - tw - 1.6, yb + hs + 7.5, "(a) leakage flux across a three-layer slot", fontsize=10)
    ax.set_xlim(-bs / 2 - tw - 3, bs / 2 + tw + 13); ax.set_ylim(-2.5, yb + hs + 8.5)
    ax.set_aspect("equal"); ax.axis("off")
    # (b) A_r(y) and F(y)
    st = StatorGeometry(Q=48, r_bore=80e-3, g=0.6e-3, l_stk=0.15, h_y=15e-3, slot=SlotGeometry.open(5e-3, 24e-3))
    regs = st.regions("over_under", 3)
    y = np.linspace(0, st.slot.hs, 400)
    F = np.zeros_like(y)
    for k, r in enumerate(regs):
        A = _below_share(st.slot, st.Q, r, y)
        F += A
        bx.plot(A, y * 1e3, color=LAYER[k], lw=2, label=f"$A_{k + 1}(y)$, layer {k + 1}")
    bx.plot(F, y * 1e3, "k--", lw=1.5, label=r"$F(y)/(n\,i) = \sum_r A_r$ (equal currents)")
    bx.set_ylabel("depth y [mm]   (0 = air-gap side, 24 = slot bottom)")
    bx.set_xlabel("share of turns deeper than y")
    bx.legend(fontsize=8.5, frameon=False, loc="upper right")
    bx.set_title(r"(b)  $\Lambda_{rs} = \int A_r A_s / b\,dy$  →  self 1 : 4 : 7", fontsize=10, loc="left")
    fig.savefig(OUT / "slot_leakage_field.svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


def fig_taper():
    base = StatorGeometry(Q=48, r_bore=80e-3, g=0.6e-3, l_stk=0.15, h_y=15e-3, slot=SlotGeometry.open(5e-3, 24e-3))
    semi = replace(base, slot=SlotGeometry.semi_closed(b0=2e-3, h0=1e-3, h1=1.5e-3, bs=5e-3, hs=24e-3))
    ts = np.linspace(0, 1, 41)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.5, 3.8))
    for st, name, ls in [(base, "open", "-"), (semi, "semi-closed", "--")]:
        d = np.array([np.diag(slot_permeance(replace(st, slot=replace(st.slot, t=t)), "over_under", 3)) for t in ts])
        if name == "open":
            for k in range(3):
                ax.plot(ts, d[:, k], color=LAYER[k], lw=2, label=f"layer {k + 1}")
        bx.plot(ts, 100 * (d[:, 2] - d[:, 0]) / d.mean(axis=1), ls, color="#333", lw=2, label=f"{name} slot")
    ax.set_xlabel("taper t  (0 = parallel slot, 1 = parallel tooth)"); ax.set_ylabel(r"self permeance $\Lambda_{rr}$")
    ax.set_title("(a) open slot, 3 equal-area layers", fontsize=10, loc="left"); ax.legend(frameon=False, fontsize=9)
    bx.set_xlabel("taper t"); bx.set_ylabel("layer spread [%]"); bx.set_ylim(0, None)
    bx.set_title(r"(b) $(\Lambda_{33} - \Lambda_{11}) / \overline{\Lambda}$", fontsize=10, loc="left")
    bx.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "layer_taper.svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    fig_field()
    fig_taper()
    print("ok")
