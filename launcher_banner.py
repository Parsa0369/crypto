"""Animated CryptoPulse terminal splash using the 'art' ASCII-font library."""

from __future__ import annotations

import random
import sys
import time

try:
    from art import text2art
except ImportError:
    text2art = None

GREEN = "\033[92m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
DIM = "\033[2m"
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

FONTS = ("slant", "standard", "small", "doom")
COLORS = (GREEN, CYAN, BLUE, MAGENTA)


def make_logo(font: str) -> str:
    if text2art is None:
        return r"""
   ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗
  ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗
  ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║
  ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║
  ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝
   ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝
"""
    try:
        return text2art("CRYPTOPULSE", font=font, chr_ignore=True).rstrip()
    except Exception:
        return text2art("CRYPTOPULSE", font="standard", chr_ignore=True).rstrip()


def main() -> None:
    interactive = sys.stdout.isatty()
    frames = 6 if interactive else 1
    if interactive:
        sys.stdout.write(HIDE_CURSOR)

    try:
        for frame in range(frames):
            color = COLORS[frame % len(COLORS)]
            font = FONTS[frame % len(FONTS)]
            logo = make_logo(font)
            noise = "".join(random.choice("01ABCDEF") for _ in range(34))
            signature = f"0x{random.randrange(0x10000):04X}"
            sys.stdout.write(CLEAR if interactive else "")
            print(f"{color}╔{'═' * 66}╗{RESET}")
            print(f"{color}║{' C R Y P T O P U L S E  //  M A R K E T  L A B ':^66}║{RESET}")
            print(f"{color}╚{'═' * 66}╝{RESET}")
            print()
            print(f"{color}{logo}{RESET}")
            print()
            print(f"{DIM}{color}  [BOOT {signature}]  [NETWORK READY]  [MODE: LOCAL]{RESET}")
            print(f"{color}  {noise}{RESET}")
            print()
            print(f"{color}  ▰ ▰ ▰  INITIALIZING MARKET SYSTEM  ▰ ▰ ▰{RESET}")
            sys.stdout.flush()
            if interactive and frame < frames - 1:
                time.sleep(0.23)
    finally:
        if interactive:
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.flush()


if __name__ == "__main__":
    main()
