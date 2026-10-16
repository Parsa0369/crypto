"""Compact CryptoPulse terminal intro with Windows-safe colors and progress bars."""

from __future__ import annotations

import colorsys
import ctypes
import math
import os
import re
import shutil
import sys
import time


ESC = "\033["
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
GREEN = f"{ESC}92m"
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
CLEAR = f"{ESC}2J{ESC}H"


def enable_terminal_colors() -> bool:
    """Enable VT processing on Windows consoles; never print raw escapes as fallback."""
    if not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetStdHandle.argtypes = [ctypes.c_ulong]
        kernel32.GetStdHandle.restype = ctypes.c_void_p
        kernel32.GetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel32.GetConsoleMode.restype = ctypes.c_int
        kernel32.SetConsoleMode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel32.SetConsoleMode.restype = ctypes.c_int

        # STD_OUTPUT_HANDLE is the unsigned DWORD value 0xFFFFFFF5 (-11).
        stdout_handle = kernel32.GetStdHandle(ctypes.c_ulong(0xFFFFFFF5))
        mode = ctypes.c_ulong()
        if not stdout_handle or not kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode)):
            return False

        # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return bool(kernel32.SetConsoleMode(stdout_handle, mode.value | 0x0004))
    except Exception:
        return False


RESET = "\033[0m"

SIZE = 56            # اندازه‌ی کانوا (پیکسل)؛ هر کاراکتر = ۲ پیکسل عمودی
SS = 2               # سوپرسمپلینگ برای لبه‌های نرم
SHADOW = (24, 30, 44)
SHADOW_OFFSET = 0.06

GREEN = (68, 214, 44)        # سبز اسیدی (مار اول)
BLUE = (55, 118, 171)        # آبی (مار دوم)
YELLOW = (255, 212, 59)      # زرد (چشم‌ها)
BOLT_TOP, BOLT_BOT = (255, 247, 140), (255, 160, 20)
AURA_COLOR = (255, 215, 70)
WHITE = (255, 255, 255)

RING_IN = 0.88               # شعاع داخلی حلقه‌ی سکه
AURA = 0.16                  # شعاع هاله‌ی صاعقه
_LX, _LY = -0.58, -0.81      # جهت نور (بالا-چپ)

# صاعقه (مختصات نرمال‌شده)
BOLT = ((0.10, -0.54), (-0.24, 0.05), (-0.03, 0.05), (-0.13, 0.54), (0.25, -0.10), (0.04, -0.10))
_BY0, _BY1 = -0.54, 0.54


