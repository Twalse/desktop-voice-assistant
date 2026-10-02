"""Tests for audio.listener and core.router modules."""

import unittest
from unittest.mock import MagicMock, patch

from audio.listener import AudioListener
from core.router import CommandRouter, RouterMode


class TestAudioListener(unittest.TestCase):
    def test_init_and_attributes(self):
        listener = AudioListener(language="ru-RU")
        self.assertEqual(listener.language, "ru-RU")
        self.assertFalse(listener._is_listening)

    def test_audio_callback_success(self):
        mock_speech_detected = MagicMock()
        mock_transcription_ready = MagicMock()

        listener = AudioListener(
            language="ru-RU",
            on_speech_detected=mock_speech_detected,
            on_transcription_ready=mock_transcription_ready,
        )

        mock_recognizer = MagicMock()
        mock_recognizer.recognize_google.return_value = "открой браузер"
        mock_audio = MagicMock()

        listener._audio_callback(mock_recognizer, mock_audio)

        mock_speech_detected.assert_called_once()
        mock_recognizer.recognize_google.assert_called_once_with(mock_audio, language="ru-RU")
        mock_transcription_ready.assert_called_once_with("открой браузер")

    def test_audio_callback_unknown_value_error(self):
        mock_transcription_ready = MagicMock()
        listener = AudioListener(on_transcription_ready=mock_transcription_ready)

        mock_recognizer = MagicMock()

        try:
            import speech_recognition as sr
            mock_recognizer.recognize_google.side_effect = sr.UnknownValueError()
        except ImportError:
            mock_recognizer.recognize_google.side_effect = Exception("UnknownValue")

        mock_audio = MagicMock()
        listener._audio_callback(mock_recognizer, mock_audio)

        mock_transcription_ready.assert_not_called()


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
