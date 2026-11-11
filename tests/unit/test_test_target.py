import pytest

from db.manage import test_target as check_target


@pytest.mark.parametrize(
    "environment,database,host",
    [
        ("production", "fulfillops_test", "127.0.0.1"),
        ("test", "fulfillops", "127.0.0.1"),
        ("test", "fulfillops_test", "database.example.com"),
    ],
)
def test_seed_reset_target_rejects_unsafe_configuration(
    monkeypatch, environment, database, host
):
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("POSTGRES_DB", database)
    monkeypatch.setenv("DB_HOST", host)
    with pytest.raises(RuntimeError):
        check_target()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "db"])
def test_seed_reset_target_accepts_explicit_lab_configuration(monkeypatch, host):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("POSTGRES_DB", "fulfillops_test_containers")
    monkeypatch.setenv("DB_HOST", host)
    check_target()
