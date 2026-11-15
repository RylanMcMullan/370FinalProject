"""Interactive command-line menu."""

import argparse
from getpass import getpass
from pathlib import Path

from .generator import generate_password
from .vault import Vault, VaultError


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
        length = int(input("Length [20]: ") or "20")
        choices = []
        for label in ("Lowercase", "Uppercase", "Digits", "Symbols"):
            answer = input(f"{label}? [Y/n]: ").strip().lower()
            if answer not in ("", "y", "yes", "n", "no"):
                raise ValueError("Answer y or n for each character group.")
            choices.append(answer not in ("n", "no"))
        return generate_password(length, lowercase=choices[0], uppercase=choices[1],
                                 digits=choices[2], symbols=choices[3])
    except ValueError as exc:
        print(exc)
        return None


def _menu(vault: Vault) -> None:
    while True:
        print("\n1. List entries  2. View entry  3. Add entry  4. Delete entry")
        print("5. Generate password  6. Lock and exit")
        choice = input("Choose: ").strip()
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
                print(f"Name: {entry['name']}\nUsername: {entry['username']}\nPassword: {entry['password']}")
        elif choice == "3":
            name = input("Name: ").strip()
            username = input("Username: ")
            password = getpass("Password (blank to generate): ")
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
            print("Vault locked.")
            return
        else:
            print("Choose a number from 1 to 6.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local encrypted password manager")
    parser.add_argument("--vault", type=Path, default=Path("vault.json"),
                        help="vault file path (default: ./vault.json)")
    args = parser.parse_args(argv)
    try:
        if args.vault.exists():
            password = getpass("Master password: ")
            vault = Vault.open(args.vault, password)
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
