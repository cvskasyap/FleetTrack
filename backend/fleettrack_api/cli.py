from __future__ import annotations

import argparse
import getpass
import sys

import psycopg
from psycopg.rows import dict_row

from fleettrack_api.core.config import get_settings
from fleettrack_api.repositories.auth import AuthRepository
from fleettrack_api.services.auth import AuthService


def _prompt_new_password(label: str) -> str:
    password = getpass.getpass(f"Set {label} password (minimum 14 characters): ")
    confirmation = getpass.getpass(f"Confirm {label} password: ")
    if password != confirmation:
        raise ValueError(f"{label} password confirmation does not match.")
    if len(password) < 14 or "\x00" in password:
        raise ValueError("Passwords must contain at least 14 characters and no null characters.")
    return password


def _authorize_existing_admin(repository: AuthRepository) -> bool:
    username = getpass.getpass("Existing administrator username: ").strip().lower()
    password = getpass.getpass("Existing administrator password: ")
    user = repository.user_for_login(username)
    if (
        user is None
        or not user["is_active"]
        or "ADMIN" not in user["roles"]
        or not AuthService._verify(user["password_hash"], password)
    ):
        return False
    print("Existing administrator authorization accepted.")
    return True


def bootstrap_users() -> int:
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is required to bootstrap accounts.", file=sys.stderr)
        return 2

    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
            repository = AuthRepository(connection)
            user_count, initial_accounts = repository.bootstrap_state()
            required = {
                "admin": ("FleetTrack Administrator", "ADMIN"),
                "user": ("FleetTrack User", "USER"),
            }
            missing = [
                (username, details)
                for username, details in required.items()
                if username not in initial_accounts
            ]
            incorrect_roles = [
                username
                for username, (_, role) in required.items()
                if username in initial_accounts and role not in initial_accounts[username]
            ]
            if not missing and not incorrect_roles:
                print("The initial Admin and User accounts already exist; credentials were not changed.")
                return 0
            if user_count and not _authorize_existing_admin(repository):
                print("An active administrator must authorize this partial bootstrap.", file=sys.stderr)
                return 1
            if incorrect_roles:
                print(
                    "An initial account has an unexpected role; use the administration interface to review it.",
                    file=sys.stderr,
                )
                return 1

            accounts = []
            for username, (display_name, role) in missing:
                password = _prompt_new_password(username)
                accounts.append(
                    {
                        "username": username,
                        "display_name": display_name,
                        "password_hash": AuthService.hash_password(password),
                        "role": role,
                    }
                )
            repository.create_bootstrap_users(accounts)
        print("Initial Admin and User accounts are ready. Passwords were not displayed or logged.")
        return 0
    except (ValueError, psycopg.Error) as exc:
        print(f"Account bootstrap failed: {type(exc).__name__}.", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="fleettrack_api.cli")
    parser.add_argument("command", choices=["bootstrap-users"])
    args = parser.parse_args()
    if args.command == "bootstrap-users":
        raise SystemExit(bootstrap_users())


if __name__ == "__main__":
    main()
