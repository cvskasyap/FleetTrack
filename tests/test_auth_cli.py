from __future__ import annotations

from types import SimpleNamespace

from fleettrack_api import cli


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return False


def _configure_bootstrap(monkeypatch, *, passwords, account_count=0, accounts=None):
    created_accounts: list[dict] = []
    prompts: list[str] = []
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(database_url="postgresql://test"))
    monkeypatch.setattr(cli.psycopg, "connect", lambda *_args, **_kwargs: FakeConnection())

    class FakeRepository:
        def __init__(self, _connection):
            pass

        def bootstrap_state(self):
            return account_count, accounts or {}

        def create_bootstrap_users(self, new_accounts):
            created_accounts.extend(new_accounts)

    monkeypatch.setattr(cli, "AuthRepository", FakeRepository)
    password_values = iter(passwords)

    def get_password(prompt):
        prompts.append(prompt)
        return next(password_values)

    monkeypatch.setattr(cli.getpass, "getpass", get_password)
    monkeypatch.setattr(cli.AuthService, "hash_password", staticmethod(lambda value: f"hash:{value}"))
    return created_accounts, prompts


def test_bootstrap_prompts_without_echo_and_never_prints_passwords(monkeypatch, capsys):
    created_accounts, prompts = _configure_bootstrap(
        monkeypatch,
        passwords=[
            "admin-password-1234",
            "admin-password-1234",
            "user-password-12345",
            "user-password-12345",
        ],
    )

    assert cli.bootstrap_users() == 0

    output = capsys.readouterr()
    assert len(prompts) == 4
    assert created_accounts == [
        {
            "username": "admin",
            "display_name": "FleetTrack Administrator",
            "password_hash": "hash:admin-password-1234",
            "role": "ADMIN",
        },
        {
            "username": "user",
            "display_name": "FleetTrack User",
            "password_hash": "hash:user-password-12345",
            "role": "USER",
        },
    ]
    assert "admin-password-1234" not in output.out
    assert "user-password-12345" not in output.out


def test_bootstrap_rejects_mismatched_confirmation_without_creating_accounts(monkeypatch, capsys):
    created_accounts, _prompts = _configure_bootstrap(
        monkeypatch,
        passwords=["admin-password-1234", "different-password-1234"],
    )

    assert cli.bootstrap_users() == 1

    output = capsys.readouterr()
    assert created_accounts == []
    assert "ValueError" in output.err
    assert "admin-password-1234" not in output.err
    assert "different-password-1234" not in output.err
