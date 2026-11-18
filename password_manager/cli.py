"""Interactive command-line menu."""

import argparse
import msvcrt
import os
from pathlib import Path
import sys
import time

from .generator import generate_password
from .paths import default_vault_path
from .permissions import restrict_access
from .security import validate_new_master_password
from .vault import Vault, VaultAuthenticationError, VaultError

IDLE_SECONDS = 300


class IdleTimeout(Exception):
    """No key was pressed for the configured idle period."""


def _console_input(prompt: str, *, hidden: bool) -> str:
    """Read from a Windows console without echoing secrets and with an idle timeout."""
    print(prompt, end="", flush=True)
    chars = []
    deadline = time.monotonic() + IDLE_SECONDS
    while True:
        if time.monotonic() >= deadline:
            raise IdleTimeout
        if not msvcrt.kbhit():
            time.sleep(0.05)
            continue
        char = msvcrt.getwch()
        deadline = time.monotonic() + IDLE_SECONDS
        if char in ("\x00", "\xe0"):
            msvcrt.getwch()  # consume the scan code for a special key
        elif char in ("\r", "\n"):
            print()
            return "".join(chars)
        elif char == "\b":
            if chars:
                chars.pop()
                if not hidden:
                    print("\b \b", end="", flush=True)
        elif char.isprintable() and len(chars) < 4096:
            chars.append(char)
            if not hidden:
                print(char, end="", flush=True)


def _input(prompt: str) -> str:
    if sys.stdin.isatty():
        return _console_input(prompt, hidden=False)
    return input(prompt)


