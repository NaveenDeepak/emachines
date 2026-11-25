"""Generate stator and slot geometry SVGs for emachines.inductance (draft for review)."""
import math, sys
OUT = sys.argv[1]

IRON_F, IRON_S = "#cfd4dc", "#4a5160"
TOP_F, BOT_F = "#f0b45a", "#6fa3ef"
DIM, ACC = "#222", "#c0392b"
HEAD = ('<defs><marker id="ar" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker></defs>')

def svg_open(w, h):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="Helvetica, Arial, sans-serif" font-size="14">', HEAD,
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>']

def sym(name, sub=None, size=14):
    """Italic symbol with optional subscript, as tspans."""
    s = f'<tspan font-style="italic">{name}</tspan>'
    if sub:
        s += f'<tspan font-size="{size-4}" dy="4">{sub}</tspan><tspan dy="-4"> </tspan>'
    return s

def text(x, y, content, anchor="middle", size=14, fill=DIM, extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" fill="{fill}" {extra}>{content}</text>'

def line(x1, y1, x2, y2, w=1.0, dash=None, color=DIM, arrows=False, end_only=False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ' marker-start="url(#ar)" marker-end="url(#ar)"' if arrows else (' marker-end="url(#ar)"' if end_only else "")
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{w}"{d}{m}/>'

def poly(pts, fill, stroke=IRON_S, w=1.2):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{w}"/>'

# ---------------------------------------------------------------- geometry (mm)
Q, r_b, g = 36, 60.0, 0.8
b0, h0, h1, bs, hs, t = 2.5, 1.0, 1.5, 6.0, 18.0, 0.5
h_y = 12.0
r_body = r_b + h0 + h1                 # start of conductor body
r_sb = r_body + hs                     # slot bottom
R_o = r_sb + h_y
def b_of_y(y):                         # body width at depth y (taper t)
    return bs + t * 2 * math.pi * y / Q
bb = b_of_y(hs)
w_t = 2 * math.pi * r_body / Q - bs   # tooth width at the body top

def slot_outline(semi=True, n=12):
    """Local (x, r) outline of one slot, x tangential (mm), going round."""
    right = []
    if semi:
        right += [(b0/2, r_b), (b0/2, r_b + h0), (bs/2, r_body)]
    else:
        right += [(bs/2, r_b)]
    for i in range(n + 1):
        y = hs * i / n
        right.append((b_of_y(y)/2, r_body + y if semi else r_b + y))
    left = [(-x, r) for x, r in reversed(right)]
    return right + left

def region(y0, y1, x0f, x1f, semi=True, n=6, inset=0.35):
    """Conductor region between depths y0..y1, tangential fraction x0f..x1f of local width."""
    base = r_body if semi else r_b
    pts = []
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        hw = b_of_y(y) / 2 - inset
        pts.append((-hw + (2*hw) * x1f, base + y))
    for i in range(n, -1, -1):
        y = y0 + (y1 - y0) * i / n
        hw = b_of_y(y) / 2 - inset
        pts.append((-hw + (2*hw) * x0f, base + y))
    return pts

# ================================================================ Figure 1: stator
def stator_svg():
    W, H = 1000, 500
    s = 7.2                                  # px per mm
    span = 16.0
    cx, cy = 300, 120 - r_b * s              # centre above the canvas: bore at the top
    def P(phi_deg, r):                       # polar -> svg (phi from vertical, + to the right)
        a = math.radians(phi_deg)
        return cx + r * s * math.sin(a), cy + r * s * math.cos(a)
    def L(phic, x, r):                       # local slot coords -> svg
        return P(phic + math.degrees(x / r), r)
    def arc(r, a1, a2, n=80):
        return " ".join(f"{P(a1 + (a2-a1)*i/n, r)[0]:.1f},{P(a1 + (a2-a1)*i/n, r)[1]:.1f}" for i in range(n + 1))
    out = svg_open(W, H)
    out.append(text(300, 24, "Stator cross-section (3 of Q slots)", size=15, extra='font-weight="bold"'))
    rr = r_b - g
    out.append(f'<polyline points="{arc(rr, -span-2, span+2)}" fill="none" stroke="{IRON_S}" stroke-width="1.2" stroke-dasharray="6,4"/>')
    pts = [P(-span + 2*span*i/120, r_b) for i in range(121)] + [P(span - 2*span*i/120, R_o) for i in range(121)]
    out.append(poly(pts, IRON_F))
    for phic in (-10.0, 0.0, 10.0):
        out.append(poly([L(phic, x, r) for x, r in slot_outline()], "#ffffff"))
        sep = 0.6
        out.append(poly([L(phic, x, r) for x, r in region(0.4, hs/2 - sep/2, 0, 1)], TOP_F, stroke=DIM, w=0.7))
        out.append(poly([L(phic, x, r) for x, r in region(hs/2 + sep/2, hs - 0.4, 0, 1)], BOT_F, stroke=DIM, w=0.7))
    for k, phic in zip(("i − 1", "i", "i + 1"), (-10.0, 0.0, 10.0)):
        x, y = P(phic, r_sb + 3.0); out.append(text(x, y + 4, f"slot {k}", size=12, fill=IRON_S))
    x, y = P(0, R_o - 3.5); out.append(text(x, y + 4, "yoke", size=12, fill=IRON_S))
    x, y = P(-5.0, r_body + 9); out.append(text(x, y, "tooth", size=12, fill=IRON_S))
    # rotor label
    x, y = P(-6, rr - 2.8); out.append(text(x, y, "rotor surface", size=12, fill=IRON_S))
    # slot pitch arc between slot centres 0 and +10, on the rotor side
    ra = r_b - 6.2
    out.append(line(*P(0.0, r_b), *P(0.0, ra - 0.8), w=0.7, dash="2,2"))
    out.append(line(*P(10.0, r_b), *P(10.0, ra - 0.8), w=0.7, dash="2,2"))
    out.append(f'<polyline points="{arc(ra, 0.3, 9.7)}" fill="none" stroke="{DIM}" stroke-width="1" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    xm, ym = P(5.0, ra - 1.6)
    out.append(text(xm, ym, sym("τ", "s") + "= 2π" + sym("r", "bore") + "/" + sym("Q"), size=13))
    # tooth width at the body top (tooth between slots 0 and +10)
    xL, yL = L(0.0, bs/2, r_body); xR, yR = L(10.0, -bs/2, r_body)
    out.append(line(xL, yL, xR, yR, arrows=True))
    out.append(text((xL+xR)/2, (yL+yR)/2 + 18, sym("w", "t"), size=13))
    # left call-outs: air gap, bore radius, outer radius
    xa, ya = P(-span + 1.0, r_b - g/2)
    out.append(line(70, 64, xa, ya, end_only=True)); out.append(text(66, 60, sym("g") + " air gap", anchor="end"))
    xa, ya = P(-span + 0.2, r_b + 0.2)
    out.append(line(70, 104, xa, ya, end_only=True)); out.append(text(66, 100, sym("r", "bore"), anchor="end"))
    out.append(text(66, 118, "bore radius", anchor="end", size=11, fill=IRON_S))
    xa, ya = P(-span + 0.6, R_o)
    out.append(line(70, ya + 40, xa, ya, end_only=True)); out.append(text(66, ya + 44, sym("R", "out"), anchor="end"))
    out.append(text(66, ya + 60, "outer radius", anchor="end", size=11, fill=IRON_S))
    # right radial dimensions
    phid = span + 1.4
    def rdim(r1, r2, label):
        x1, y1 = P(phid, r1); x2, y2 = P(phid, r2)
        out.append(line(*P(span, r1), *P(phid + 0.6, r1), w=0.7, dash="2,2"))
        out.append(line(*P(span, r2), *P(phid + 0.6, r2), w=0.7, dash="2,2"))
        out.append(line(x1, y1, x2, y2, arrows=True))
        out.append(text((x1+x2)/2 + 12, (y1+y2)/2 + 5, label, anchor="start"))
    rdim(r_b, r_sb, sym("h", "slot"))
    rdim(r_sb, R_o, sym("h", "y"))
    xm, ym = P(phid, (r_b + r_sb)/2)
    out.append(text(xm + 12, ym + 22, "= " + sym("h", "0") + "+ " + sym("h", "1") + "+ " + sym("h", "s"), anchor="start", size=12))
    # legend + note
    lx, ly = 40, 400
    out.append(f'<rect x="{lx}" y="{ly}" width="18" height="12" fill="{TOP_F}" stroke="{DIM}" stroke-width="0.7"/>')
    out.append(text(lx + 26, ly + 11, "top (gap-side) layer", anchor="start", size=12))
    out.append(f'<rect x="{lx}" y="{ly+20}" width="18" height="12" fill="{BOT_F}" stroke="{DIM}" stroke-width="0.7"/>')
    out.append(text(lx + 26, ly + 31, "bottom layer", anchor="start", size=12))
    out.append(text(lx, ly + 58, "Slot dimensions in the slot figure. Tooth width " + sym("w", "t") + " is measured at the top of the conductor body.", anchor="start", size=12, fill=IRON_S))

    # ---------------- side view (axial section through one slot)
    ox, oy = 700, 110
    sl = 2.0
    l_stk, l_ew = 100.0, 22.0
    hpx = (R_o - r_b) * s * 0.7
    stk_w = l_stk * sl
    out.append(text(ox + stk_w/2, 24, "Side view (axial section)", size=15, extra='font-weight="bold"'))
    out.append(f'<rect x="{ox}" y="{oy}" width="{stk_w:.1f}" height="{hpx:.1f}" fill="{IRON_F}" stroke="{IRON_S}" stroke-width="1.2"/>')
    frac = lambda d: oy + d / (R_o - r_b) * hpx
    out.append(f'<rect x="{ox}" y="{oy}" width="{stk_w:.1f}" height="{frac(r_sb - r_b) - oy:.1f}" fill="#ffffff" stroke="{IRON_S}" stroke-width="0.8"/>')
    y_t0, y_t1 = frac(h0 + h1 + 0.4), frac(h0 + h1 + hs/2 - 0.3)
    y_b0, y_b1 = frac(h0 + h1 + hs/2 + 0.3), frac(r_sb - r_b - 0.4)
    ew = l_ew * sl
    for (y0, y1, f, bend) in ((y_t0, y_t1, TOP_F, -1), (y_b0, y_b1, BOT_F, 1)):
        # straight part through the stack plus end-turn overhangs on both sides
        out.append(f'<rect x="{ox - ew:.1f}" y="{y0:.1f}" width="{stk_w + 2*ew:.1f}" height="{y1 - y0:.1f}" rx="10" fill="{f}" stroke="{DIM}" stroke-width="0.7"/>')
    out.append(line(ox, oy, ox, oy + hpx, w=1.2, color=IRON_S)); out.append(line(ox + stk_w, oy, ox + stk_w, oy + hpx, w=1.2, color=IRON_S))
    yr = oy - 10
    out.append(line(ox - ew - 20, yr, ox + stk_w + ew + 20, yr, w=1.2, dash="6,4", color=IRON_S))
    out.append(text(ox + stk_w/2, yr - 8, "rotor surface", size=12, fill=IRON_S))
    yd = oy + hpx + 30
    for xx in (ox - ew, ox, ox + stk_w, ox + stk_w + ew):
        out.append(line(xx, y_b1 if xx in (ox - ew, ox + stk_w + ew) else oy + hpx, xx, yd + 4, w=0.7, dash="2,2"))
    out.append(line(ox, yd, ox + stk_w, yd, arrows=True)); out.append(text(ox + stk_w/2, yd + 20, sym("l", "stk") + " stack length"))
    out.append(line(ox + stk_w, yd, ox + stk_w + ew, yd, arrows=True)); out.append(line(ox - ew, yd, ox, yd, arrows=True))
    out.append(text(ox + stk_w + ew/2, yd + 20, sym("l", "ew"), size=13)); out.append(text(ox - ew/2, yd + 20, sym("l", "ew"), size=13))
    out.append(text(ox + stk_w/2, oy + hpx - 14, "stator iron", size=12, fill=IRON_S))
    out.append(text(ox + stk_w/2, (y_t0 + y_t1)/2 + 4, "top layer", size=11))
    out.append(text(ox + stk_w/2, (y_b0 + y_b1)/2 + 4, "bottom layer", size=11))
    out.append(text(ox + stk_w/2, yd + 48, "end-winding overhang " + sym("l", "ew") + " beyond each end of the stack", size=12, fill=IRON_S))
    out.append("</svg>")
    return "\n".join(out)

# ================================================================ Figure 2: slot close-up
def slot_svg():
    global h0, h1, r_body
    _saved = (h0, h1, r_body)
    h0, h1 = 1.6, 2.2                    # tooth-tip heights drawn larger for legibility
    r_body = r_b + h0 + h1
    W, H = 1000, 600
    s = 13.0
    out = svg_open(W, H)
    def panel(ox, oy, semi, title):
        """Straight-drawn slot, opening at top. ox = slot centre x, oy = bore line y."""
        X = lambda x: ox + x * s
        Y = lambda d: oy + d * s           # d = depth from bore, mm
        dtot = (h0 + h1 + hs) if semi else hs
        base = (h0 + h1) if semi else 0.0
        out.append(text(ox, 30, title, size=15, extra='font-weight="bold"'))
        # iron block
        half = bb/2 + 4.5
        out.append(poly([(X(-half), Y(0)), (X(half), Y(0)), (X(half), Y(dtot + 3.5)), (X(-half), Y(dtot + 3.5))], IRON_F))
        # slot
        pts = []
        for x, r in slot_outline(semi=semi):
            pts.append((X(x), Y(r - r_b)))
        out.append(poly(pts, "#ffffff"))
        # air gap strip
        out.append(line(X(-half - 1), Y(0) - 10, X(half + 1), Y(0) - 10, w=1.2, dash="6,4", color=IRON_S))
        out.append(text(X(-half) - 4, Y(0) - 14, "air gap", anchor="start", size=11, fill=IRON_S))
        # conductors (over-under)
        sep = 0.6
        for (y0, y1, f, lab) in ((0.4, hs/2 - sep/2, TOP_F, "top"), (hs/2 + sep/2, hs - 0.4, BOT_F, "bottom")):
            rp = region(y0, y1, 0, 1, semi=semi)
            out.append(poly([(X(x), Y(r - r_b)) for x, r in rp], f, stroke=DIM, w=0.7))
            out.append(text(X(0), Y(base + (y0 + y1)/2) + 5, lab, size=12))
        # ---- dimensions
        def hdim(x1, x2, d, label, above=True, dy=18):
            yy = Y(d) - dy if above else Y(d) + dy
            out.append(line(X(x1), Y(d), X(x1), yy, w=0.7, dash="2,2")); out.append(line(X(x2), Y(d), X(x2), yy, w=0.7, dash="2,2"))
            out.append(line(X(x1), yy, X(x2), yy, arrows=True))
            out.append(text((X(x1)+X(x2))/2, yy - 6 if above else yy + 17, label, size=13))
        def vdim(xr, d1, d2, label, side=1, dx=20, xa=None):
            xx = X(xr) + side*dx
            xa = X(xr) if xa is None else xa
            out.append(line(xa, Y(d1), xx + side*4, Y(d1), w=0.7, dash="2,2")); out.append(line(xa, Y(d2), xx + side*4, Y(d2), w=0.7, dash="2,2"))
            out.append(line(xx, Y(d1), xx, Y(d2), arrows=True))
            out.append(text(xx + side*8, (Y(d1)+Y(d2))/2 + 5, label, anchor="start" if side > 0 else "end", size=13))
        if semi:
            hdim(-b0/2, b0/2, 0, sym("b", "0"), above=True, dy=24)
            vdim(half, 0, h0, sym("h", "0"), dx=14, xa=X(b0/2))
            vdim(half, h0, h0 + h1, sym("h", "1"), dx=14, xa=X(bs/2))
            vdim(half, base, base + hs, sym("h", "s"), dx=14, xa=X(bb/2))
            out.append(line(X(-bs/2), Y(base) + 6, X(bs/2), Y(base) + 6, arrows=True))
            out.append(text(X(-bb/2) - 10, Y(base) + 11, sym("b", "s"), anchor="end", size=13))
        else:
            hdim(-bs/2, bs/2, 0, sym("b", "s") + "(= opening)", above=True, dy=24)
            vdim(half, 0, hs, sym("h", "s"), dx=14, xa=X(bb/2))
        hdim(-bb/2, bb/2, base + hs, sym("b", "b") + "= " + sym("b", "s") + "+ " + sym("t") + "·2π" + sym("h", "s") + "/" + sym("Q"), above=False, dy=22)
        # y axis
        ya0 = Y(base); ya1 = Y(base + hs*0.45)
        xa = X(-half) - 26
        out.append(line(xa, ya0, xa, ya1, w=1.2, color=ACC, end_only=True))
        out.append(line(xa - 5, ya0, X(-b_of_y(0)/2), ya0, w=0.7, dash="2,2", color=ACC))
        out.append(text(xa - 6, (ya0+ya1)/2 + 5, sym("y"), anchor="end", fill=ACC))
    panel(200, 110, False, "(a) Open slot")
    panel(560, 110, True, "(b) Semi-closed slot")
    # ---- (c) position layouts
    ox = 830
    out.append(text(ox + 40, 30, "(c) Named positions", size=15, extra='font-weight="bold"'))
    def mini(x0, y0, kind):
        w, h = 46, 110
        out.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#ffffff" stroke="{IRON_S}" stroke-width="1.2"/>')
        if kind == "ou":
            out.append(f'<rect x="{x0+4}" y="{y0+4}" width="{w-8}" height="{h/2-7}" fill="{TOP_F}" stroke="{DIM}" stroke-width="0.7"/>')
            out.append(f'<rect x="{x0+4}" y="{y0+h/2+3}" width="{w-8}" height="{h/2-7}" fill="{BOT_F}" stroke="{DIM}" stroke-width="0.7"/>')
            out.append(text(x0 + w/2, y0 + h/4 + 4, "top", size=11)); out.append(text(x0 + w/2, y0 + 3*h/4 + 4, "bottom", size=10))
            out.append(text(x0 + w/2, y0 + h + 18, "over-under", size=12))
        elif kind == "sbs":
            out.append(f'<rect x="{x0+4}" y="{y0+4}" width="{w/2-6}" height="{h-8}" fill="{TOP_F}" stroke="{DIM}" stroke-width="0.7"/>')
            out.append(f'<rect x="{x0+w/2+2}" y="{y0+4}" width="{w/2-6}" height="{h-8}" fill="{BOT_F}" stroke="{DIM}" stroke-width="0.7"/>')
            out.append(text(x0 + w/4 + 1, y0 + h/2 + 4, "L", size=11)); out.append(text(x0 + 3*w/4 - 1, y0 + h/2 + 4, "R", size=11))
            out.append(text(x0 + w/2, y0 + h + 18, "side-by-side", size=12))
        else:
            n = 6
            for k in range(n):
                f = TOP_F if k % 2 == 0 else BOT_F
                hh = (h - 8) / n
                out.append(f'<rect x="{x0+6}" y="{y0+4+k*hh:.1f}" width="{w-12}" height="{hh-2:.1f}" fill="{f}" stroke="{DIM}" stroke-width="0.7"/>')
                out.append(text(x0 + w/2, y0 + 4 + k*hh + hh/2 + 3, str(k+1), size=10))
            out.append(text(x0 + w/2, y0 + h + 18, "hairpin 1…N", size=12))
    mini(ox - 30, 110, "ou"); mini(ox + 50, 110, "sbs"); mini(ox + 10, 290, "hp")
    # notes
    notes = [
        "Conductor-body width at depth " + sym("y") + ":  " + sym("b") + "(" + sym("y") + ") = " + sym("b", "s") + "+ " + sym("t") + "·2π" + sym("y") + "/" + sym("Q"),
        sym("t") + " = 0 parallel slot,  " + sym("t") + " = 1 parallel tooth (constant tooth width " + sym("w", "t") + "),  0 < " + sym("t") + " < 1 in between.",
        "Open slot: " + sym("b", "0") + " = " + sym("b", "s") + ",  " + sym("h", "0") + " = " + sym("h", "1") + " = 0.   An optional separator " + sym("h", "sep") + " sits between layers.",
    ]
    for k, n in enumerate(notes):
        out.append(text(40, 520 + 22*k, n, anchor="start", size=13))
    out.append(text(960, 590, "tip heights not to scale", anchor="end", size=11, fill=IRON_S))
    out.append("</svg>")
    h0, h1, r_body = _saved
    return "\n".join(out)

open(f"{OUT}/stator_geometry.svg", "w").write(stator_svg())
open(f"{OUT}/slot_geometry.svg", "w").write(slot_svg())
print("ok", round(bb, 3), round(w_t, 3))
