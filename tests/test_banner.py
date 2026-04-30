from unittest.mock import patch

from kanon._banner import _BANNER, _should_emit_banner


def test_banner_is_nonempty_and_contains_kanon():
    assert isinstance(_BANNER, str)
    assert len(_BANNER) > 0
    # ASCII art spells "Kanon" — verify key fragments are present
    assert "| |/ /" in _BANNER  # K
    assert "| ' /" in _BANNER   # a-row
    assert "___" in _BANNER     # o arcs


def test_quiet_true_always_returns_false():
    with patch("sys.stderr") as mock_stderr:
        mock_stderr.isatty.return_value = True
        assert _should_emit_banner(quiet=True) is False


def test_quiet_false_tty_returns_true():
    with patch("kanon._banner.sys.stderr") as mock_stderr:
        mock_stderr.isatty.return_value = True
        assert _should_emit_banner(quiet=False) is True


def test_quiet_false_no_tty_returns_false():
    with patch("kanon._banner.sys.stderr") as mock_stderr:
        mock_stderr.isatty.return_value = False
        assert _should_emit_banner(quiet=False) is False
