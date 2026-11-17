"""Interactive command-line menu."""

import argparse
from getpass import getpass
import msvcrt
from pathlib import Path
import time

from .generator import generate_password
from .vault import Vault, VaultAuthenticationError, VaultError


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
        number = int(input("Entry number: "))
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
            answer = input(f"{label}? [Y/n, Enter = yes]: ").strip().lower()
            if answer not in ("", "y", "yes", "n", "no"):
                raise ValueError("Answer y or n for each character group.")
            choices.append(answer not in ("n", "no"))
        minimum = sum(choices)
        if not minimum:
            raise ValueError("Select at least one character group.")
        length = int(input(f"Password length in characters ({minimum}-1024, Enter = 20): ") or "20")
        return generate_password(length, lowercase=choices[0], uppercase=choices[1],
                                 digits=choices[2], symbols=choices[3])
    except ValueError as exc:
        print(exc)
        return None


def _menu(vault: Vault) -> None:
    while True:
        print("\n1. List entries  2. View entry  3. Add entry  4. Delete entry")
        print("5. Generate password  6. Lock and exit  7. Reset vault")
        choice = input("Choose a menu number: ").strip()
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
                print(f"Entry label: {entry['name']}\nUsername or email: {entry['username']}\nPassword: {entry['password']}")
        elif choice == "3":
            name = input("Entry label (e.g., Email or School): ").strip()
            username = input("Username or email for this entry: ")
            password = getpass("Password for this entry (Enter to generate): ")
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
            except OSError as exc:
                print(f"Could not save vault: {exc}")
        elif choice == "4":
            index = _select_entry(vault)
            if index is not None and input("Type DELETE to confirm: ") == "DELETE":
                try:
                    vault.delete(index)
                    print("Entry deleted.")
                except OSError as exc:
                    print(f"Could not save vault: {exc}")
        elif choice == "5":
            password = _generate()
            if password is not None:
                print(f"Generated password: {password}")
        elif choice == "6":
            if _countdown("Vault will lock and close."):
                print("Goodbye!")
                return
        elif choice == "7":
            print("Reset deletes this vault file, including every saved entry and its master password.")
            if input("Type RESET to continue, or press Enter to cancel: ") != "RESET":
                print("Reset canceled.")
                continue
            password = getpass("Enter your current master password to authorize reset: ")
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
                    vault.path.unlink()
                except OSError as exc:
                    print(f"Could not reset vault: {exc}")
                    continue
                print("Vault reset. The next launch will ask for a new master password. Goodbye!")
                return
        else:
            print("Choose a number from 1 to 7.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local encrypted password manager. Start without options to use vault.json in the current folder.",
        epilog="Example: password-manager --vault my-demo-vault.json",
    )
    parser.add_argument("--vault", type=Path, default=Path("vault.json"),
                        help="path to the encrypted vault file to create or open (default: ./vault.json)")
    args = parser.parse_args(argv)
    try:
        if args.vault.exists():
            for attempt in range(1, 4):
                password = getpass("Master password to unlock this vault: ")
                try:
                    vault = Vault.open(args.vault, password)
                    break
                except VaultAuthenticationError:
                    remaining = 3 - attempt
                    print("Master password incorrect, or vault data is damaged.")
                    if remaining:
                        print(f"{remaining} attempt{'s' if remaining != 1 else ''} remaining.")
                    else:
                        if not _countdown("No attempts remaining. Vault locked for this run."):
                            input("Vault remains locked. Press Enter to close.")
                        return 1
        else:
            print(f"Creating vault: {args.vault}")
            password = getpass("New master password: ")
            if not password:
                print("Master password cannot be empty.")
                return 1
            if password != getpass("Confirm master password: "):
                print("Passwords do not match.")
                return 1
            vault = Vault.create(args.vault, password)
            print("Vault created.")
        _menu(vault)
        return 0
    except (VaultError, OSError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nVault locked.")
        return 1
