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

SIZE = 56
SS = 2
SHADOW = (30, 12, 40)
SHADOW_OFFSET = 0.07

PINK = (255, 105, 180)
HOT = (255, 160, 215)
DEEP = (70, 20, 110)
LILAC = (205, 95, 215)
WHITE = (255, 255, 255)

_L = (-0.45, -0.55, 0.70)
_LN = math.sqrt(sum(v * v for v in _L))
LIGHT = tuple(v / _LN for v in _L)

ECG = ((-0.62, 0.14), (-0.30, 0.14), (-0.18, -0.10), (-0.06, 0.36),
       (0.06, -0.28), (0.17, 0.14), (0.62, 0.14))


def _scale(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _heart_f(x, y):
    return (x * x + y * y - 1) ** 3 - x * x * y ** 3


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _bow(nx, ny):
    cx, cy = -0.50, -0.60
    for sgn in (-1, 1):
        ex, ey = nx - (cx + sgn * 0.22), ny - (cy - 0.04 * sgn)
        a = math.radians(-28 * sgn)
        u, v = ex * math.cos(a) - ey * math.sin(a), ex * math.sin(a) + ey * math.cos(a)
        d = (u / 0.23) ** 2 + (v / 0.135) ** 2
        if d < 1:
            lit = max(0.0, -(ex * LIGHT[0] + ey * LIGHT[1]) / 0.18)
            col = _mix(PINK, HOT, 0.6 * lit)
            if d < 0.30:
                col = _scale(col, 0.78)
            if d > 0.80:
                col = _mix(col, WHITE, 0.35)
            return col
    k = math.hypot(nx - cx, ny - cy)
    if k < 0.09:
        lit = max(0.0, -((nx - cx) * LIGHT[0] + (ny - cy) * LIGHT[1]) / 0.09)
        return _mix(_scale(PINK, 0.85), WHITE, 0.45 * lit)
    return None


def _heart_color(nx, ny, s):
    nx, ny = nx / s, ny / s
    x, y = nx * 1.25, -ny * 1.25 + 0.10
    f = _heart_f(x, y)

    bow = _bow(nx, ny)
    if f > 0:
        return bow

    e = 0.01
    gx = _heart_f(x + e, y) - _heart_f(x - e, y)
    gy = _heart_f(x, y + e) - _heart_f(x, y - e)
    dist = -f * 2 * e / (math.hypot(gx, gy) or 1.0)

    rr = (nx * nx + (ny - 0.02) ** 2) / 0.95
    z = math.sqrt(max(0.0, 1 - rr))
    dot = max(0.0, nx * LIGHT[0] * 0.8 + ny * LIGHT[1] * 0.8 + z * LIGHT[2] * 1.15)
    body = _mix(DEEP, LILAC, min(1.0, dot) ** 1.3)

    if dist < 0.045:
        body = _mix(PINK, body, dist / 0.045 * 0.55)
    g = math.hypot(nx + 0.40, ny + 0.20)
    if g < 0.10:
        body = _mix(body, WHITE, 0.6 * (1 - g / 0.10))

    ex, ey = nx, ny
    best = min(_seg_dist(ex, ey, ECG[i][0], ECG[i][1], ECG[i + 1][0], ECG[i + 1][1])
               for i in range(len(ECG) - 1))
    if best < 0.04:
        body = _mix(body, WHITE, 0.95 if best < 0.026 else 0.5)
        body = _mix(body, HOT, 0.25)
    return bow if bow is not None else body


def _pixel(px, py, s):
    half = SIZE / 2
    cx = cy = half - 1.0
    scale = half * 0.92
    acc, n, sh = [0, 0, 0], 0, 0
    for i in range(SS):
        for j in range(SS):
            nx = (px + (i + 0.5) / SS - cx) / scale
            ny = (py + (j + 0.5) / SS - cy) / scale
            c = _heart_color(nx, ny, s)
            if c is not None:
                n += 1
                acc = [acc[k] + c[k] for k in range(3)]
            elif SHADOW and _heart_color(nx - SHADOW_OFFSET, ny - SHADOW_OFFSET, s) is not None:
                sh += 1
    total = SS * SS
    if n * 2 >= total:
        return (acc[0] // n, acc[1] // n, acc[2] // n)
    if sh * 2 >= total:
        return SHADOW
    return None


def _code(rgb, truecolor):
    if truecolor:
        return f"2;{rgb[0]};{rgb[1]};{rgb[2]}"
    return f"5;{16 + 36 * round(rgb[0] / 51) + 6 * round(rgb[1] / 51) + round(rgb[2] / 51)}"


def _frame(s, truecolor=True):
    px = [[_pixel(x, y, s) for x in range(SIZE)] for y in range(SIZE)]
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


def pulse_heart_3d(ansi_enabled: bool = True, truecolor: bool = True, beat: float = 1.0) -> str:
    if not ansi_enabled:
        return _plain()
    return _frame(beat, truecolor)


def _beat(t):
    t %= 1.0
    return math.exp(-((t - 0.10) / 0.055) ** 2) + 0.7 * math.exp(-((t - 0.32) / 0.07) ** 2)


def beat_pulse_heart(seconds: float = 4.0, strength: float = 0.09, truecolor: bool = True,
                     ansi_enabled: bool = True) -> None:
    if not ansi_enabled or not sys.stdout.isatty():
        print(pulse_heart_3d(ansi_enabled, truecolor))
        return
    height = SIZE // 2
    out = sys.stdout
    out.write("\033[?25l")
    try:
        start = time.perf_counter()
        first = True
        while True:
            el = time.perf_counter() - start
            done = el >= seconds
            s = 1.0 if done else 1.0 + strength * _beat(el)
            if not first:
                out.write(f"\033[{height}A")
            out.write(_frame(s, truecolor) + "\n")
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
            c = _heart_color(((x + 0.5) / W * 2 - 1) / 0.92, ((y + 0.5) / H * 2 - 1) / 0.92, 1.0)
            row.append(" " if c is None else ("*" if c[0] > 200 and c[2] > 140 else "#"))
        out.append("".join(row))
    return "\n".join(out)

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
        beat_pulse_heart(seconds=4.0, strength=0.09, ansi_enabled=ansi_enabled)
        print_animated_art(f"{green}{bold}          HEARTBEAT{reset}", delay=0.045)
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
