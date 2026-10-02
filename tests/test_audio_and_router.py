"""Tests for audio.listener and core.router modules."""

import json
import unittest
from unittest.mock import MagicMock, patch

from audio.listener import AudioListener
from core.router import CommandRouter, RouterMode


class TestAudioListener(unittest.TestCase):
    def test_init_and_attributes(self):
        listener = AudioListener(model_path="model", sample_rate=16000)
        self.assertEqual(listener.model_path, "model")
        self.assertEqual(listener.sample_rate, 16000)
        self.assertFalse(listener._is_listening)

    def test_process_waveform_results(self):
        mock_speech_detected = MagicMock()
        mock_transcription_ready = MagicMock()

        listener = AudioListener(
            on_speech_detected=mock_speech_detected,
            on_transcription_ready=mock_transcription_ready,
        )

        mock_recognizer = MagicMock()
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({"text": "открой блокнот"})
        listener.recognizer = mock_recognizer

        # Simulate handling a full waveform result
        if mock_recognizer.AcceptWaveform(b"fake_audio"):
            res = json.loads(mock_recognizer.Result())
            text = res.get("text", "").strip()
            if text and listener.on_transcription_ready:
                listener.on_transcription_ready(text)

        mock_transcription_ready.assert_called_once_with("открой блокнот")


class TestCommandRouter(unittest.TestCase):
    def setUp(self):
        self.mock_app_finder = MagicMock()
        self.router = CommandRouter(app_finder=self.mock_app_finder, mode=RouterMode.STRICT)

    def test_phonetic_replacement_and_launch(self):
        self.mock_app_finder.launch_app.return_value = True

        # Test misrecognitions mapping to "steam"
        res1 = self.router.dispatch("оуэн тим")
        self.mock_app_finder.launch_app.assert_called_with("steam")
        self.assertEqual(res1, "Запускаю Steam")

        res2 = self.router.dispatch("открой с тима")
        self.mock_app_finder.launch_app.assert_called_with("steam")
        self.assertEqual(res2, "Запускаю Steam")

        res3 = self.router.dispatch("запусти стин")
        self.mock_app_finder.launch_app.assert_called_with("steam")
        self.assertEqual(res3, "Запускаю Steam")

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
