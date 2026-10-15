"""Compact CryptoPulse terminal intro with Windows-safe colors and progress bars."""

from __future__ import annotations

import ctypes
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


def razer_logo_3d(ansi_enabled: bool = True) -> str:
    """Render a three-arm, acid-green 3D emblem."""
    W, H = 46, 24
    cx, cy = (W - 1) / 2, (H - 1) / 2
    R = 7.6
    SWEEP = 2.3
    N = 90
    ramp = (157, 120, 118, 82, 76, 70, 34, 28)
    depth_color, eye_color = 22, 226
    L = (-0.6, -0.8)

    arms = []
    for k in range(3):
        a0 = k * 2 * math.pi / 3 - math.pi / 2
        pts = []
        for i in range(N + 1):
            t = i / N
            r = R * (0.10 + 0.90 * t)
            a = a0 + SWEEP * t
            width = 0.8 + 2.3 * t ** 2.4
            pts.append((r * math.cos(a), r * math.sin(a), width, t))
        arms.append(pts)

    def sample(px, py):
        best = None
        for pts in arms:
            for qx, qy, w, t in pts:
                dx, dy = px - qx, py - qy
                d = math.hypot(dx, dy)
                if d <= w and (best is None or d / w < best[0]):
                    nx, ny = dx / w, dy / w
                    light = 0.55 + 0.45 * (nx * L[0] + ny * L[1]) - 0.25 * (d / w) ** 2
                    best = (d / w, max(0.0, min(1.0, light)), t)
        return best

    def pixel(x, y):
        return ((x - cx) / 2.0, y - cy)

    eyes = set()
    for pts in arms:
        qx, qy, _, _ = pts[int(N * 0.9)]
        eyes.add((round(qx * 2 + cx), round(qy + cy)))

    rows = []
    reset = RESET if ansi_enabled else ""
    for y in range(H):
        line = []
        for x in range(W):
            hit = sample(*pixel(x, y))
            if hit is not None:
                if (x, y) in eyes and ansi_enabled:
                    line.append(f"\\033[38;5;{eye_color}m●")
                elif ansi_enabled:
                    c = ramp[min(int((1 - hit[1]) * len(ramp)), len(ramp) - 1)]
                    line.append(f"\\033[38;5;{c}m█")
                else:
                    line.append("#")
            elif sample(*pixel(x - 2, y - 1)) is not None:
                line.append(f"\\033[38;5;{depth_color}m▒" if ansi_enabled else ":")
            else:
                line.append(" ")
        rows.append("".join(line) + reset)
    return "\\n".join(rows)


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
        # Ten connected stages, with a soft blue gradient; each stage takes 1.5 seconds.
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
                        time.sleep((steps * 1.5) / total)
            finally:
                sys.stdout.write(show_cursor)
                sys.stdout.flush()
        else:
            print("  [########################################] 100%   STAGE 10/10")
            if interactive:
                time.sleep(steps * 1.5)

        print(f"{green}{bold}  READY{reset}")
        print()
        print_animated_art(razer_logo_3d(ansi_enabled), delay=0.004)
        print_animated_art(f"{green}{bold}             RAZER{reset}", delay=0.045)
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
