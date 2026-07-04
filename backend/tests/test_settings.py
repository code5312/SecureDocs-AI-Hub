import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def test_cors_origins_accepts_comma_separated_string() -> None:
    settings = Settings(_env_file=None, cors_origins="http://localhost,http://localhost:3000")

    assert settings.cors_origins == ["http://localhost", "http://localhost:3000"]


def test_cors_origins_accepts_json_array_string() -> None:
    settings = Settings(_env_file=None, cors_origins='["http://localhost","http://localhost:3000"]')

    assert settings.cors_origins == ["http://localhost", "http://localhost:3000"]


def test_cors_origins_accepts_python_list() -> None:
    settings = Settings(_env_file=None, cors_origins=["http://localhost", "http://localhost:3000"])

    assert settings.cors_origins == ["http://localhost", "http://localhost:3000"]


def test_cors_origins_trims_spaces_and_removes_empty_values() -> None:
    settings = Settings(_env_file=None, cors_origins=" http://localhost , , http://localhost:3000 ")

    assert settings.cors_origins == ["http://localhost", "http://localhost:3000"]


def test_cors_origins_accepts_empty_string_as_empty_list() -> None:
    settings = Settings(_env_file=None, cors_origins="")

    assert settings.cors_origins == []


def test_cors_origins_rejects_invalid_json() -> None:
    with pytest.raises(ValidationError, match="valid string array"):
        Settings(_env_file=None, cors_origins='["http://localhost",]')


def test_cors_origins_rejects_json_object() -> None:
    with pytest.raises(ValidationError, match="string array"):
        Settings(_env_file=None, cors_origins='{"origin":"http://localhost"}')


def test_settings_reads_comma_separated_cors_origins_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost,http://localhost:3000")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost", "http://localhost:3000"]


def test_settings_reads_json_array_cors_origins_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost","http://localhost:3000"]')

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost", "http://localhost:3000"]


def test_settings_uses_no_env_json_decoding_for_comma_separated_cors(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost,http://localhost:3000")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == ["http://localhost", "http://localhost:3000"]
