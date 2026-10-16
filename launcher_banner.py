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
MARGIN = 0.93
SHADOW_OFFSET = 0.07
SHADOW_COLOR = (38, 38, 38)

RED, GREEN, YELLOW, BLUE = (234, 67, 53), (52, 168, 83), (251, 188, 5), (66, 133, 244)
WHITE = (255, 255, 255)
SECTORS = ((30, 150, RED), (150, 270, GREEN), (270, 390, YELLOW))

BLUE_R, RING_R = 0.325, 0.415
_L = (-0.45, -0.55, 0.70)
_LN = math.sqrt(sum(v * v for v in _L))
LIGHT = tuple(v / _LN for v in _L)


def _scale(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _analyze(nx, ny):
    r = math.hypot(nx, ny)
    if r > 1:
        return None
    z = math.sqrt(max(0.0, 1 - r * r))
    dome = max(0.0, nx * LIGHT[0] + ny * LIGHT[1] + z * LIGHT[2])

    if r < BLUE_R:
        k = r / BLUE_R
        zz = math.sqrt(max(0.0, 1 - k * k))
        d = max(0.0, (nx / BLUE_R) * LIGHT[0] + (ny / BLUE_R) * LIGHT[1] + zz * LIGHT[2])
        col = _scale(BLUE, 0.72 + 0.40 * d)
        g = math.hypot(nx + 0.10, ny + 0.12)
        if g < 0.085:
            col = _mix(col, WHITE, 0.55 * (1 - g / 0.085))
        if k > 0.9:
            col = _scale(col, 1 - 0.25 * (k - 0.9) / 0.1)
        return ("c", col)

    if r < RING_R:
        t = (r - BLUE_R) / (RING_R - BLUE_R)
        col = _scale(WHITE, 0.90 + 0.10 * dome)
        if t < 0.15:
            col = _scale(col, 0.82 + 0.18 * t / 0.15)
        return ("c", col)

    ang = math.degrees(math.atan2(-ny, nx)) % 360
    f = (0.88 + 0.14 * r) * (0.80 + 0.30 * dome)
    rim = 0.0
    if r > 0.93:
        lit = max(0.0, -(nx * LIGHT[0] + ny * LIGHT[1]) / max(r, 1e-6))
        rim = 0.30 * lit * (r - 0.93) / 0.07
    edge = 0.85 if r > 0.985 else 1.0
    return ("s", ang, r, f, rim, edge)


def _seg_color(s, rot):
    _, ang, r, f, rim, edge = s
    a = (ang - rot) % 360
    base, delta = RED, 0.0
    for a0, a1, c in SECTORS:
        dlt = (a - a0) % 360
        if dlt < a1 - a0:
            base, delta = c, dlt
            break
    col = _scale(base, f)
    if delta < 90:
        dist = r * math.sin(math.radians(delta))
        if dist < 0.075:
            col = _scale(col, 1 - 0.32 * (1 - dist / 0.075))
    if rim:
        col = _mix(col, WHITE, rim)
    if edge != 1.0:
        col = _scale(col, edge)
    return col


def _build():
    half = SIZE / 2
    cx = cy = half - 1.2
    scale = half * MARGIN
    total = SS * SS
    grid = []
    for py in range(SIZE):
        row = []
        for px in range(SIZE):
            fixed, nfix, segs, sh = [0, 0, 0], 0, [], 0
            for i in range(SS):
                for j in range(SS):
                    nx = (px + (i + 0.5) / SS - cx) / scale
                    ny = (py + (j + 0.5) / SS - cy) / scale
                    a = _analyze(nx, ny)
                    if a is None:
                        if _analyze(nx - SHADOW_OFFSET, ny - SHADOW_OFFSET) is not None:
                            sh += 1
                    elif a[0] == "c":
                        nfix += 1
                        fixed = [fixed[k] + a[1][k] for k in range(3)]
                    else:
                        segs.append(a)
            row.append((fixed, nfix, segs, sh, total))
        grid.append(row)
    return grid


def _resolve(entry, rot):
    fixed, nfix, segs, sh, total = entry
    n, acc = nfix, list(fixed)
    for s in segs:
        c = _seg_color(s, rot)
        acc[0] += c[0]
        acc[1] += c[1]
        acc[2] += c[2]
        n += 1
    if n * 2 >= total:
        return (acc[0] // n, acc[1] // n, acc[2] // n)
    if sh * 2 >= total and SHADOW_COLOR:
        return SHADOW_COLOR
    return None


def _code(rgb, truecolor):
    if truecolor:
        return f"2;{rgb[0]};{rgb[1]};{rgb[2]}"
    idx = 16 + 36 * round(rgb[0] / 51) + 6 * round(rgb[1] / 51) + round(rgb[2] / 51)
    return f"5;{idx}"


def _frame(grid, rot, truecolor=True):
    px = [[_resolve(e, rot) for e in row] for row in grid]
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


_GRID = None


def _grid():
    global _GRID
    if _GRID is None:
        _GRID = _build()
    return _GRID


def chrome_logo_3d(ansi_enabled: bool = True, truecolor: bool = True, rotation: float = 0.0) -> str:
    if not ansi_enabled:
        return _plain()
    return _frame(_grid(), rotation, truecolor)


def _ease_in_out(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def spin_chrome_logo(seconds: float = 3.2, turns: float = 2.0, truecolor: bool = True,
                     ansi_enabled: bool = True) -> None:
    if not ansi_enabled or not sys.stdout.isatty():
        print(chrome_logo_3d(ansi_enabled, truecolor))
        return
    grid = _grid()
    height = SIZE // 2
    out = sys.stdout
    out.write("\033[?25l")
    try:
        start = time.perf_counter()
        first = True
        while True:
            t = min(1.0, (time.perf_counter() - start) / seconds)
            rot = 360.0 * turns * _ease_in_out(t)
            if not first:
                out.write(f"\033[{height}A")
            out.write(_frame(grid, rot, truecolor) + "\n")
            out.flush()
            first = False
            if t >= 1.0:
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
            a = _analyze(((x + 0.5) / W * 2 - 1) / MARGIN, ((y + 0.5) / H * 2 - 1) / MARGIN)
            if a is None:
                row.append(" ")
                continue
            c = a[1] if a[0] == "c" else _seg_color(a, 0.0)
            if min(c) > 200:
                row.append(".")
            else:
                h = colorsys.rgb_to_hsv(*(v / 255 for v in c))[0] * 360
                row.append("@" if 180 <= h < 270 else "G" if 70 <= h < 180 else "Y" if 25 <= h < 70 else "R")
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
        spin_chrome_logo(seconds=3.2, turns=2.0, ansi_enabled=ansi_enabled)
        print_animated_art(f"{green}{bold}             CHROME{reset}", delay=0.045)
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
