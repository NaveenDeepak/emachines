"""Generate the end-turn and winding-comparison figures for nbs/inductance/05_end_winding and 06_stator.

Run from the repository root:  python nbs/inductance/images/make_end_figs.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, Wedge

from emachines.inductance import EndTurn, SlotGeometry, StatorGeometry, stator_inductances
from emachines.winding import Coil, WindingPattern

OUT = Path(__file__).parent
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "svg.fonttype": "path", "svg.hashsalt": "emachines",
                     "axes.spines.top": False, "axes.spines.right": False})
IRON, IRON_EDGE = "#cfd4dc", "#4a5160"
LAYER = ["#d9534f", "#f0ad4e", "#5b8def"]
PART_COL = {"magnetising": "#1f5fbf", "harmonic": "#7f7f7f", "slot": "#e07b00", "tooth_tip": "#2e9d48",
            "end_winding": "#8e44ad"}


def fig_end_turn():
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw=dict(width_ratios=[1.25, 1]))
    # (a) side view: stack on the left, conductors of 3 layers leaving the slot and bending at their tier
    ax.add_patch(Rectangle((0, 0), 6, 10, fc=IRON, ec=IRON_EDGE))
    ax.text(3, 10.5, "stator stack", ha="center", fontsize=9, color="#444")
    l_ext, tiers = 3.0, [2.4, 1.2, 0.0]
    for k, (y, tier) in enumerate(zip([7.6, 5.0, 2.4], tiers)):      # layer 1 nearest the gap (top here)
        x_end = 6 + l_ext + tier
        ax.plot([1, x_end], [y, y], color=LAYER[k], lw=5, solid_capstyle="butt", alpha=0.85)
        ax.plot([x_end, x_end + 1.4], [y, y - 0.0], color=LAYER[k], lw=5, alpha=0.35, solid_capstyle="round")
        ax.text(x_end + 1.6, y, f"layer {k + 1}: bends at $l_{{ext}} + \\Delta_{k + 1}$", va="center", fontsize=9)
    ax.annotate("", (6, -0.8), (6 + l_ext, -0.8), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(6 + l_ext / 2, -1.5, "$l_{ext}$", ha="center", fontsize=10)
    ax.annotate("", (6 + l_ext, 9.0), (6 + l_ext + tiers[0], 9.0), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(6 + l_ext + tiers[0] / 2, 9.4, r"$\Delta_1$ (tier)", ha="center", fontsize=9)
    ax.plot([6 + l_ext] * 2, [-0.5, 9.3], ":", color="#888", lw=0.8)
    ax.text(-0.3, 12, "(a) side view: each layer leaves the slot and bends at its own axial distance", fontsize=10)
    ax.set_xlim(-0.5, 21); ax.set_ylim(-2.2, 12.6); ax.set_aspect("equal"); ax.axis("off")
    # (b) end view: arc across the coil span at the conductors' mean radius
    Q, r_b, r_o = 24, 5.0, 8.6
    bx.add_patch(Wedge((0, 0), r_o, 20, 160, width=r_o - r_b, fc=IRON, ec=IRON_EDGE))
    for i in range(Q):
        th = np.radians(i * 360 / Q)
        if 20 < np.degrees(th) < 160:
            bx.add_patch(Rectangle((0, 0), 0.5, 2.2, angle=0, fc="white", ec=IRON_EDGE, lw=0.6,
                                   transform=matplotlib.transforms.Affine2D().translate(-0.25, r_b).rotate(th - np.pi / 2)
                                   + bx.transData))
    a0, a1, r_mid = np.radians(45), np.radians(120), r_b + 1.1
    t = np.linspace(a0, a1, 60)
    bx.plot(r_mid * np.cos(t), r_mid * np.sin(t), color=LAYER[1], lw=3.5)
    for a in (a0, a1):
        bx.plot([0, (r_o + 0.6) * np.cos(a)], [0, (r_o + 0.6) * np.sin(a)], ":", color="#888", lw=0.8)
    bx.annotate("", (0, 0), (r_mid * np.cos(np.radians(150)), r_mid * np.sin(np.radians(150))),
                arrowprops=dict(arrowstyle="<-", lw=0.9))
    bx.text(-3.7, 2.4, r"$r_{mid}$", fontsize=10)
    bx.text(0, r_o + 1.4, r"arc $= k_{arc}\,s\,2\pi r_{mid}/Q$", ha="center", fontsize=10)
    bx.text(1.6, 1.2, "span s\n(slots)", fontsize=9, ha="center")
    bx.text(-r_o, r_o + 2.6, "(b) end view", fontsize=10)
    bx.set_xlim(-r_o - 1, r_o + 1); bx.set_ylim(-0.5, r_o + 3); bx.set_aspect("equal"); bx.axis("off")
    fig.savefig(OUT / "end_turn_geometry.svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


def ep2237392(turns=2):
    coils = []
    for ph, (start, sign0) in enumerate([(0, 1), (4, -1), (8, 1)]):
        for pole in range(4):
            s0, sign = start + 12 * pole, sign0 * (-1) ** pole
            for k in range(6):
                a, b = (s0 + 5 - k) % 48, (s0 + 6 + k) % 48
                if sign < 0:
                    a, b = b, a
                coils.append(Coil(ph, a, str(ph + 1), b, str(ph + 1), turns))
    return WindingPattern.custom(48, 4, coils, layout="over_under", n_layers=3, name="EP2237392\n(one phase per layer)")


def fig_comparison():
    st = StatorGeometry(Q=48, r_bore=80e-3, g=0.6e-3, l_stk=150e-3, h_y=15e-3, l_ew=30e-3,
                        slot=SlotGeometry.open(5e-3, 24e-3))
    end = EndTurn(l_ext=12e-3, tier={"1": 16e-3, "2": 8e-3, "3": 0.0})
    pats = [ep2237392(), WindingPattern.distributed(48, 4, pitch=10, turns=3),
            WindingPattern.distributed(48, 4, layers=1, turns=6)]
    labels = ["EP2237392\n(one phase per layer)", "double layer\npitch 10/12", "single layer\nfull pitch"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw=dict(width_ratios=[1, 1]))
    for i, (pat, lab) in enumerate(zip(pats, labels)):
        s = stator_inductances(pat, st, end, fill=0.45, T=120)
        bottom = bottom_l = 0.0
        for part, col in PART_COL.items():
            v = s.positive(part) * 1e3
            ax.bar(i, v, bottom=bottom, color=col, width=0.55, label=part.replace("_", " ") if i == 0 else None)
            bottom += v
            if part != "magnetising":
                bx.bar(i, v * 1e3, bottom=bottom_l, color=col, width=0.55)
                bottom_l += v * 1e3
        imb = s.imbalance()
        ax.text(i, bottom + 0.4, f"L self spread {100 * imb['self_spread']:.1f}%\nR spread {100 * imb['R_spread']:.1f}%",
                ha="center", fontsize=8.5)
    for a_ in (ax, bx):
        a_.set_xticks(range(3)); a_.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("positive-sequence inductance [mH]"); ax.set_ylim(0, 22)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("(a) all parts", fontsize=10, loc="left")
    bx.set_ylabel("[µH]"); bx.set_title("(b) leakage parts only", fontsize=10, loc="left")
    fig.suptitle("48 slots, 4 poles, 48 series turns per phase, 120 °C, fill 0.45 (dimensions assumed)",
                 fontsize=10, x=0.02, ha="left")
    fig.tight_layout()
    fig.savefig(OUT / "winding_comparison.svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    fig_end_turn()
    fig_comparison()
    print("ok")
