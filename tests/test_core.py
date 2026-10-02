"""Tests for core.app_finder and core.system_actions modules."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from core.app_finder import AppFinder, launch_app
from core import system_actions


class TestAppFinder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        # Create mock shortcut files
        self.lnk_file = os.path.join(self.temp_dir.name, "Google Chrome.lnk")
        with open(self.lnk_file, "w") as f:
            f.write("mock lnk content")

        self.cs2_file = os.path.join(self.temp_dir.name, "CS2.lnk")
        with open(self.cs2_file, "w") as f:
            f.write("mock cs2 content")

        self.url_file = os.path.join(self.temp_dir.name, "YouTube.url")
        with open(self.url_file, "w", encoding="utf-8") as f:
            f.write("[InternetShortcut]\nURL=https://youtube.com\n")

        self.finder = AppFinder(extra_paths=[self.temp_dir.name])

    def test_indexing(self):
        self.assertIn("google chrome", self.finder.apps)
        self.assertIn("cs2", self.finder.apps)
        self.assertIn("youtube", self.finder.apps)

    def test_exact_match_prioritization(self):
        with patch.object(self.finder, "_execute", return_value=True) as mock_exec:
            res = self.finder.launch_app("cs2")
            self.assertTrue(res)
            mock_exec.assert_called_once()

    def test_parse_url_shortcut(self):
        url_target = self.finder._parse_shortcut(os.path.join(self.temp_dir.name, "YouTube.url"))
        self.assertEqual(url_target, "https://youtube.com")

    @patch("core.app_finder.AppFinder._execute", return_value=True)
    def test_launch_app_fuzzy_match_success(self, mock_execute):
        # High similarity query
        result = self.finder.launch_app("chrome", threshold=70.0)
        self.assertTrue(result)
        mock_execute.assert_called_once()

    @patch("core.app_finder.AppFinder._execute", return_value=True)
    def test_launch_app_fuzzy_match_below_threshold(self, mock_execute):
        # Low similarity query
        result = self.finder.launch_app("xyzxyz1239999", threshold=70.0)
        self.assertFalse(result)
        mock_execute.assert_not_called()

    @patch("core.app_finder.AppFinder.launch_app", return_value=True)
    def test_module_launch_app(self, mock_launch):
        res = launch_app("chrome")
        self.assertTrue(res)


class TestSystemActions(unittest.TestCase):
    @patch("core.system_actions._send_vk")
    def test_volume_controls_fallback(self, mock_send_vk):
        mock_send_vk.return_value = True

        self.assertTrue(system_actions.volume_up())
        mock_send_vk.assert_called_with(system_actions.VK_VOLUME_UP, count=5)

        self.assertTrue(system_actions.volume_down())
        mock_send_vk.assert_called_with(system_actions.VK_VOLUME_DOWN, count=5)

        self.assertTrue(system_actions.mute())

    @patch("core.system_actions._send_vk")
    def test_media_controls(self, mock_send_vk):
        mock_send_vk.return_value = True

        self.assertTrue(system_actions.media_play_pause())
        self.assertTrue(system_actions.media_next())
        self.assertTrue(system_actions.media_prev())

    def test_datetime_russian(self):
        time_str = system_actions.get_current_time()
        self.assertRegex(time_str, r"^\d{2}:\d{2}$")

        date_str = system_actions.get_current_date()
        self.assertIn(" г., ", date_str)

    @patch("os.system")
    def test_power_commands(self, mock_system):
        mock_system.return_value = 0
        self.assertTrue(system_actions.shutdown_pc())
        self.assertTrue(system_actions.restart_pc())

    def test_move_cursor(self):
        mock_pyautogui = MagicMock()
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            self.assertTrue(system_actions.move_cursor(100, 200))
            mock_pyautogui.moveTo.assert_called_once_with(100, 200)

    def test_click(self):
        mock_pyautogui = MagicMock()
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            self.assertTrue(system_actions.click("left"))
            mock_pyautogui.click.assert_called_once_with(button="left")

    def test_press_hotkey(self):
        mock_pyautogui = MagicMock()
        with patch.dict("sys.modules", {"pyautogui": mock_pyautogui}):
            self.assertTrue(system_actions.press_hotkey("ctrl", "c"))
            mock_pyautogui.hotkey.assert_called_once_with("ctrl", "c")

    def test_get_open_windows(self):
        mock_gw = MagicMock()
        win1 = MagicMock()
        win1.title = "Calculator"
        win1.visible = True

        win2 = MagicMock()
        win2.title = ""
        win2.visible = True

        win3 = MagicMock()
        win3.title = "Untitled - Notepad"
        win3.visible = True

        mock_gw.getAllWindows.return_value = [win1, win2, win3]

        with patch.dict("sys.modules", {"pygetwindow": mock_gw}):
            windows = system_actions.get_open_windows()
            self.assertEqual(windows, ["Calculator", "Untitled - Notepad"])

    def test_window_operations_with_active_window(self):
        mock_gw = MagicMock()
        mock_win = MagicMock()
        mock_gw.getActiveWindow.return_value = mock_win

        with patch.dict("sys.modules", {"pygetwindow": mock_gw}):
            self.assertTrue(system_actions.minimize_active_window())
            mock_win.minimize.assert_called_once()

            self.assertTrue(system_actions.maximize_active_window())
            mock_win.maximize.assert_called_once()

            self.assertTrue(system_actions.close_active_window())
            mock_win.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
