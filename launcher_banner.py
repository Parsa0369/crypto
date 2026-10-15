"""Compact CryptoPulse terminal intro with Windows-safe colors and progress bars."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import time

try:
    from art import text2art
except ImportError:
    text2art = None

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


def make_logo() -> list[str]:
    if text2art is not None:
        for font in ("small", "standard", "slant"):
            try:
                result = text2art("CRYPTOPULSE", font=font, chr_ignore=True).rstrip()
                if result:
                    return result.splitlines()
            except Exception:
                pass
    return [
        "  CCCCC  RRRRR  Y   Y  PPPPP  TTTTT  OOOOO  PPPPP  U   U  L      SSSSS  EEEEE",
        " C       R   R   Y Y   P   P    T    O   O  P   P  U   U  L      S      E",
        " C       RRRRR    Y    PPPPP    T    O   O  PPPPP  U   U  L      SSSS   EEEE",
        " C       R  R     Y    P        T    O   O  P      U   U  L      S         E",
        "  CCCCC  R   R    Y    P        TTTTT OOOOO P       UUU   LLLLL  SSSSS EEEEE",
    ]


def _pane(x: int, y: int) -> float | None:
    """Return a 0..1 lighting value when a point lies on the front of the Windows mark."""
    if not (2 <= x <= 21 or 24 <= x <= 43):
        return None
    scale = 1 - 0.22 * (x - 2) / 41
    adjusted_y = 11.5 + (y - 11.5) / scale
    if not (1 <= adjusted_y < 11 or 12 <= adjusted_y <= 22.5):
        return None
    return ((x - 2) / 41) * 0.5 + ((adjusted_y - 1) / 21.5) * 0.5


def windows_logo_3d(ansi_enabled: bool) -> str:
    """Render a perspective Windows logo with a blue light gradient and dark depth."""
    ramp = (195, 159, 153, 117, 111, 81, 75, 74)
    depth_color = 24
    reset = RESET if ansi_enabled else ""
    rows = []
    for y in range(27):
        line = []
        for x in range(50):
            light = _pane(x, y)
            if light is not None:
                if ansi_enabled:
                    color = ramp[min(int(light * len(ramp)), len(ramp) - 1)]
                    line.append(f"\033[38;5;{color}m█")
                else:
                    line.append("#")
            elif _pane(x - 2, y - 1) is not None:
                if ansi_enabled:
                    line.append(f"\033[38;5;{depth_color}m▒")
                else:
                    line.append(":")
            else:
                line.append(" ")
        rows.append("".join(line) + reset)
    return "\n".join(rows)


def main() -> None:
    interactive = sys.stdout.isatty()
    ansi_enabled = enable_terminal_colors()
    green = GREEN if ansi_enabled else ""
    bold = BOLD if ansi_enabled else ""
    reset = RESET if ansi_enabled else ""
    hide_cursor = HIDE_CURSOR if interactive and ansi_enabled else ""
    show_cursor = SHOW_CURSOR if interactive and ansi_enabled else ""
    clear = CLEAR if interactive and ansi_enabled else ""

    width = min(max(shutil.get_terminal_size((88, 24)).columns - 4, 48), 88)
    logo_lines = make_logo()

    if clear:
        sys.stdout.write(hide_cursor + clear)
    try:
        print(f"{green}{bold}+{'-' * width}+{reset}")
        print(f"{green}{bold}|{' CRYPTOPULSE // TERMINAL ':^{width}}|{reset}")
        print(f"{green}{bold}+{'-' * width}+{reset}")
        print()

        for char in "CRYPTOPULSE":
            sys.stdout.write(f"{green}{bold}{char}{reset}")
            sys.stdout.flush()
            if interactive:
                time.sleep(0.055)
        print()

        if interactive:
            time.sleep(0.2)

        for line in logo_lines:
            print(f"{green}{bold}  {line}{reset}")
            sys.stdout.flush()
            if interactive:
                time.sleep(0.08)

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
                        line.append(f"\\033[38;5;{color}m█")
                    elif amount == 0:
                        line.append(f"\\033[38;5;{track[row_index]}m█")
                    else:
                        line.append(
                            f"\\033[38;5;{color}m\\033[48;5;{track[row_index]}m{partial[amount]}{reset}"
                        )
                line.append(reset)
                output.append("".join(line))
            percent = eighths * 100 // total
            stage = min(steps, eighths // (cell * 8) + (1 if eighths % (cell * 8) else 0))
            output.append(f"  {green}{percent:3d}%{reset}   STAGE {stage}/{steps}")
            return "\\n".join(output)

        if interactive and ansi_enabled:
            sys.stdout.write(hide_cursor)
            try:
                for amount in range(total + 1):
                    if amount:
                        sys.stdout.write("\\033[4A")
                    sys.stdout.write(render_progress(amount) + "\\n")
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
        print(windows_logo_3d(ansi_enabled))
        print(f"{green}{bold}          MICROSOFT WINDOWS{reset}")
        print()
    finally:
        if show_cursor:
            sys.stdout.write(show_cursor + reset)
            sys.stdout.flush()


if __name__ == "__main__":
    main()
