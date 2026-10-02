"""App Finder module for scanning Windows Start Menu shortcuts and launching applications.

This module indexes .lnk and .url files from Windows Start Menu directories
and provides fuzzy matching search to launch applications.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from rapidfuzz import fuzz, process


class AppFinder:
    """Scans and indexes installed applications and handles fuzzy searching and launching."""

    def __init__(self, extra_paths: Optional[List[str]] = None) -> None:
        """Initialize AppFinder and scan default Windows Start Menu directories."""
        self.apps: Dict[str, Tuple[str, str]] = {}  # clean_name -> (shortcut_path, target_path)
        self.scan_directories(extra_paths)

    def _get_start_menu_paths(self) -> List[Path]:
        """Get standard Windows Start Menu program directories."""
        paths: List[Path] = []
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        programdata = os.environ.get("PROGRAMDATA")
        if programdata:
            paths.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")

        return paths

    def _parse_shortcut(self, file_path: Union[Path, str]) -> str:
        """Parse target path from a shortcut file (.lnk or .url).

        Args:
            file_path: Path or path string to .lnk or .url file.

        Returns:
            Resolved target path or string representation of file_path as fallback.
        """
        path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        ext = path_obj.suffix.lower()
        if ext == ".url":
            try:
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.strip().startswith("URL="):
                            return line.strip().split("URL=", 1)[1]
            except Exception:
                pass
            return str(path_obj)

        if ext == ".lnk":
            if sys.platform == "win32":
                try:
                    import comtypes.client  # type: ignore

                    shell = comtypes.client.CreateObject("WScript.Shell")
                    shortcut = shell.CreateShortcut(str(path_obj))
                    target = shortcut.TargetPath
                    if target:
                        return target
                except Exception:
                    pass
            return str(path_obj)

        return str(path_obj)

    def scan_directories(self, extra_paths: Optional[List[str]] = None) -> None:
        """Scan Start Menu directories for .lnk and .url shortcuts and populate index.

        Args:
            extra_paths: Optional list of additional directory paths to scan.
        """
        self.apps.clear()
        search_paths = self._get_start_menu_paths()
        if extra_paths:
            for ep in extra_paths:
                search_paths.append(Path(ep))

        for base_path in search_paths:
            if not base_path.exists():
                continue

            try:
                for file_path in base_path.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in [".lnk", ".url"]:
                        clean_name = file_path.stem.strip().lower()
                        if clean_name and clean_name not in self.apps:
                            target_path = self._parse_shortcut(file_path)
                            self.apps[clean_name] = (str(file_path), target_path)
            except Exception:
                # Safely ignore directory traversal errors
                continue

    def launch_app(self, query: str, threshold: float = 70.0) -> bool:
        """Find the closest matching app for query and launch it if similarity >= threshold.

        Args:
            query: The application name query to search for.
            threshold: Minimum rapidfuzz similarity score (0-100). Defaults to 70.0.

        Returns:
            True if matching application was found and successfully launched, False otherwise.
        """
        if not query or not self.apps:
            return False

        clean_query = query.strip().lower()
        choices = list(self.apps.keys())

        try:
            match = process.extractOne(clean_query, choices, scorer=fuzz.WRatio)
            if not match:
                return False

            matched_name, score, _ = match
            if score < threshold:
                return False

            shortcut_path, target_path = self.apps[matched_name]

            # Attempt launching app via os.startfile or subprocess.Popen
            return self._execute(shortcut_path, target_path)
        except Exception:
            return False

    def _execute(self, shortcut_path: str, target_path: str) -> bool:
        """Execute application via os.startfile or subprocess.Popen safely.

        Args:
            shortcut_path: Path to shortcut file.
            target_path: Path to target binary/URL.

        Returns:
            True if execution started without exceptions, False otherwise.
        """
        # Strategy 1: os.startfile if available (Windows)
        if hasattr(os, "startfile"):
            try:
                # Try target first if executable or url, else shortcut file
                file_to_start = target_path if (target_path and os.path.exists(target_path)) else shortcut_path
                os.startfile(file_to_start)
                return True
            except Exception:
                try:
                    os.startfile(shortcut_path)
                    return True
                except Exception:
                    pass

        # Strategy 2: subprocess.Popen
        try:
            cmd = target_path if (target_path and target_path != shortcut_path) else shortcut_path
            subprocess.Popen([cmd], shell=True)
            return True
        except Exception:
            return False


# Global default instance for top-level usage
_default_finder: Optional[AppFinder] = None


def launch_app(query: str) -> bool:
    """Module-level function to launch an app by query using AppFinder.

    Args:
        query: Application name query.

    Returns:
        True if application was found and launched, False otherwise.
    """
    global _default_finder
    if _default_finder is None:
        _default_finder = AppFinder()
    return _default_finder.launch_app(query)
