"""Minimal animated CryptoPulse intro with a slower logo reveal and neon accents."""

from __future__ import annotations

import random
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
DIM = f"{ESC}2m"
CYAN = f"{ESC}96m"
GREEN = f"{ESC}92m"
BLUE = f"{ESC}94m"
MAGENTA = f"{ESC}95m"
WHITE = f"{ESC}97m"
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
CLEAR = f"{ESC}2J{ESC}H"
COLORS = (CYAN, GREEN, BLUE, MAGENTA)


def make_logo() -> str:
    if text2art is not None:
        for font in ("slant", "doom", "standard"):
            try:
                result = text2art("CRYPTOPULSE", font=font, chr_ignore=True).rstrip()
                if result:
                    return result
            except Exception:
                pass
    return "  C R Y P T O P U L S E\n  ===================="


def main() -> None:
    interactive = sys.stdout.isatty()
    width = min(max(shutil.get_terminal_size((88, 24)).columns - 4, 48), 88)
    color = random.choice(COLORS)
    logo_lines = make_logo().splitlines()

    if interactive:
        sys.stdout.write(HIDE_CURSOR + CLEAR)
    try:
        print(f"{color}{BOLD}╔{'═' * width}╗{RESET}")
        print(f"{color}{BOLD}║{' CRYPTOPULSE // TERMINAL ':^{width}}║{RESET}")
        print(f"{color}{BOLD}╚{'═' * width}╝{RESET}")
        print()

        # Keep the intro quiet: only the brand, logo, and a progress bar.
        for char in "CRYPTOPULSE":
            sys.stdout.write(f"{CYAN}{BOLD}{char}{RESET}")
            sys.stdout.flush()
            if interactive:
                time.sleep(0.075)
        print()
        if interactive:
            time.sleep(0.25)

        for line in logo_lines:
            print(f"{color}{BOLD}  {line}{RESET}")
            sys.stdout.flush()
            if interactive:
                time.sleep(0.12)

        print()
        bar_width = min(28, max(12, width // 3))
        if interactive:
            for progress in range(bar_width + 1):
                bar = "█" * progress + "░" * (bar_width - progress)
                percent = int(progress * 100 / bar_width)
                sys.stdout.write(f"\r  {color}{bar}{RESET}  {WHITE}{percent:3d}%{RESET}")
                sys.stdout.flush()
                time.sleep(0.045)
            print()
            time.sleep(0.35)
        else:
            print(f"{color}{'█' * bar_width}{RESET}  {WHITE}100%{RESET}")
        print(f"{DIM}{GREEN}  READY{RESET}")
        print()
    finally:
        if interactive:
            sys.stdout.write(SHOW_CURSOR + RESET)
            sys.stdout.flush()


if __name__ == "__main__":
    main()
