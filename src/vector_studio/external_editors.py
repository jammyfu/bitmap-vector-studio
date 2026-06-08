"""External vector editor detection and integration.

Provides cross-platform discovery of installed vector editors (Illustrator,
Inkscape, Figma, Affinity Designer, CorelDRAW, Vectr, Boxy SVG) and utilities
to open generated SVG files without blocking the main process.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class EditorInfo:
    """Metadata for a detected external vector editor."""

    name: str
    display_name: str
    executable_path: Path | None
    platform: str
    is_available: bool

    def __repr__(self) -> str:
        status = "available" if self.is_available else "not found"
        return f"<EditorInfo {self.name!r} ({status})>"


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------

def _current_platform() -> str:
    """Return a normalized platform name."""
    system = platform.system()
    if system == "Windows":
        return "windows"
    if system == "Darwin":
        return "macos"
    return "linux"


# ---------------------------------------------------------------------------
# Windows registry helpers
# ---------------------------------------------------------------------------

def _winreg_read_install_path(key_path: str, value_name: str = "InstallPath") -> Path | None:
    """Try to read an installation directory from the Windows registry."""
    try:
        import winreg
    except ImportError:
        return None

    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    for hive in hives:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                path, _ = winreg.QueryValueEx(key, value_name)
                if path and isinstance(path, str):
                    return Path(path)
        except OSError:
            continue
    return None


def _winreg_read_uninstall_display_name(subkey: str) -> str | None:
    """Read DisplayName from an Uninstall registry subkey."""
    try:
        import winreg
    except ImportError:
        return None

    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
    for hive in hives:
        try:
            with winreg.OpenKey(hive, f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{subkey}") as key:
                name, _ = winreg.QueryValueEx(key, "DisplayName")
                if name and isinstance(name, str):
                    return name
        except OSError:
            continue
    return None


# ---------------------------------------------------------------------------
# Editor definitions & detection logic
# ---------------------------------------------------------------------------

WINDOWS_COMMON_PATHS: dict[str, list[Path]] = {
    "illustrator": [
        Path(r"C:\Program Files\Adobe\Adobe Illustrator 2024\Support Files\Contents\Windows\Illustrator.exe"),
        Path(r"C:\Program Files\Adobe\Adobe Illustrator 2023\Support Files\Contents\Windows\Illustrator.exe"),
        Path(r"C:\Program Files\Adobe\Adobe Illustrator 2022\Support Files\Contents\Windows\Illustrator.exe"),
        Path(r"C:\Program Files\Adobe\Adobe Illustrator 2021\Support Files\Contents\Windows\Illustrator.exe"),
        Path(r"C:\Program Files\Adobe\Adobe Illustrator 2020\Support Files\Contents\Windows\Illustrator.exe"),
        Path(r"C:\Program Files\Adobe\Adobe Illustrator CC 2019\Support Files\Contents\Windows\Illustrator.exe"),
    ],
    "inkscape": [
        Path(r"C:\Program Files\Inkscape\bin\inkscape.exe"),
        Path(r"C:\Program Files\Inkscape\inkscape.exe"),
    ],
    "figma": [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Figma" / "Figma.exe",
        Path(r"C:\Users\%USERNAME%\AppData\Local\Figma\Figma.exe"),
    ],
    "affinity_designer": [
        Path(r"C:\Program Files\Affinity\Designer\Designer.exe"),
        Path(r"C:\Program Files\Affinity\Designer 2\Designer.exe"),
    ],
    "coreldraw": [
        Path(r"C:\Program Files\Corel\CorelDRAW Graphics Suite 2024\Programs64\CorelDRW.exe"),
        Path(r"C:\Program Files\Corel\CorelDRAW Graphics Suite 2023\Programs64\CorelDRW.exe"),
        Path(r"C:\Program Files\Corel\CorelDRAW Graphics Suite 2022\Programs64\CorelDRW.exe"),
    ],
    "vectr": [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Vectr" / "Vectr.exe",
    ],
    "boxy_svg": [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "boxy-svg" / "Boxy SVG.exe",
        Path(r"C:\Program Files\Boxy SVG\Boxy SVG.exe"),
    ],
}

MACOS_COMMON_PATHS: dict[str, list[Path]] = {
    "illustrator": [
        Path("/Applications/Adobe Illustrator 2024/Adobe Illustrator 2024.app"),
        Path("/Applications/Adobe Illustrator 2023/Adobe Illustrator 2023.app"),
        Path("/Applications/Adobe Illustrator 2022/Adobe Illustrator 2022.app"),
        Path("/Applications/Adobe Illustrator 2021/Adobe Illustrator 2021.app"),
        Path("/Applications/Adobe Illustrator 2020/Adobe Illustrator 2020.app"),
        Path("/Applications/Adobe Illustrator CC 2019/Adobe Illustrator CC 2019.app"),
        Path("/Applications/Adobe Illustrator.app"),
    ],
    "inkscape": [
        Path("/Applications/Inkscape.app"),
    ],
    "figma": [
        Path("/Applications/Figma.app"),
    ],
    "affinity_designer": [
        Path("/Applications/Affinity Designer.app"),
        Path("/Applications/Affinity Designer 2.app"),
    ],
    "vectr": [
        Path("/Applications/Vectr.app"),
    ],
    "boxy_svg": [
        Path("/Applications/Boxy SVG.app"),
    ],
}

LINUX_COMMON_PATHS: dict[str, list[Path]] = {
    "inkscape": [
        Path("/usr/bin/inkscape"),
        Path("/usr/local/bin/inkscape"),
        Path("/snap/bin/inkscape"),
        Path("/flatpak/app/org.inkscape.Inkscape/current/active/export/bin/inkscape"),
    ],
    "figma": [
        Path("/usr/bin/figma-linux"),
    ],
}

_EDITOR_DISPLAY_NAMES: dict[str, str] = {
    "illustrator": "Adobe Illustrator",
    "inkscape": "Inkscape",
    "figma": "Figma",
    "affinity_designer": "Affinity Designer",
    "coreldraw": "CorelDRAW",
    "vectr": "Vectr",
    "boxy_svg": "Boxy SVG",
}

# Priority order for default editor selection.
_DEFAULT_PRIORITY: tuple[str, ...] = (
    "illustrator",
    "affinity_designer",
    "inkscape",
    "figma",
    "coreldraw",
    "boxy_svg",
    "vectr",
)


def _resolve_windows_path_candidates(candidates: list[Path]) -> list[Path]:
    """Expand environment variables in Windows path strings."""
    resolved: list[Path] = []
    for candidate in candidates:
        try:
            expanded = Path(os.path.expandvars(str(candidate)))
        except (TypeError, ValueError):
            continue
        resolved.append(expanded)
    return resolved


def _detect_editor_on_windows(name: str) -> EditorInfo:
    """Detect a single editor on Windows."""
    candidates = _resolve_windows_path_candidates(WINDOWS_COMMON_PATHS.get(name, []))
    executable: Path | None = None

    # 1. Check common install paths
    for candidate in candidates:
        if candidate.exists():
            executable = candidate
            break

    # 2. Try registry for specific editors
    if executable is None:
        if name == "illustrator":
            reg_path = _winreg_read_install_path(
                r"SOFTWARE\Adobe\Adobe Illustrator\24.0",
                "InstallPath",
            )
            if reg_path:
                exe = reg_path / "Support Files" / "Contents" / "Windows" / "Illustrator.exe"
                if exe.exists():
                    executable = exe
        elif name == "inkscape":
            reg_path = _winreg_read_install_path(
                r"SOFTWARE\Inkscape\Inkscape",
                "InstallPath",
            )
            if reg_path:
                exe = reg_path / "bin" / "inkscape.exe"
                if exe.exists():
                    executable = exe

    # 3. Fallback to PATH search for CLI-available editors
    if executable is None and name in ("inkscape",):
        which = shutil.which("inkscape")
        if which:
            executable = Path(which)

    is_available = executable is not None and executable.exists()
    return EditorInfo(
        name=name,
        display_name=_EDITOR_DISPLAY_NAMES.get(name, name),
        executable_path=executable,
        platform="windows",
        is_available=is_available,
    )


def _detect_editor_on_macos(name: str) -> EditorInfo:
    """Detect a single editor on macOS."""
    candidates = MACOS_COMMON_PATHS.get(name, [])
    executable: Path | None = None

    for candidate in candidates:
        if candidate.exists():
            executable = candidate
            break

    # Fallback to PATH for CLI tools
    if executable is None and name in ("inkscape",):
        which = shutil.which("inkscape")
        if which:
            executable = Path(which)

    is_available = executable is not None and executable.exists()
    return EditorInfo(
        name=name,
        display_name=_EDITOR_DISPLAY_NAMES.get(name, name),
        executable_path=executable,
        platform="macos",
        is_available=is_available,
    )


def _detect_editor_on_linux(name: str) -> EditorInfo:
    """Detect a single editor on Linux."""
    candidates = LINUX_COMMON_PATHS.get(name, [])
    executable: Path | None = None

    for candidate in candidates:
        if candidate.exists():
            executable = candidate
            break

    if executable is None:
        which = shutil.which(name.replace("_", "-"))
        if which:
            executable = Path(which)
        # Additional CLI aliases
        if executable is None and name == "inkscape":
            which = shutil.which("inkscape")
            if which:
                executable = Path(which)

    is_available = executable is not None and executable.exists()
    return EditorInfo(
        name=name,
        display_name=_EDITOR_DISPLAY_NAMES.get(name, name),
        executable_path=executable,
        platform="linux",
        is_available=is_available,
    )


def detect_editors() -> list[EditorInfo]:
    """Detect all supported external vector editors on the current system.

    Returns:
        A list of :class:`EditorInfo` objects, one per supported editor.
        Editors that are not installed will have ``is_available=False``.
    """
    plat = _current_platform()
    all_names = list(_EDITOR_DISPLAY_NAMES.keys())

    if plat == "windows":
        return [_detect_editor_on_windows(name) for name in all_names]
    if plat == "macos":
        return [_detect_editor_on_macos(name) for name in all_names]
    return [_detect_editor_on_linux(name) for name in all_names]


def get_default_editor() -> EditorInfo | None:
    """Return the highest-priority available editor, or ``None`` if none found."""
    editors = detect_editors()
    available = {e.name: e for e in editors if e.is_available}
    for name in _DEFAULT_PRIORITY:
        if name in available:
            return available[name]
    return None


# ---------------------------------------------------------------------------
# Opening files
# ---------------------------------------------------------------------------

class EditorNotFoundError(RuntimeError):
    """Raised when the requested editor is not available on the system."""

    def __init__(self, editor_name: str) -> None:
        super().__init__(f"Editor '{editor_name}' is not installed or not found.")
        self.editor_name = editor_name


class EditorOpenError(RuntimeError):
    """Raised when launching the editor fails."""

    def __init__(self, editor_name: str, svg_path: Path, cause: Exception) -> None:
        super().__init__(f"Failed to open {svg_path} with '{editor_name}': {cause}")
        self.editor_name = editor_name
        self.svg_path = svg_path
        self.__cause__ = cause


def _open_on_windows(svg_path: Path, editor: EditorInfo) -> None:
    """Launch *svg_path* with *editor* on Windows without blocking."""
    exe = editor.executable_path
    if exe is None or not exe.exists():
        raise EditorNotFoundError(editor.name)

    # For .app-style bundles on Windows we can still use the exe directly.
    # If the editor is Inkscape or another CLI-friendly tool, pass the file.
    if editor.name in ("inkscape", "vectr", "boxy_svg"):
        subprocess.Popen([str(exe), str(svg_path)], shell=False)
        return

    # For GUI-centric apps (Illustrator, Figma, Affinity, CorelDRAW)
    # we use ``startfile`` when possible, otherwise Popen with shell.
    try:
        os.startfile(str(svg_path))
    except OSError as exc:
        # Fallback: open via the executable with the file as argument.
        subprocess.Popen([str(exe), str(svg_path)], shell=False)


def _open_on_macos(svg_path: Path, editor: EditorInfo) -> None:
    """Launch *svg_path* with *editor* on macOS without blocking."""
    exe = editor.executable_path
    if exe is None or not exe.exists():
        raise EditorNotFoundError(editor.name)

    # For .app bundles, use ``open -a``.
    if exe.suffix == ".app":
        app_name = exe.name.replace(".app", "")
        subprocess.Popen(["open", "-a", app_name, str(svg_path)], shell=False)
        return

    # For plain binaries, invoke directly.
    subprocess.Popen([str(exe), str(svg_path)], shell=False)


def _open_on_linux(svg_path: Path, editor: EditorInfo) -> None:
    """Launch *svg_path* with *editor* on Linux without blocking."""
    exe = editor.executable_path
    if exe is None or not exe.exists():
        raise EditorNotFoundError(editor.name)

    # Prefer direct invocation for known CLI-friendly editors.
    if editor.name in ("inkscape", "vectr", "boxy_svg"):
        subprocess.Popen([str(exe), str(svg_path)], shell=False)
        return

    # For GUI apps, try xdg-open first, then direct invocation.
    try:
        subprocess.Popen(["xdg-open", str(svg_path)], shell=False)
    except FileNotFoundError:
        subprocess.Popen([str(exe), str(svg_path)], shell=False)


def open_with_editor(svg_path: Path, editor_name: str | None = None) -> None:
    """Open an SVG file with a specific external editor.

    Args:
        svg_path: Path to the SVG file to open.
        editor_name: Internal editor name (e.g. ``"inkscape"``,
            ``"illustrator"``). If ``None``, the system default editor is used.

    Raises:
        EditorNotFoundError: If the requested editor is not installed.
        EditorOpenError: If the launch itself fails.
    """
    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    plat = _current_platform()

    if editor_name is None:
        # Use system default handler for the file type.
        if plat == "windows":
            try:
                os.startfile(str(svg_path))
            except OSError as exc:
                raise EditorOpenError("default", svg_path, exc) from exc
            return
        if plat == "macos":
            try:
                subprocess.Popen(["open", str(svg_path)], shell=False)
            except OSError as exc:
                raise EditorOpenError("default", svg_path, exc) from exc
            return
        # Linux
        try:
            subprocess.Popen(["xdg-open", str(svg_path)], shell=False)
        except FileNotFoundError as exc:
            raise EditorOpenError("default", svg_path, exc) from exc
        return

    editors = detect_editors()
    editor_map = {e.name: e for e in editors}
    editor = editor_map.get(editor_name)
    if editor is None or not editor.is_available:
        raise EditorNotFoundError(editor_name or "default")

    try:
        if plat == "windows":
            _open_on_windows(svg_path, editor)
        elif plat == "macos":
            _open_on_macos(svg_path, editor)
        else:
            _open_on_linux(svg_path, editor)
    except (OSError, subprocess.SubprocessError) as exc:
        raise EditorOpenError(editor.name, svg_path, exc) from exc


def open_with_default_editor(svg_path: Path) -> None:
    """Open an SVG file with the highest-priority available editor.

    If no supported editor is detected, falls back to the system default
    file handler (``startfile``, ``open``, or ``xdg-open``).

    Args:
        svg_path: Path to the SVG file to open.

    Raises:
        EditorOpenError: If the launch fails.
    """
    svg_path = Path(svg_path)
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG file not found: {svg_path}")

    default = get_default_editor()
    if default is not None:
        open_with_editor(svg_path, default.name)
    else:
        open_with_editor(svg_path, None)
