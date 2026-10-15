"""CryptoPulse terminal intro: typed logo, neon color cycling, and subtle glitch effects."""

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
RED = f"{ESC}91m"
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
CLEAR = f"{ESC}2J{ESC}H"
HOME = f"{ESC}H"
COLORS = (CYAN, GREEN, BLUE, MAGENTA)
GLITCH_CHARS = "01ABCDEF#$%&*+="


def make_logo() -> str:
    if text2art is not None:
        for font in ("slant", "doom", "standard"):
            try:
                logo = text2art("CRYPTOPULSE", font=font, chr_ignore=True).rstrip()
                if logo:
                    return logo
            except Exception:
                continue
    return (
        "  C R Y P T O P U L S E\n"
        "  ===================="
    )


def type_text(text: str, delay: float = 0.018) -> None:
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)


def glitch_line(width: int) -> str:
    return "".join(random.choice(GLITCH_CHARS) for _ in range(max(8, width)))


def main() -> None:
    interactive = sys.stdout.isatty()
    width = min(max(shutil.get_terminal_size((88, 24)).columns - 4, 48), 88)
    color = random.choice(COLORS)
    logo = make_logo()
    logo_lines = logo.splitlines()

    if interactive:
        sys.stdout.write(HIDE_CURSOR + CLEAR)
    try:
        print(f"{color}{BOLD}╔{'═' * width}╗{RESET}")
        title = " CRYPTOPULSE  //  TERMINAL INTERFACE "
        print(f"{color}{BOLD}║{title:^{width}}║{RESET}")
        print(f"{color}{BOLD}╚{'═' * width}╝{RESET}")
        print()

        # Type the brand one character at a time for a boot-sequence feel.
        type_text(f"{CYAN}{BOLD}  {'CRYPTOPULSE'}{RESET}", 0.045 if interactive else 0)
        print()
        print(f"{DIM}{WHITE}  MARKET INTELLIGENCE  /  LOCAL CONSOLE{RESET}")
        print()

        # A brief controlled glitch flicker, then settle on the real ASCII art.
        if interactive:
            for _ in range(2):
                print(f"{random.choice((GREEN, MAGENTA, BLUE))}  {glitch_line(min(width, 42))}{RESET}")
                time.sleep(0.07)
            print(f"{ESC}2K", end="")
            print(f"{ESC}1A{ESC}2K", end="")
        for line in logo_lines:
            print(f"{color}{BOLD}  {line}{RESET}")

        print()
        status = ("BOOT", "NETWORK", "ENGINE", "MARKET")
        for label in status:
            print(f"{GREEN}  [ OK ]{RESET} {WHITE}{label:<8}{RESET} {DIM}initialized{RESET}")
            if interactive:
                time.sleep(0.055)

        print()
        bar_width = min(28, max(12, width // 3))
        if interactive:
            for progress in range(bar_width + 1):
                bar = "█" * progress + "░" * (bar_width - progress)
                percent = int(progress * 100 / bar_width)
                sys.stdout.write(f"\r  {color}{bar}{RESET}  {WHITE}{percent:3d}%{RESET}")
                sys.stdout.flush()
                time.sleep(0.018)
            print()
        else:
            print(f"{color}  {'█' * bar_width}{RESET}  {WHITE}100%{RESET}")

        print()
        print(f"{DIM}{color}  SESSION: {random.randrange(0x10000):04X}  |  MODE: LOCAL  |  STATUS: READY{RESET}")
        print()
    finally:
        if interactive:
            sys.stdout.write(SHOW_CURSOR + RESET)
            sys.stdout.flush()


if __name__ == "__main__":
    main()
