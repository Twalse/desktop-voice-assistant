"""Audio Listener module using SpeechRecognition for lightweight speech transcription.

Listens in background using SpeechRecognition and recognize_google.
Provides callbacks on_speech_detected() and on_transcription_ready(text).
"""

from typing import Callable, Optional

try:
    import speech_recognition as sr  # type: ignore
except ImportError:
    sr = None


class AudioListener:
    """Asynchronous audio listener using SpeechRecognition."""

    def __init__(
        self,
        language: str = "ru-RU",
        on_speech_detected: Optional[Callable[[], None]] = None,
        on_transcription_ready: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        """Initialize AudioListener.

        Args:
            language: Speech recognition language code (e.g., 'ru-RU').
            on_speech_detected: Optional callback when speech activity is detected.
            on_transcription_ready: Optional callback receiving transcribed text.
        """
        self.language = language
        self.on_speech_detected = on_speech_detected
        self.on_transcription_ready = on_transcription_ready

        self.recognizer: Optional[sr.Recognizer] = None
        self.microphone: Optional[sr.Microphone] = None
        self.stop_listening_fn: Optional[Callable[[bool], None]] = None
        self._is_listening = False

        if sr:
            try:
                self.recognizer = sr.Recognizer()
            except Exception:
                self.recognizer = None

    def start_listening(self) -> None:
        """Start listening to microphone input asynchronously in the background."""
        if self._is_listening or sr is None or self.recognizer is None:
            return

        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

            self.stop_listening_fn = self.recognizer.listen_in_background(
                self.microphone,
                self._audio_callback,
            )
            self._is_listening = True
        except Exception:
            self._is_listening = False

    def stop_listening(self) -> None:
        """Stop microphone listening loop."""
        if self.stop_listening_fn:
            try:
                self.stop_listening_fn(wait_for_stop=False)
            except Exception:
                pass
            self.stop_listening_fn = None
        self._is_listening = False

    def _audio_callback(self, recognizer: sr.Recognizer, audio: sr.AudioData) -> None:
        """Background callback called when audio frame is captured."""
        if self.on_speech_detected:
            try:
                self.on_speech_detected()
            except Exception:
                pass

        try:
            text = recognizer.recognize_google(audio, language=self.language)
            if text and text.strip() and self.on_transcription_ready:
                try:
                    self.on_transcription_ready(text.strip())
                except Exception:
                    pass
        except sr.UnknownValueError:
            # Speech was unintelligible / background noise
            pass
        except sr.RequestError:
            # API unreached or request failed
            pass
        except Exception:
            pass
