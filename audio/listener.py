"""Audio Listener module using Vosk and sounddevice for lightweight offline speech transcription.

Listens in a background thread using sounddevice.RawInputStream and vosk.KaldiRecognizer.
Provides callbacks on_speech_detected() and on_transcription_ready(text: str).
"""

import json
import os
import queue
import threading
from typing import Callable, Optional

try:
    import sounddevice as sd  # type: ignore
except (ImportError, OSError):
    sd = None

try:
    import vosk  # type: ignore
except (ImportError, OSError):
    vosk = None


class AudioListener:
    """Asynchronous offline audio listener using Vosk and sounddevice."""

    def __init__(
        self,
        model_path: str = "model",
        sample_rate: int = 16000,
        on_speech_detected: Optional[Callable[[], None]] = None,
        on_transcription_ready: Optional[Callable[[str], None]] = None,
        **kwargs,
    ) -> None:
        """Initialize AudioListener.

        Args:
            model_path: Path to local Vosk model directory. Defaults to 'model'.
            sample_rate: Audio sampling rate in Hz. Defaults to 16000.
            on_speech_detected: Optional callback when voice activity is detected.
            on_transcription_ready: Optional callback receiving transcribed text string.
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.on_speech_detected = on_speech_detected
        self.on_transcription_ready = on_transcription_ready

        self.model = None
        self.recognizer = None
        self._is_listening = False
        self._listen_thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue()

    def _init_vosk(self) -> None:
        """Initialize Vosk model and recognizer safely."""
        if self.model is not None or vosk is None:
            return

        try:
            # Disable Vosk verbose logging
            vosk.SetLogLevel(-1)

            if os.path.exists(self.model_path):
                self.model = vosk.Model(self.model_path)
            else:
                # Fallback / attempt default model loading
                self.model = vosk.Model(lang="ru")

            if self.model:
                self.recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
        except Exception:
            self.model = None
            self.recognizer = None

    def start_listening(self) -> None:
        """Start listening to microphone input asynchronously in a background thread."""
        if self._is_listening:
            return

        self._is_listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

    def stop_listening(self) -> None:
        """Stop microphone listening thread."""
        self._is_listening = False
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=2.0)

    def _listen_loop(self) -> None:
        """Background thread loop capturing raw audio chunks and feeding Vosk recognizer."""
        self._init_vosk()

        if sd is None or self.recognizer is None:
            self._is_listening = False
            return

        def audio_callback(indata, frames, time_info, status):
            if self._is_listening:
                self._audio_queue.put(bytes(indata))

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            ):
                speech_triggered = False

                while self._is_listening:
                    try:
                        data = self._audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if self.recognizer.AcceptWaveform(data):
                        result_json = self.recognizer.Result()
                        try:
                            result = json.loads(result_json)
                            text = result.get("text", "").strip()
                            if text and self.on_transcription_ready:
                                self.on_transcription_ready(text)
                        except Exception:
                            pass
                        speech_triggered = False
                    else:
                        partial_json = self.recognizer.PartialResult()
                        try:
                            partial = json.loads(partial_json)
                            partial_text = partial.get("partial", "").strip()
                            if partial_text and not speech_triggered:
                                speech_triggered = True
                                if self.on_speech_detected:
                                    self.on_speech_detected()
                        except Exception:
                            pass
        except Exception:
            self._is_listening = False
