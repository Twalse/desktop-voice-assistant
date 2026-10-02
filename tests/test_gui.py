"""Tests for gui.app module."""

import queue
import unittest
from unittest.mock import MagicMock, patch

from core.router import CommandRouter, RouterMode


class TestVoiceAssistantGUI(unittest.TestCase):
    @patch("customtkinter.CTk.__init__", return_value=None)
    @patch("gui.app.VoiceAssistantGUI.title")
    @patch("gui.app.VoiceAssistantGUI.geometry")
    @patch("gui.app.VoiceAssistantGUI.resizable")
    @patch("gui.app.VoiceAssistantGUI._build_ui")
    @patch("gui.app.VoiceAssistantGUI._start_queue_poller")
    @patch("gui.app.VoiceAssistantGUI._start_system_monitor")
    def test_gui_init_and_mode_toggle(
        self, mock_sys, mock_poller, mock_build, mock_res, mock_geom, mock_title, mock_ctk_init
    ):
        from gui.app import VoiceAssistantGUI

        mock_router = MagicMock(spec=CommandRouter)
        app = VoiceAssistantGUI(router=mock_router)
        app.log_textbox = MagicMock()

        app._on_mode_changed("Диалог (Нейросеть)")
        mock_router.set_mode.assert_called_with(RouterMode.DIALOGUE)

        app._on_mode_changed("Команды (Скрипты)")
        mock_router.set_mode.assert_called_with(RouterMode.STRICT)

    @patch("customtkinter.CTk.__init__", return_value=None)
    @patch("gui.app.VoiceAssistantGUI.title")
    @patch("gui.app.VoiceAssistantGUI.geometry")
    @patch("gui.app.VoiceAssistantGUI.resizable")
    @patch("gui.app.VoiceAssistantGUI._build_ui")
    @patch("gui.app.VoiceAssistantGUI._start_queue_poller")
    @patch("gui.app.VoiceAssistantGUI._start_system_monitor")
    def test_mic_toggle(
        self, mock_sys, mock_poller, mock_build, mock_res, mock_geom, mock_title, mock_ctk_init
    ):
        from gui.app import VoiceAssistantGUI

        mock_listener = MagicMock()
        mock_router = MagicMock()
        app = VoiceAssistantGUI(router=mock_router, listener=mock_listener)

        app.mic_button = MagicMock()
        app.audio_status_label = MagicMock()
        app.status_badge = MagicMock()
        app.log_textbox = MagicMock()

        # Toggle ON
        app._toggle_mic()
        self.assertTrue(app._is_mic_active)
        mock_listener.start_listening.assert_called_once()

        # Toggle OFF
        app._toggle_mic()
        self.assertFalse(app._is_mic_active)
        mock_listener.stop_listening.assert_called_once()

    @patch("customtkinter.CTk.__init__", return_value=None)
    @patch("gui.app.VoiceAssistantGUI.title")
    @patch("gui.app.VoiceAssistantGUI.geometry")
    @patch("gui.app.VoiceAssistantGUI.resizable")
    @patch("gui.app.VoiceAssistantGUI._build_ui")
    @patch("gui.app.VoiceAssistantGUI.after")
    @patch("gui.app.VoiceAssistantGUI._start_system_monitor")
    def test_queue_poller_transcription_event(
        self, mock_sys, mock_after, mock_build, mock_res, mock_geom, mock_title, mock_ctk_init
    ):
        from gui.app import VoiceAssistantGUI

        mock_router = MagicMock()
        mock_router.dispatch.return_value = "Запускаю Discord"

        app = VoiceAssistantGUI(router=mock_router)
        app.status_badge = MagicMock()
        app.log_textbox = MagicMock()

        app.ui_queue.put(("TRANSCRIPTION_READY", "открой discord"))

        # Process queue
        app._start_queue_poller()

        mock_router.dispatch.assert_called_once_with("открой discord")


if __name__ == "__main__":
    unittest.main()
