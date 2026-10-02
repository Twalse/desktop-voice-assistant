"""Audio Listener module for asynchronous microphone listening and offline STT transcription.

This module listens to the microphone in a background thread, detects voice activity,
records audio chunks when speech is detected, and transcribes them using faster-whisper.
"""

import threading
import time
from typing import Callable, Optional

import numpy as np


class AudioListener:
    """Asynchronous audio listener using sounddevice and faster-whisper STT."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        sample_rate: int = 16000,
        silence_threshold: float = 0.015,
        silence_duration: float = 1.0,
        on_speech_detected: Optional[Callable[[], None]] = None,
        on_transcription_ready: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize AudioListener.

        Args:
            model_size: faster-whisper model size ('base', 'small', etc.).
            device: Computing device ('cuda' or 'cpu'). Falls back to 'cpu' if cuda fails.
            sample_rate: Sampling rate in Hz. Defaults to 16000.
            silence_threshold: RMS amplitude threshold for speech detection.
            silence_duration: Seconds of silence required to trigger end of speech.
            on_speech_detected: Optional callback when voice activity starts.
            on_transcription_ready: Optional callback receiving transcribed text.
        """
        self.model_size = model_size
        self.device = device
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        self.on_speech_detected = on_speech_detected
        self.on_transcription_ready = on_transcription_ready

        self.whisper_model = None
        self._is_listening = False
        self._listen_thread: Optional[threading.Thread] = None

    def _init_whisper_model(self) -> None:
        """Lazy load faster-whisper model with CUDA -> CPU fallback."""
        if self.whisper_model is not None:
            return

        try:
            from faster_whisper import WhisperModel  # type: ignore

            try:
                self.whisper_model = WhisperModel(self.model_size, device=self.device, compute_type="float16")
            except Exception:
                # Fallback to CPU
                self.whisper_model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        except Exception:
            # Model loading failure or faster-whisper missing
            self.whisper_model = None

    def start_listening(self) -> None:
        """Start listening to microphone input asynchronously in a separate thread."""
        if self._is_listening:
            return

        self._is_listening = True
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

    def stop_listening(self) -> None:
        """Stop microphone listening loop."""
        self._is_listening = False
        if self._listen_thread and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=2.0)

    def _listen_loop(self) -> None:
        """Background thread loop for capturing audio and performing VAD & transcription."""
        self._init_whisper_model()

        try:
            import sounddevice as sd  # type: ignore
        except Exception:
            return

        chunk_duration = 0.1  # 100ms chunks
        chunk_samples = int(self.sample_rate * chunk_duration)

        is_speaking = False
        audio_buffer = []
        silence_chunks_count = 0
        max_silence_chunks = int(self.silence_duration / chunk_duration)

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=chunk_samples,
            ) as stream:
                while self._is_listening:
                    data, _ = stream.read(chunk_samples)
                    if data is None or len(data) == 0:
                        continue

                    # Calculate RMS energy for VAD
                    rms = np.sqrt(np.mean(data**2))

                    if rms >= self.silence_threshold:
                        if not is_speaking:
                            is_speaking = True
                            if self.on_speech_detected:
                                try:
                                    self.on_speech_detected()
                                except Exception:
                                    pass
                        audio_buffer.append(data.flatten())
                        silence_chunks_count = 0
                    else:
                        if is_speaking:
                            audio_buffer.append(data.flatten())
                            silence_chunks_count += 1
                            if silence_chunks_count >= max_silence_chunks:
                                # End of speech detected -> transcribe buffer
                                is_speaking = False
                                complete_audio = np.concatenate(audio_buffer, axis=0)
                                audio_buffer.clear()
                                silence_chunks_count = 0

                                self._transcribe_and_callback(complete_audio)

        except Exception:
            self._is_listening = False

    def _transcribe_and_callback(self, audio_data: np.ndarray) -> None:
        """Transcribe float32 audio array using faster-whisper and call callback."""
        if not self.on_transcription_ready:
            return

        text = self.transcribe_audio(audio_data)
        if text and text.strip():
            try:
                self.on_transcription_ready(text.strip())
            except Exception:
                pass

    def transcribe_audio(self, audio_data: np.ndarray) -> str:
        """Transcribe audio numpy array to text.

        Args:
            audio_data: 1D float32 numpy array sampled at sample_rate.

        Returns:
            Transcribed text string or empty string on error.
        """
        self._init_whisper_model()
        if self.whisper_model is None:
            return ""

        try:
            segments, _ = self.whisper_model.transcribe(audio_data, beam_size=5)
            transcription = " ".join([seg.text for seg in segments]).strip()
            return transcription
        except Exception:
            return ""
