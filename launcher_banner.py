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
        kernel32 = ctypes.windll.kernel32
        stdout_handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if not kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode)):
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
        bar_width = 28
        steps = 33  # 33 x 100 ms = 3.3 seconds for each bar.
        for index in range(1, 11):
            if interactive:
                for step in range(steps + 1):
                    filled = round(bar_width * step / steps)
                    bar = "#" * filled + "." * (bar_width - filled)
                    percent = round(100 * step / steps)
                    row = f"\r  [{green}{bar}{reset}] {green}{percent:3d}%  MODULE {index:02d}/10{reset}"
                    sys.stdout.write(row)
                    sys.stdout.flush()
                    if step < steps:
                        time.sleep(0.1)
                print()
            else:
                bar = "#" * bar_width
                print(f"  [{bar}] 100%  MODULE {index:02d}/10")

        print(f"{green}{bold}  READY{reset}")
        print()
    finally:
        if show_cursor:
            sys.stdout.write(show_cursor + reset)
            sys.stdout.flush()


if __name__ == "__main__":
    main()