def _scale(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------- دو مار (گردابی، مثل یین‌یانگ) ----------
def _make_arms(n=120, sweep=3.7):
    arms = []
    for k in range(2):
        a0 = -2.9 + k * math.pi
        pts = []
        for i in range(n + 1):
            t = i / n
            r = 0.04 + 0.60 * t
            a = a0 + sweep * t
            w = 0.035 + 0.17 * t ** 1.6              # دم باریک، سر پهن
            pts.append((r * math.cos(a), r * math.sin(a), w, t))
        arms.append(pts)
    return arms


ARMS = _make_arms()
PAL = (GREEN, BLUE)


def _eye(pts, side):
    qx, qy, w, t = pts[int(len(pts) * 0.86)]
    r = math.hypot(qx, qy) or 1.0
    return (qx + side * qx / r * w * 0.45, qy + side * qy / r * w * 0.45)


EYES = [_eye(ARMS[0], 1), _eye(ARMS[1], 1)]


def _poly_dist(x, y):
    """فاصله‌ی علامت‌دار تا صاعقه؛ منفی = داخل."""
    inside, best = False, 9.0
    n = len(BOLT)
    for i in range(n):
        ax, ay = BOLT[i]
        bx, by = BOLT[(i + 1) % n]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return -best if inside else best


def _base(nx, ny):
    """رنگ ثابت (سکه + مارها)؛ بیرون دایره None."""
    r = math.hypot(nx, ny)
    if r > 1:
        return None
    ang = math.degrees(math.atan2(ny, nx)) % 360

    if r >= RING_IN:                                  # حلقه‌ی سکه (لبه‌ی دندانه‌دار)
        k = (r - RING_IN) / (1 - RING_IN)
        cross = (k - 0.5) * 2
        rx, ry = nx / r, ny / r
        dot = (rx * _LX + ry * _LY) * cross * 0.8 + math.sqrt(max(0.0, 1 - cross * cross)) * 0.55
        f = 0.50 + 0.70 * max(0.0, dot)
        col = _mix(GREEN, BLUE, (1 + math.cos(math.radians(ang - 40))) / 2)
        col = _scale(col, f)
        if f > 1.0:
            col = _mix(col, WHITE, (f - 1.0) * 0.9)
        if ang % 15 < 1.6:
            col = _scale(col, 0.72)
        return col

    best = None
    for ki, pts in enumerate(ARMS):                   # مارها
        for (qx, qy, w, t) in pts:
            dx, dy = nx - qx, ny - qy
            d = math.hypot(dx, dy)
            if d < w and (best is None or d / w < best[0]):
                best = (d / w, ki, t, dx / w, dy / w)
    for ex, ey in EYES:
        if math.hypot(nx - ex, ny - ey) < 0.05:
            return YELLOW
    if best is not None:
        cross, ki, t, ux, uy = best
        nz = math.sqrt(max(0.0, 1 - cross * cross))
        dot = (ux * _LX + uy * _LY) * 0.8 + nz * 0.55
        f = 0.45 + 0.75 * max(0.0, min(1.0, dot))
        if int(t * 20) % 2 == 0 and cross < 0.85:     # خط‌های فلس روی بدنه
            f *= 0.88
        col = _scale(PAL[ki], f)
        if f > 1.0:
            col = _mix(col, WHITE, (f - 1.0) * 1.1)
        return col

    if 0.855 < r < 0.875:                             # خط باریک داخلی سکه
        return _scale(_mix(GREEN, BLUE, (1 + math.cos(math.radians(ang - 40))) / 2), 0.45)
    return _mix((18, 27, 50), (6, 9, 20), r / RING_IN)  # صفحه‌ی تیره‌ی سکه


_GRID = None


def _build():
    half = SIZE / 2
    cx = cy = half - 1.0
    scale = half * 0.92
    grid = []
    for py in range(SIZE):
        row = []
        for px in range(SIZE):
            samples = []
            for i in range(SS):
                for j in range(SS):
                    nx = (px + (i + 0.5) / SS - cx) / scale
                    ny = (py + (j + 0.5) / SS - cy) / scale
                    b = _base(nx, ny)
                    if b is None:
                        sh = math.hypot(nx - SHADOW_OFFSET, ny - SHADOW_OFFSET) <= 1
                        samples.append((None, 9.0, ny, sh))
                    else:
                        samples.append((b, _poly_dist(nx, ny), ny, False))
            row.append(samples)
        grid.append(row)
    return grid


def _resolve(samples, glow):
    acc, n, sh = [0, 0, 0], 0, 0
    for base, bd, ny, shadow in samples:
        if base is None:
            sh += shadow
            continue
        if bd < 0:                                    # داخل صاعقه
            col = _mix(BOLT_TOP, BOLT_BOT, (ny - _BY0) / (_BY1 - _BY0))
            if -bd < 0.028:
                col = _mix(col, WHITE, 0.55 * (1 - -bd / 0.028))
            col = _scale(col, 0.80 + 0.30 * glow)
        elif bd < AURA:                               # هاله‌ی نور
            col = _mix(base, AURA_COLOR, glow * (1 - bd / AURA) ** 2 * 0.65)
        else:
            col = base
        acc[0] += col[0]; acc[1] += col[1]; acc[2] += col[2]
        n += 1
    total = len(samples)
    if n * 2 >= total:
        return (acc[0] // n, acc[1] // n, acc[2] // n)
    if sh * 2 >= total:
        return SHADOW
    return None


def _code(rgb, truecolor):
    if truecolor:
        return f"2;{rgb[0]};{rgb[1]};{rgb[2]}"
    return f"5;{16 + 36 * round(rgb[0] / 51) + 6 * round(rgb[1] / 51) + round(rgb[2] / 51)}"


def _frame(glow, truecolor=True):
    global _GRID
    if _GRID is None:
        _GRID = _build()
    px = [[_resolve(s, glow) for s in row] for row in _GRID]
    rows = []
    for r in range(SIZE // 2):
        line = []
        for x in range(SIZE):
            top, bot = px[2 * r][x], px[2 * r + 1][x]
            if top is None and bot is None:
                line.append(" ")
            elif bot is None:
                line.append(f"\033[38;{_code(top, truecolor)}m▀")
            elif top is None:
                line.append(f"\033[38;{_code(bot, truecolor)}m▄")
            else:
                line.append(f"\033[38;{_code(top, truecolor)};48;{_code(bot, truecolor)}m▀\033[49m")
        rows.append("".join(line) + RESET)
    return "\n".join(rows)


def _caption():
    pad = " " * ((SIZE - 26) // 2)
    return (f"{pad}\033[1;38;5;75mP Y T H O N\033[0m \033[38;5;220m ⚡ \033[0m "
            f"\033[1;38;5;82mC R Y P T O\033[0m")


def snake_bolt_logo(ansi_enabled: bool = True, truecolor: bool = True,
                    glow: float = 1.0, caption: bool = True) -> str:
    """سکه‌ی کریپتو + دو مار (سبز و آبی) + صاعقه‌ی ⚡. glow = شدت نور صاعقه."""
    if not ansi_enabled:
        return _plain()
    out = _frame(glow, truecolor)
    return out + "\n" + _caption() if caption else out


def _flash(t):
    """الگوی برق: دو جرقه‌ی پشت‌سرهم و محو شدن؛ دوره‌ی ۱.۲ ثانیه."""
    t %= 1.2
    return max(math.exp(-((t - 0.10) / 0.04) ** 2), 0.8 * math.exp(-((t - 0.26) / 0.05) ** 2),
               0.35 * math.exp(-max(0.0, t - 0.3) / 0.35))


def flash_snake_bolt(seconds: float = 4.0, truecolor: bool = True, ansi_enabled: bool = True,
                     caption: bool = True) -> None:
    """انیمیشن: صاعقه جرقه می‌زنه و نورش روی سکه و مارها می‌افته؛ در پایان روشن می‌مونه."""
    if not ansi_enabled or not sys.stdout.isatty():
        print(snake_bolt_logo(ansi_enabled, truecolor, caption=caption))
        return
    height = SIZE // 2 + (1 if caption else 0)
    out = sys.stdout
    out.write("\033[?25l")
    try:
        start = time.perf_counter()
        first = True
        while True:
            el = time.perf_counter() - start
            done = el >= seconds
            g = 1.0 if done else 0.25 + 0.95 * _flash(el)
            if not first:
                out.write(f"\033[{height}A")
            text = _frame(g, truecolor)
            out.write((text + "\n" + _caption() if caption else text) + "\n")
            out.flush()
            first = False
            if done:
                break
    finally:
        out.write("\033[?25h")
        out.flush()


def _plain():
    W, H = 44, 22
    out = []
    for y in range(H):
        row = []
        for x in range(W):
            nx, ny = ((x + 0.5) / W * 2 - 1) / 0.92, ((y + 0.5) / H * 2 - 1) / 0.92
            b = _base(nx, ny)
            if b is None:
                row.append(" ")
            elif _poly_dist(nx, ny) < 0:
                row.append("Z")
            elif math.hypot(nx, ny) >= RING_IN:
                row.append("o")
            else:
                row.append("S" if max(b) > 70 and (b[1] > b[2] or b[2] > b[0]) and sum(b) > 160 else " ")
        out.append("".join(row))
    return "\n".join(out)


# ---------- Original standalone 3D lightning animation ----------
_lightning_RESET = "\033[0m"

_lightning_W, _lightning_H = 56, 64             # اندازه‌ی کانوا به پیکسل (هر کاراکتر = ۲ پیکسل عمودی)
_lightning_SS = 2                    # سوپرسمپلینگ برای لبه‌های نرم
_lightning_SHADOW = (26, 22, 8)
_lightning_SHADOW_OFFSET = 0.05

_lightning_BOLT_TOP, _lightning_BOLT_BOT = (255, 247, 140), (255, 160, 20)
_lightning_HOT = (255, 255, 235)     # هسته‌ی داغ صاعقه
_lightning_AURA_COLOR = (255, 205, 60)
_lightning_WHITE = (255, 255, 255)

# شکل صاعقه (مختصات نرمال‌شده؛ y به سمت پایین)
_lightning_BOLT = ((0.17, -0.92), (-0.41, 0.09), (-0.05, 0.09), (-0.22, 0.92), (0.43, -0.17), (0.07, -0.17))
_lightning_Y0, _lightning_Y1 = -0.92, 0.92

_lightning_L = (-0.45, -0.55, 0.70)
_lightning_LN = math.sqrt(sum(v * v for v in _lightning_L))
_lightning_LIGHT = tuple(v / _lightning_LN for v in _lightning_L)


def _lightning_scale(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _lightning_mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _lightning_poly_dist(x, y, ox=0.0, oy=0.0):
    """فاصله‌ی علامت‌دار تا صاعقه؛ منفی = داخل."""
    x, y = x - ox, y - oy
    inside, best = False, 9.0
    n = len(_lightning_BOLT)
    for i in range(n):
        ax, ay = _lightning_BOLT[i]
        bx, by = _lightning_BOLT[(i + 1) % n]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return -best if inside else best


_lightning_GRID = None


def _lightning_build():
    """بخش‌های ثابت (شکل، بیول، سایه) رو یک‌بار پیش‌محاسبه می‌کنه."""
    scale = _lightning_H / 2 * 0.92
    cx, cy = _lightning_W / 2, _lightning_H / 2
    e = 0.01
    grid = []
    for py in range(_lightning_H):
        row = []
        for px in range(_lightning_W):
            samples = []
            for i in range(_lightning_SS):
                for j in range(_lightning_SS):
                    nx = (px + (i + 0.5) / _lightning_SS - cx) / scale
                    ny = (py + (j + 0.5) / _lightning_SS - cy) / scale
                    bd = _lightning_poly_dist(nx, ny)
                    if bd < 0:                                   # داخل صاعقه
                        gx = _lightning_poly_dist(nx + e, ny) - _lightning_poly_dist(nx - e, ny)
                        gy = _lightning_poly_dist(nx, ny + e) - _lightning_poly_dist(nx, ny - e)
                        gl = math.hypot(gx, gy) or 1.0
                        t = min(1.0, -bd / 0.10)                 # عمق بیول
                        n = (gx / gl * (1 - t), gy / gl * (1 - t), t)
                        nl = math.sqrt(sum(v * v for v in n)) or 1.0
                        dot = max(0.0, (n[0] * _lightning_LIGHT[0] + n[1] * _lightning_LIGHT[1] + n[2] * _lightning_LIGHT[2]) / nl)
                        light = 0.60 + 0.65 * dot
                        u = nx * 0.7 + ny * 0.7                  # مختصات برای درخشش متحرک
                        samples.append((True, bd, light, ny, u, False))
                    else:
                        sh = _lightning_poly_dist(nx, ny, _lightning_SHADOW_OFFSET, _lightning_SHADOW_OFFSET) < 0
                        samples.append((False, bd, 0.0, ny, 0.0, sh))
            row.append(samples)
        grid.append(row)
    return grid


def _lightning_resolve(samples, glow, shimmer):
    acc, n, sh = [0, 0, 0], 0, 0
    aura_r = 0.34 * (0.55 + 0.6 * glow)
    for inside, bd, light, ny, u, shadow in samples:
        if inside:
            col = _lightning_mix(_lightning_BOLT_TOP, _lightning_BOLT_BOT, (ny - _lightning_Y0) / (_lightning_Y1 - _lightning_Y0))
            col = _lightning_scale(col, light * (0.82 + 0.26 * glow))
            depth = -bd
            if depth > 0.11:                                      # هسته‌ی داغ
                col = _lightning_mix(col, _lightning_HOT, 0.30 * glow)
            if depth < 0.03:                                      # لبه‌ی روشن
                col = _lightning_mix(col, _lightning_WHITE, 0.55 * (1 - depth / 0.03) * (0.5 + 0.5 * glow))
            if shimmer is not None:                               # درخشش عبوری
                col = _lightning_mix(col, _lightning_WHITE, 0.6 * math.exp(-((u - shimmer) / 0.13) ** 2))
        else:
            a = glow * (1 - bd / aura_r) ** 2 * 0.80 if bd < aura_r else 0.0
            if a > 0.05:                                          # هاله‌ی نور
                col = _lightning_scale(_lightning_AURA_COLOR, a)
            else:
                sh += shadow
                continue
        acc[0] += col[0]; acc[1] += col[1]; acc[2] += col[2]
        n += 1
    total = len(samples)
    if n * 2 >= total:
        return (acc[0] // n, acc[1] // n, acc[2] // n)
    if sh * 2 >= total and _lightning_SHADOW:
        return _lightning_SHADOW
    return None


def _lightning_code(rgb, truecolor):
    if truecolor:
        return f"2;{rgb[0]};{rgb[1]};{rgb[2]}"
    return f"5;{16 + 36 * round(rgb[0] / 51) + 6 * round(rgb[1] / 51) + round(rgb[2] / 51)}"


def _lightning_frame(glow, shimmer=None, truecolor=True):
    global _lightning_GRID
    if _lightning_GRID is None:
        _lightning_GRID = _lightning_build()
    px = [[_lightning_resolve(s, glow, shimmer) for s in row] for row in _lightning_GRID]
    rows = []
    for r in range(_lightning_H // 2):
        line = []
        for x in range(_lightning_W):
            top, bot = px[2 * r][x], px[2 * r + 1][x]
            if top is None and bot is None:
                line.append(" ")
            elif bot is None:
                line.append(f"\033[38;{_lightning_code(top, truecolor)}m▀")
            elif top is None:
                line.append(f"\033[38;{_lightning_code(bot, truecolor)}m▄")
            else:
                line.append(f"\033[38;{_lightning_code(top, truecolor)};48;{_lightning_code(bot, truecolor)}m▀\033[49m")
        rows.append("".join(line) + _lightning_RESET)
    return "\n".join(rows)


def bolt_logo(ansi_enabled: bool = True, truecolor: bool = True, glow: float = 1.0) -> str:
    """یک صاعقه‌ی ⚡ سه‌بعدی (تصویر ثابت)."""
    if not ansi_enabled:
        return "\n".join(["      /\\", "     /  /", "    /  /", "   /  /___", "  /      /",
                          "  ‾‾/  /‾‾", "   /  /", "  / /", " //"])
    return _lightning_frame(glow, None, truecolor)


def _lightning_glow_at(t):
    """نور صاعقه در زمان t: نفس‌کشیدن آروم + جرقه‌های دوتایی هر ۲.۵ ثانیه."""
    breath = 0.50 + 0.12 * math.sin(2 * math.pi * t / 1.6)
    c = t % 2.5
    flash = max(math.exp(-((c - 0.20) / 0.05) ** 2),
                0.85 * math.exp(-((c - 0.40) / 0.06) ** 2),
                0.40 * math.exp(-max(0.0, c - 0.5) / 0.30))
    flicker = 0.04 * math.sin(41 * t) * math.sin(13 * t)
    return max(0.0, min(1.2, max(breath, 0.35 + 0.85 * flash) + flicker))


def _lightning_shimmer_at(t):
    """درخششی که هر ۱.۲۵ ثانیه از گوشه‌ی بالا-چپ به پایین-راست روی صاعقه می‌رد شه."""
    p = (t % 1.25) / 0.55
    return None if p > 1 else -1.5 + 3.0 * p


def bolt_animation(seconds: float = 10.0, truecolor: bool = True, ansi_enabled: bool = True,
                   clear_after: bool = False) -> None:
    """فقط یه ⚡ سه‌بعدی و متحرک، دقیقاً `seconds` ثانیه (پیش‌فرض ۱۰).
    clear_after=True → بعد از اتمام، صاعقه از صفحه پاک می‌شه."""
    if not ansi_enabled or not sys.stdout.isatty():
        print(bolt_logo(ansi_enabled, truecolor))
        return
    height = _lightning_H // 2
    out = sys.stdout
    out.write("\033[?25l")                                        # مخفی کردن مکان‌نما
    try:
        start = time.perf_counter()
        first = True
        while True:
            el = time.perf_counter() - start
            done = el >= seconds
            g = 1.0 if done else _lightning_glow_at(el)
            sh = None if done else _lightning_shimmer_at(el)
            if not first:
                out.write(f"\033[{height}A")
            out.write(_lightning_frame(g, sh, truecolor) + "\n")
            out.flush()
            first = False
            if done:
                break
        if clear_after:
            out.write(f"\033[{height}A\033[J")
    finally:
        out.write("\033[?25h")
        out.flush()

def crypto_plus_text(ansi_enabled: bool) -> str:
    """Render CRYPTO PLUS as a separate blue-gradient bitmap wordmark."""
    font = {
        "C": [".####", "#....", "#....", "#....", ".####"],
        "R": ["####.", "#...#", "####.", "#..#.", "#...#"],
        "Y": ["#...#", ".#.#.", "..#..", "..#..", "..#.."],
        "P": ["####.", "#...#", "####.", "#....", "#...."],
        "T": ["#####", "..#..", "..#..", "..#..", "..#.."],
        "O": [".###.", "#...#", "#...#", "#...#", ".###."],
        "L": ["#....", "#....", "#....", "#....", "#####"],
        "U": ["#...#", "#...#", "#...#", "#...#", ".###."],
        "S": [".####", "#....", ".###.", "....#", "####."],
    }
    sx, gap = 2, 1
    dx, dy = 2, 1
    ramp = (159, 153, 117, 111, 81)
    edge_color, depth_color = 231, 24
    reset = RESET if ansi_enabled else ""

    def bitmap(word: str) -> tuple[set[tuple[int, int]], int]:
        points: set[tuple[int, int]] = set()
        cursor_x = 0
        for char in word:
            for y, row in enumerate(font[char]):
                for x, bit in enumerate(row):
                    if bit == "#":
                        for k in range(sx):
                            points.add((cursor_x + x * sx + k, y))
            cursor_x += (5 + gap) * sx
        return points, cursor_x - gap * sx

    def render_word(word: str, width: int = 72) -> list[str]:
        points, word_width = bitmap(word)
        pad = max(0, (width - word_width - dx) // 2)
        rows = []
        for y in range(5 + dy):
            line = []
            for x in range(word_width + dx):
                if (x, y) in points:
                    if ansi_enabled:
                        color = edge_color if (x, y - 1) not in points else ramp[min(y, len(ramp) - 1)]
                        line.append(f"\033[38;5;{color}m█")
                    else:
                        line.append("#")
                elif (x - dx, y - dy) in points:
                    line.append(f"\033[38;5;{depth_color}m▒" if ansi_enabled else ":")
                else:
                    line.append(" ")
            rows.append(" " * pad + "".join(line) + reset)
        return rows

    return "\n".join(render_word("CRYPTO") + [""] + render_word("PLUS"))


def print_animated_art(art: str, delay: float = 0.008) -> None:
    """Reveal ANSI-colored logo art gradually without animating escape codes."""
    ansi_token = re.compile(r"\033\[[0-?]*[ -/]*[@-~]")
    for line in art.splitlines():
        cursor = 0
        for match in ansi_token.finditer(line):
            for char in line[cursor:match.start()]:
                sys.stdout.write(char)
                if char not in (" ", "\t"):
                    sys.stdout.flush()
                    if sys.stdout.isatty():
                        time.sleep(delay)
            sys.stdout.write(match.group())
            cursor = match.end()
        for char in line[cursor:]:
            sys.stdout.write(char)
            if char not in (" ", "\t"):
                sys.stdout.flush()
                if sys.stdout.isatty():
                    time.sleep(delay)
        sys.stdout.write("\n")
        sys.stdout.flush()


def main() -> None:
    interactive = sys.stdout.isatty()
    ansi_enabled = enable_terminal_colors()
    green = GREEN if ansi_enabled else ""
    bold = BOLD if ansi_enabled else ""
    reset = RESET if ansi_enabled else ""
    hide_cursor = HIDE_CURSOR if interactive and ansi_enabled else ""
    show_cursor = SHOW_CURSOR if interactive and ansi_enabled else ""
    clear = CLEAR if interactive and ansi_enabled else ""


    if clear:
        sys.stdout.write(hide_cursor + clear)
    try:
        print()
        # Ten connected stages, with a soft blue gradient; total duration is 4.3 seconds.
        steps = 10
        cell = 4
        width = steps * cell
        total = width * 8
        partial = " ▏▎▍▌▋▊▉"
        top = [231, 195, 195, 159, 159, 153, 153, 117, 117, 111]
        body = [159, 153, 117, 117, 111, 81, 81, 75, 75, 74]
        bottom = [74, 68, 68, 67, 67, 61, 61, 24, 24, 24]
        track = [235, 237, 233]
        rows = [top, body, bottom]

        def render_progress(eighths: int) -> str:
            output = []
            for row_index, ramp in enumerate(rows):
                line = ["  "]
                for position in range(width):
                    amount = max(0, min(8, eighths - position * 8))
                    color = ramp[min(position // cell, len(ramp) - 1)]
                    if position % cell == cell - 1:
                        color = max(16, color - 1) if color > 16 else color
                    if amount == 8:
                        line.append(f"\033[38;5;{color}m█")
                    elif amount == 0:
                        line.append(f"\033[38;5;{track[row_index]}m█")
                    else:
                        line.append(
                            f"\033[38;5;{color}m\033[48;5;{track[row_index]}m{partial[amount]}{reset}"
                        )
                line.append(reset)
                output.append("".join(line))
            percent = eighths * 100 // total
            stage = min(steps, eighths // (cell * 8) + (1 if eighths % (cell * 8) else 0))
            output.append(f"  {green}{percent:3d}%{reset}   STAGE {stage}/{steps}")
            return "\n".join(output)

        if interactive and ansi_enabled:
            sys.stdout.write(hide_cursor)
            try:
                for amount in range(total + 1):
                    if amount:
                        sys.stdout.write("\033[4A")
                    sys.stdout.write(render_progress(amount) + "\n")
                    sys.stdout.flush()
                    if amount < total:
                        time.sleep(4.3 / total)
            finally:
                sys.stdout.write(show_cursor)
                sys.stdout.flush()
        else:
            print("  [########################################] 100%   STAGE 10/10")
            if interactive:
                time.sleep(4.3)

        print(f"{green}{bold}  READY{reset}")
        print()
        bolt_animation(seconds=4.0, ansi_enabled=ansi_enabled)
        print_animated_art(f"{green}{bold}       LIGHTNING{reset}", delay=0.045)
        print()
        print_animated_art(crypto_plus_text(ansi_enabled), delay=0.004)
        print()
        if interactive:
            time.sleep(3)
    finally:
        if show_cursor:
            sys.stdout.write(show_cursor + reset)
            sys.stdout.flush()


if __name__ == "__main__":
    main()
