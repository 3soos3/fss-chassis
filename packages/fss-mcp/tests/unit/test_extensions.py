"""Unit tests for fss_mcp.extensions module."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from fss_mcp.extensions import _check_file_permissions, _scan_directory, discover_extensions


class TestFilePermissionsPlatformCheck:
    """Tests for platform-aware file permissions checking."""

    def test_windows_skips_permission_check(self, tmp_path: Path) -> None:
        """On Windows, _check_file_permissions should return True (skip check)."""
        test_file = tmp_path / "ext.py"
        test_file.write_text("# extension")
        with patch("fss_mcp.extensions.sys") as mock_sys:
            mock_sys.platform = "win32"
            assert _check_file_permissions(test_file) is True

    def test_non_windows_checks_permissions(self, tmp_path: Path) -> None:
        """On non-Windows, _check_file_permissions should check S_IWOTH."""
        test_file = tmp_path / "ext.py"
        test_file.write_text("# extension")
        # File created by tmp_path won't be world-writable, so should pass
        with patch("fss_mcp.extensions.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert _check_file_permissions(test_file) is True


class TestScanDirectory:
    """Tests for _scan_directory."""

    def test_loads_and_registers_module(self, tmp_path: Path) -> None:
        ext_file = tmp_path / "my_tool.py"
        ext_file.write_text("def register(server): server.called = True\n")

        server = MagicMock()
        _scan_directory(tmp_path, "fake_prefix", server)
        server.called  # attribute was set by register()

    def test_skips_init_py(self, tmp_path: Path) -> None:
        (tmp_path / "__init__.py").write_text("# package")
        server = MagicMock()
        _scan_directory(tmp_path, "fake_prefix", server)
        # No call attempted for __init__.py

    def test_skips_invalid_module_name(self, tmp_path: Path) -> None:
        (tmp_path / "bad-name.py").write_text("def register(s): pass\n")
        server = MagicMock()
        _scan_directory(tmp_path, "fake_prefix", server)
        # No register() called — invalid stem is skipped


class TestDiscoverExtensionsExtraPackages:
    """Tests for extra_packages parameter of discover_extensions."""

    def test_extra_package_is_scanned(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "my_pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        tool_file = pkg_dir / "tool_a.py"
        tool_file.write_text("def register(server): server.tool_a_registered = True\n")

        # Make the package importable by adding its parent to sys.path
        fake_spec = MagicMock()
        fake_spec.submodule_search_locations = [str(pkg_dir)]

        server = MagicMock()
        with patch("fss_mcp.extensions.importlib.util.find_spec", return_value=fake_spec):
            with patch.object(sys, "path", [str(tmp_path)] + sys.path):
                discover_extensions(server, extra_packages=("my_pkg",))

        assert server.tool_a_registered is True

    def test_missing_extra_package_logs_warning_no_crash(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        server = MagicMock()
        with patch("fss_mcp.extensions.importlib.util.find_spec", return_value=None):
            with caplog.at_level(logging.WARNING, logger="fss_mcp.extensions"):
                discover_extensions(server, extra_packages=("nonexistent.pkg",))

        assert any("nonexistent.pkg" in r.message for r in caplog.records)

    def test_empty_extra_packages_unchanged_behaviour(self) -> None:
        server = MagicMock()
        # Should not raise even with no extra packages
        discover_extensions(server, extra_packages=())
