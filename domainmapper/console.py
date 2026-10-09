import sys
from collections.abc import Sequence
from functools import partial

from colorama import Fore, Style, just_fix_windows_console

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
just_fix_windows_console()


def _paint(style: str, text: object) -> str:
    return f"{style}{text}{Style.RESET_ALL}"


yellow = partial(_paint, Fore.YELLOW)
green = partial(_paint, Fore.GREEN)
cyan = partial(_paint, Fore.CYAN)
red = partial(_paint, Fore.RED)
bright = partial(_paint, Style.BRIGHT)


def ask(prompt: str) -> str:
    return input(prompt).strip()


def ask_until_filled(value: str, prompt: str) -> str:
    while not value:
        value = ask(prompt)
    return value


def choose_one(title: str, labels: Sequence[str], fallback: str) -> int | None:
    options = "".join(f"\n{number}. {label}" for number, label in enumerate(labels, 1))
    answer = ask(f"\n{yellow(title)}{options}\n{green('Enter')} - {fallback}\nВаш выбор: ")
    return int(answer) - 1 if answer.isdigit() and 1 <= int(answer) <= len(labels) else None


def choose_many(title: str, labels: Sequence[str], subject: str) -> list[int]:
    print(f"\n{yellow(title)}\n0. Выбрать все")
    for number, label in enumerate(labels, 1):
        print(f"{number}. {label}")
    while True:
        tokens = ask(f"\nУкажите {green('номера')} {subject} через пробел и нажмите {green('Enter')}: ").split()
        if "0" in tokens:
            return list(range(len(labels)))
        chosen = list(dict.fromkeys(int(token) - 1 for token in tokens if token.isdigit() and 1 <= int(token) <= len(labels)))
        if chosen:
            return chosen
