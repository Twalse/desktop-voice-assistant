"""Tests for audio.listener and core.router modules."""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from audio.listener import AudioListener
from core.router import CommandRouter, RouterMode


class TestAudioListener(unittest.TestCase):
    def test_init_and_attributes(self):
        listener = AudioListener(model_size="small", device="cpu", sample_rate=16000)
        self.assertEqual(listener.model_size, "small")
        self.assertEqual(listener.device, "cpu")
        self.assertEqual(listener.sample_rate, 16000)
        self.assertFalse(listener._is_listening)

    @patch("audio.listener.AudioListener._init_whisper_model")
    def test_transcribe_audio_empty_when_no_model(self, mock_init):
        listener = AudioListener()
        listener.whisper_model = None
        audio_data = np.zeros(16000, dtype=np.float32)
        res = listener.transcribe_audio(audio_data)
        self.assertEqual(res, "")

    def test_transcribe_audio_with_mock_model(self):
        listener = AudioListener()
        mock_seg = MagicMock()
        mock_seg.text = "Hello world"
        mock_whisper = MagicMock()
        mock_whisper.transcribe.return_value = ([mock_seg], None)
        listener.whisper_model = mock_whisper

        audio_data = np.zeros(16000, dtype=np.float32)
        res = listener.transcribe_audio(audio_data)
        self.assertEqual(res, "Hello world")


class TestCommandRouter(unittest.TestCase):
    def setUp(self):
        self.mock_app_finder = MagicMock()
        self.router = CommandRouter(app_finder=self.mock_app_finder, mode=RouterMode.STRICT)

    def test_app_launch_russian(self):
        self.mock_app_finder.launch_app.return_value = True
        res = self.router.dispatch("открой discord")
        self.mock_app_finder.launch_app.assert_called_with("discord")
        self.assertEqual(res, "Запускаю Discord")

    def test_app_launch_english(self):
        self.mock_app_finder.launch_app.return_value = True
        res = self.router.dispatch("launch chrome")
        self.mock_app_finder.launch_app.assert_called_with("chrome")
        self.assertEqual(res, "Запускаю Chrome")

    def test_app_launch_not_found(self):
        self.mock_app_finder.launch_app.return_value = False
        res = self.router.dispatch("запусти fakeapp")
        self.assertEqual(res, "Приложение 'fakeapp' не найдено")

    @patch("core.system_actions.get_current_time", return_value="15:45")
    def test_time_query(self, mock_time):
        res = self.router.dispatch("сколько времени")
        self.assertEqual(res, "Сейчас 15:45")

        res_en = self.router.dispatch("what time is it")
        self.assertEqual(res_en, "Сейчас 15:45")

    @patch("core.system_actions.media_play_pause")
    def test_media_controls(self, mock_play_pause):
        res = self.router.dispatch("пауза")
        mock_play_pause.assert_called_once()
        self.assertEqual(res, "Воспроизведение/Пауза")

    @patch("core.system_actions.volume_up")
    def test_volume_controls(self, mock_vol_up):
        res = self.router.dispatch("громче")
        mock_vol_up.assert_called_once()
        self.assertEqual(res, "Громкость увеличена")

    @patch("core.system_actions.minimize_active_window")
    def test_window_management(self, mock_min):
        res = self.router.dispatch("сверни")
        mock_min.assert_called_once()
        self.assertEqual(res, "Окно свернуто")

    @patch("core.system_actions.get_open_windows", return_value=["Chrome", "Telegram"])
    def test_list_windows(self, mock_get_windows):
        res = self.router.dispatch("список окон")
        self.assertEqual(res, "Открытые окна: Chrome, Telegram")

    def test_strict_mode_unrecognized(self):
        res = self.router.dispatch("расскажи анекдот")
        self.assertEqual(res, "Команда не распознана")

    def test_dialogue_mode_llm_forwarding(self):
        mock_llm = MagicMock(return_value="Вот отличный анекдот!")
        router = CommandRouter(llm_handler=mock_llm, mode=RouterMode.DIALOGUE)

        res = router.dispatch("расскажи анекдот")
        mock_llm.assert_called_once_with("расскажи анекдот")
        self.assertEqual(res, "Вот отличный анекдот!")


if __name__ == "__main__":
    unittest.main()