def _secret(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise VaultError("Hidden password input is unavailable. Use a real terminal.")
    return _console_input(prompt, hidden=True)


def _clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.system("cls") != 0:
        print("\n" * 40)


def _countdown(message: str) -> bool:
    """Return True when the three-second delay ends; Escape cancels it."""
    print(f"{message} Press Esc within 3 seconds to cancel.")
    for remaining in (3, 2, 1):
        print(f"Closing in {remaining}...")
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            if msvcrt.kbhit() and msvcrt.getwch() == "\x1b":
                print("Canceled.")
                return False
            time.sleep(0.05)
    return True


def _select_entry(vault: Vault) -> int | None:
    if not vault.entries:
        print("Vault is empty.")
        return None
    for number, entry in enumerate(vault.entries, 1):
        print(f"{number}. {entry['name']} ({entry['username']})")
    try:
        number = int(_input("Entry number: "))
    except ValueError:
        print("Enter a valid number.")
        return None
    if not 1 <= number <= len(vault.entries):
        print("Entry number is out of range.")
        return None
    return number - 1


def _generate() -> str | None:
    try:
        choices = []
        for label in (
            "Include lowercase letters (a-z)",
            "Include uppercase letters (A-Z)",
            "Include digits (0-9)",
            "Include symbols (!, @, #, etc.)",
        ):
            answer = _input(f"{label}? [Y/n, Enter = yes]: ").strip().lower()
            if answer not in ("", "y", "yes", "n", "no"):
                raise ValueError("Answer y or n for each character group.")
            choices.append(answer not in ("n", "no"))
        if not any(choices):
            raise ValueError("Select at least one character group.")
    except ValueError as exc:
        print(exc)
        return None
    while True:
        answer = _input("Password length in characters (4-20, Enter = 20): ").strip()
        try:
            length = int(answer) if answer else 20
        except ValueError:
            print("Enter a whole number from 4 to 20, or press Enter for 20.")
            continue
        try:
            return generate_password(length, lowercase=choices[0], uppercase=choices[1],
                                     digits=choices[2], symbols=choices[3])
        except ValueError as exc:
            print(exc)


def _menu(vault: Vault) -> None:
    while True:
        print("\n1. List entries  2. View entry  3. Add entry  4. Delete entry")
        print("5. Generate password  6. Lock and exit  7. Reset vault  8. Change master password")
        choice = _input("Choose a menu number: ").strip()
        if choice == "1":
            if vault.entries:
                for number, entry in enumerate(vault.entries, 1):
                    print(f"{number}. {entry['name']} ({entry['username']})")
            else:
                print("Vault is empty.")
        elif choice == "2":
            index = _select_entry(vault)
            if index is not None:
                entry = vault.entries[index]
                print(f"Name of user: {entry['name']}\nUsername or email: {entry['username']}\nPassword: {entry['password']}")
        elif choice == "3":
            name = _input("Name of user (not the login username): ").strip()
            username = _input("Username or email for this entry: ")
            password = _secret("Password for this entry (Enter to generate): ")
            if not password:
                password = _generate()
                if password is None:
                    continue
                print(f"Generated password: {password}")
            try:
                vault.add(name, username, password)
                print("Entry saved.")
            except ValueError as exc:
                print(exc)
            except (VaultError, OSError) as exc:
                print(f"Could not save vault: {exc}")
        elif choice == "4":
            index = _select_entry(vault)
            if index is not None and _input("Type DELETE to confirm: ") == "DELETE":
                try:
                    vault.delete(index)
                    print("Entry deleted.")
                except (VaultError, OSError) as exc:
                    print(f"Could not save vault: {exc}")
        elif choice == "5":
            password = _generate()
            if password is not None:
                print(f"Generated password: {password}")
        elif choice == "6":
            if _countdown("Vault will lock and close."):
                _clear_screen()
                print("Goodbye!")
                return
        elif choice == "7":
            print("Reset deletes this vault file, including every saved entry and its master password.")
            if _input("Type RESET to continue, or press Enter to cancel: ") != "RESET":
                print("Reset canceled.")
                continue
            password = _secret("Enter your current master password to authorize reset: ")
            try:
                Vault.open(vault.path, password)
            except VaultAuthenticationError:
                print("Master password incorrect, or vault data is damaged. Reset canceled.")
                continue
            except VaultError as exc:
                print(f"Reset canceled: {exc}")
                continue
            if _countdown("Vault will be reset and close."):
                try:
                    vault.reset(password)
                except (VaultError, OSError) as exc:
                    print(f"Could not reset vault: {exc}")
                    continue
                _clear_screen()
                print("Vault reset. The next launch will ask for a new master password. Goodbye!")
                return
        elif choice == "8":
            current = _secret("Current master password: ")
            if not current:
                print("Current master password cannot be empty.")
                continue
            new = _secret("New master password (at least 12 characters): ")
            try:
                validate_new_master_password(new)
            except ValueError as exc:
                print(exc)
                continue
            if new != _secret("Confirm new master password: "):
                print("Passwords did not match. Master password unchanged.")
                continue
            try:
                vault.change_master_password(current, new)
                print("Master password changed.")
            except (VaultError, OSError) as exc:
                print(f"Master password unchanged: {exc}")
        else:
            print("Choose a number from 1 to 8.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local encrypted password manager. Existing ./vault.json files stay in place; new default vaults use your local app-data folder.",
        epilog="Example: password-manager --vault C:\\path\\to\\vault.json",
    )
    parser.add_argument("--vault", type=Path, default=None,
                        help="path to the encrypted vault file to create or open (default: local app-data folder)")
    args = parser.parse_args(argv)
    path = args.vault if args.vault is not None else default_vault_path()
    try:
        if path.exists():
            print(f"Opening vault: {path}")
            for attempt in range(1, 4):
                password = _secret("Master password to unlock this vault: ")
                try:
                    vault = Vault.open(path, password)
                    if vault.last_saved_at:
                        print(f"Last saved (UTC): {vault.last_saved_at}")
                    else:
                        print("Last saved time unavailable for this older vault.")
                    break
                except VaultAuthenticationError:
                    remaining = 3 - attempt
                    print("Master password incorrect, or vault data is damaged.")
                    if remaining:
                        print(f"{remaining} attempt{'s' if remaining != 1 else ''} remaining.")
                    else:
                        if not _countdown("No attempts remaining. Vault locked for this run."):
                            _input("Vault remains locked. Press Enter to close.")
                        _clear_screen()
                        return 1
        else:
            if args.vault is None and path.parent != Path("."):
                path.parent.mkdir(parents=True, exist_ok=True)
                restrict_access(path.parent)
            print(f"Creating vault: {path}")
            while True:
                password = _secret("New master password (at least 12 characters): ")
                try:
                    validate_new_master_password(password)
                except ValueError as exc:
                    print(f"{exc} Please try again.")
                    continue
                if password != _secret("Confirm master password: "):
                    print("Passwords did not match. Please try again.")
                    continue
                break
            vault = Vault.create(path, password)
            print("Vault created.")
        _menu(vault)
        return 0
    except (VaultError, OSError, ValueError) as exc:
        _clear_screen()
        print(f"Error: {exc}")
        return 1
    except IdleTimeout:
        _clear_screen()
        print("Session closed after five minutes without keyboard input. Goodbye!")
        return 1
    except (KeyboardInterrupt, EOFError):
        _clear_screen()
        print("\nVault locked.")
        return 1
