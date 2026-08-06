"""Tests for ingestion CLI safety checks."""

from __future__ import annotations

from cloudeyes_platform import cli


def test_serve_requires_token_by_default(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("CLOUDEYES_INGEST_TOKEN", raising=False)

    result = cli.main(["serve", "--data-dir", str(tmp_path)])

    assert result == 2
    assert "token" in capsys.readouterr().err


def test_parser_accepts_loopback_anonymous_mode(tmp_path, monkeypatch) -> None:
    class FakeServer:
        server_address = ("127.0.0.1", 43123)

        def serve_forever(self, *, poll_interval: float) -> None:
            assert poll_interval == 0.2
            raise KeyboardInterrupt

        def server_close(self) -> None:
            return

    monkeypatch.setattr(cli, "create_server", lambda *_args, **_kwargs: FakeServer())

    result = cli.main(
        [
            "serve",
            "--allow-anonymous",
            "--data-dir",
            str(tmp_path),
            "--port",
            "0",
        ]
    )

    assert result == 130
