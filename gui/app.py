"""GUI Application module built with CustomTkinter for the Windows Desktop Assistant.

Features:
- Dark theme styling with a compact 450x600 px window.
- Header status badge ("Готов к работе" / "Слушаю..." / "Обработка...").
- Mode toggle switch ("Режим команд (Скрипты)" vs "Режим диалога (Нейросеть)").
- Mic Control toggle button with dynamic visual state.
- Log / Output Panel with scrollable text and clean timestamps.
- System status footer with CPU usage / audio status.
- Thread-safe queue / root.after updates for async audio thread callbacks.
"""

import datetime
import queue
import sys
import threading
import time
from typing import Optional

import customtkinter as ctk

from audio.listener import AudioListener
from core.router import CommandRouter, RouterMode

try:
    import psutil
except ImportError:
    psutil = None


class VoiceAssistantGUI(ctk.CTk):
    """Main GUI window for Desktop Voice Assistant."""

    def __init__(
        self,
        router: Optional[CommandRouter] = None,
        listener: Optional[AudioListener] = None,
    ) -> None:
        """Initialize GUI layout and bind listener and router."""
        super().__init__()

        self.router = router if router is not None else CommandRouter()
        self.listener = listener

        self.ui_queue: queue.Queue = queue.Queue()

        # Wire listener callbacks if listener provided
        if self.listener:
            self.listener.on_speech_detected = self._on_speech_detected_callback
            self.listener.on_transcription_ready = self._on_transcription_ready_callback

        self._is_mic_active = False

        # Window properties
        self.title("Голосовой Ассистент")
        self.geometry("450x600")
        self.resizable(False, False)

        # Theme setting
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_ui()
        self._start_queue_poller()
        self._start_system_monitor()

    def _build_ui(self) -> None:
        """Build widgets and layout elements."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Log panel expands

        # 1. Header Frame with Status Badge
        self.header_frame = ctk.CTkFrame(self, corner_radius=10)
        self.header_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="ГОЛОСОВОЙ АССИСТЕНТ",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, padx=10, pady=(10, 2))

        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="Готов к работе",
            font=ctk.CTkFont(size=12, weight="normal"),
            text_color="#2ECC71",  # Green
        )
        self.status_badge.grid(row=1, column=0, padx=10, pady=(0, 10))

        # 2. Mode Toggle Segmented Button
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        self.mode_frame.grid_columnconfigure(0, weight=1)

        self.mode_selector = ctk.CTkSegmentedButton(
            self.mode_frame,
            values=["Команды (Скрипты)", "Диалог (Нейросеть)"],
            command=self._on_mode_changed,
            font=ctk.CTkFont(size=12),
        )
        self.mode_selector.set("Команды (Скрипты)")
        self.mode_selector.grid(row=0, column=0, sticky="ew", padx=5)

        # 3. Mic Control Button
        self.mic_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mic_frame.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
        self.mic_frame.grid_columnconfigure(0, weight=1)

        self.mic_button = ctk.CTkButton(
            self.mic_frame,
            text="🎤 ВКЛЮЧИТЬ МИКРОФОН",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=45,
            corner_radius=22,
            fg_color="#34495E",  # Muted blue-gray
            hover_color="#2C3E50",
            command=self._toggle_mic,
        )
        self.mic_button.grid(row=0, column=0, padx=30, sticky="ew")

        # 4. Log / Output Panel
        self.log_frame = ctk.CTkFrame(self, corner_radius=10)
        self.log_frame.grid(row=3, column=0, padx=15, pady=10, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        self.log_textbox = ctk.CTkTextbox(
            self.log_frame,
            font=ctk.CTkFont(size=12, family="Consolas"),
            wrap="word",
            activate_scrollbars=True,
        )
        self.log_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # 5. System Status Footer
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=25)
        self.footer_frame.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="ew")
        self.footer_frame.grid_columnconfigure(1, weight=1)

        self.cpu_label = ctk.CTkLabel(
            self.footer_frame,
            text="CPU: 0%",
            font=ctk.CTkFont(size=10),
            text_color="#95A5A6",
        )
        self.cpu_label.grid(row=0, column=0, padx=5, sticky="w")

        self.audio_status_label = ctk.CTkLabel(
            self.footer_frame,
            text="Аудио: Отключено",
            font=ctk.CTkFont(size=10),
            text_color="#95A5A6",
        )
        self.audio_status_label.grid(row=0, column=2, padx=5, sticky="e")

        # Log initial message
        self.log_message("Система инициализирована. Выберите режим работы.")

    def _on_mode_changed(self, value: str) -> None:
        """Handle mode switch toggle."""
        if value == "Диалог (Нейросеть)":
            self.router.set_mode(RouterMode.DIALOGUE)
            self.log_message("[РЕЖИМ] Переключено на Режим Диалога (Нейросеть)")
        else:
            self.router.set_mode(RouterMode.STRICT)
            self.log_message("[РЕЖИМ] Переключено на Режим Команд (Скрипты)")

    def _toggle_mic(self) -> None:
        """Toggle microphone listening state."""
        self._is_mic_active = not self._is_mic_active

        if self._is_mic_active:
            self.mic_button.configure(
                text="🎙 МИКРОФОН АКТИВЕН",
                fg_color="#2ECC71",  # Green accent
                hover_color="#27AE60",
            )
            self.audio_status_label.configure(text="Аудио: Запись...")
            self.update_status_badge("Слушаю...", color="#2ECC71")
            self.log_message("[МИКРОФОН] Запись включена")

            if self.listener:
                self.listener.start_listening()
        else:
            self.mic_button.configure(
                text="🎤 ВКЛЮЧИТЬ МИКРОФОН",
                fg_color="#34495E",
                hover_color="#2C3E50",
            )
            self.audio_status_label.configure(text="Аудио: Отключено")
            self.update_status_badge("Готов к работе", color="#2ECC71")
            self.log_message("[МИКРОФОН] Запись выключена")

            if self.listener:
                self.listener.stop_listening()

    def update_status_badge(self, text: str, color: str = "#2ECC71") -> None:
        """Update header status badge safely."""
        self.status_badge.configure(text=text, text_color=color)

    def log_message(self, message: str) -> None:
        """Append timestamped message to the log textbox."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"

        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", formatted)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    # --- Thread-Safe Queue Handlers ---
    def _on_speech_detected_callback(self) -> None:
        """Callback executed by listener thread when speech starts."""
        self.ui_queue.put(("SPEECH_DETECTED", None))

    def _on_transcription_ready_callback(self, text: str) -> None:
        """Callback executed by listener thread when STT finishes."""
        self.ui_queue.put(("TRANSCRIPTION_READY", text))

    def _start_queue_poller(self) -> None:
        """Periodically check queue for events from background threads."""
        try:
            while not self.ui_queue.empty():
                event_type, payload = self.ui_queue.get_nowait()

                if event_type == "SPEECH_DETECTED":
                    self.update_status_badge("Слушаю...", color="#E67E22")  # Orange

                elif event_type == "TRANSCRIPTION_READY":
                    self.update_status_badge("Обработка...", color="#3498DB")  # Blue
                    self.log_message(f"Вы: {payload}")

                    # Route query and log response
                    response = self.router.dispatch(payload)
                    self.log_message(f"Ассистент: {response}")

                    if self._is_mic_active:
                        self.update_status_badge("Слушаю...", color="#2ECC71")
                    else:
                        self.update_status_badge("Готов к работе", color="#2ECC71")

        except Exception:
            pass

        self.after(100, self._start_queue_poller)

    def _start_system_monitor(self) -> None:
        """Periodically update CPU status footer."""
        if psutil:
            try:
                cpu_usage = psutil.cpu_percent()
                self.cpu_label.configure(text=f"CPU: {cpu_usage:.1f}%")
            except Exception:
                pass

        self.after(2000, self._start_system_monitor)


def launch_gui(router: Optional[CommandRouter] = None, listener: Optional[AudioListener] = None) -> VoiceAssistantGUI:
    """Launch CustomTkinter GUI application.

    Args:
        router: CommandRouter instance.
        listener: AudioListener instance.

    Returns:
        VoiceAssistantGUI instance.
    """
    app = VoiceAssistantGUI(router=router, listener=listener)
    return app


if __name__ == "__main__":
    app = launch_gui()
    app.mainloop()
