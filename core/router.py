"""Command Router module for multi-language voice command dispatching.

Supports Russian and English phrases, phonetic normalization, pattern extraction, fuzzy matching,
and two operation modes: Strict/Scripted mode and Dialogue/LLM mode.
"""

import re
from enum import Enum
from typing import Callable, Dict, Optional, Tuple

from rapidfuzz import fuzz

from core import system_actions
from core.app_finder import AppFinder, launch_app

# --- Phonetic Replacement & Alias Dictionary ---
# Add common Speech-to-Text misrecognitions here.
# Longer phrases should come before shorter substrings for accurate replacement.
PHONETIC_REPLACEMENTS: Dict[str, str] = {
    "оуэн тим": "открой steam",
    "а у пэн стоим": "открой steam",
    "с тима": "steam",
    "с тим": "steam",
    "с тем": "steam",
    "стин": "steam",
    "дискорт": "discord",
    "дискорд": "discord",
    "хром": "chrome",
    "браузер": "chrome",
    "калькулятор": "calculator",
    "блокнот": "notepad",
}


class RouterMode(Enum):
    """Operation modes for CommandRouter."""
    STRICT = "strict"      # Predefined command matching and app launching only
    DIALOGUE = "dialogue"  # Forwards unhandled or arbitrary queries to external LLM interface


class CommandRouter:
    """Dispatches user transcribed text queries to system actions, app launches, or LLM interface."""

    def __init__(
        self,
        app_finder: Optional[AppFinder] = None,
        llm_handler: Optional[Callable[[str], str]] = None,
        mode: RouterMode = RouterMode.STRICT,
        phonetic_replacements: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize CommandRouter.

        Args:
            app_finder: AppFinder instance. Defaults to new instance or module level handler.
            llm_handler: Optional callback function for LLM/Dialogue processing.
            mode: Operating mode (RouterMode.STRICT or RouterMode.DIALOGUE).
            phonetic_replacements: Dictionary of phonetic corrections. Defaults to PHONETIC_REPLACEMENTS.
        """
        self.app_finder = app_finder
        self.llm_handler = llm_handler
        self.mode = mode
        self.phonetic_replacements = phonetic_replacements if phonetic_replacements is not None else PHONETIC_REPLACEMENTS

    def set_mode(self, mode: RouterMode) -> None:
        """Change current operation mode.

        Args:
            mode: RouterMode.STRICT or RouterMode.DIALOGUE.
        """
        self.mode = mode

    def _normalize_text(self, text: str) -> str:
        """Apply phonetic normalization and alias replacement on query string.

        Args:
            text: Lowercase query text.

        Returns:
            Normalized text with misrecognized terms replaced by canonical forms.
        """
        normalized = text.strip().lower()

        # Sort replacements by key length descending so longer phrases match first
        sorted_replacements = sorted(self.phonetic_replacements.items(), key=lambda item: len(item[0]), reverse=True)

        for misrecognized, canonical in sorted_replacements:
            pattern = re.compile(re.escape(misrecognized.lower()), re.IGNORECASE)
            normalized = pattern.sub(canonical, normalized)

        return normalized.strip()

    def dispatch(self, query: str) -> str:
        """Route and execute a voice or text query.

        Args:
            query: Input transcription phrase in Russian or English.

        Returns:
            Status message string describing the outcome of the operation.
        """
        if not query or not query.strip():
            return "Пустой запрос"

        # Apply phonetic normalization pre-processing
        text = self._normalize_text(query)

        # 1. App Launching Patterns
        app_match, app_name = self._extract_app_launch_query(text)
        if app_match:
            launched = False
            if self.app_finder:
                launched = self.app_finder.launch_app(app_name)
            else:
                launched = launch_app(app_name)

            if launched:
                # Return clean capitalized name or original extracted name
                return f"Запускаю {app_name.capitalize()}"
            else:
                return f"Приложение '{app_name}' не найдено"

        # 2. Time/Date Info Queries
        if self._is_match(text, ["сколько времени", "который час", "какое время", "what time is it", "what's the time"]):
            current_time = system_actions.get_current_time()
            return f"Сейчас {current_time}"

        if self._is_match(text, ["какое число", "какой сегодня день", "дата", "what date is it", "today's date"]):
            current_date = system_actions.get_current_date()
            return f"Сегодня {current_date}"

        # 3. Media Controls
        if self._is_match(text, ["пауза", "плей", "останови видео", "воспроизведение", "pause", "resume", "play"]):
            system_actions.media_play_pause()
            return "Воспроизведение/Пауза"

        if self._is_match(text, ["следующий трек", "следующая песня", "дальше", "next", "next track"]):
            system_actions.media_next()
            return "Следующий трек"

        if self._is_match(text, ["предыдущий трек", "назад", "prev", "previous track"]):
            system_actions.media_prev()
            return "Предыдущий трек"

        # 4. Volume Controls
        if self._is_match(text, ["громче", "сделай громче", "увеличь звук", "volume up", "louder"]):
            system_actions.volume_up()
            return "Громкость увеличена"

        if self._is_match(text, ["тише", "сделай тише", "уменьши звук", "volume down", "quieter"]):
            system_actions.volume_down()
            return "Громкость уменьшена"

        if self._is_match(text, ["выключи звук", "без звука", "мут", "mute", "unmute"]):
            system_actions.mute()
            return "Звук переключен"

        # 5. Window Management
        if self._is_match(text, ["сверни", "свернуть окно", "сверни окно", "minimize"]):
            system_actions.minimize_active_window()
            return "Окно свернуто"

        if self._is_match(text, ["разверни", "развернуть окно", "разверни окно", "maximize"]):
            system_actions.maximize_active_window()
            return "Окно развернуто"

        if self._is_match(text, ["закрой окно", "закрой", "закрыть окно", "close window", "close"]):
            system_actions.close_active_window()
            return "Окно закрыто"

        if self._is_match(text, ["что открыто", "список окон", "какие окна открыты", "open windows", "list windows"]):
            windows = system_actions.get_open_windows()
            if windows:
                return f"Открытые окна: {', '.join(windows)}"
            return "Нет открытых окон"

        # 6. Mode 2: Dialogue / LLM fallback
        if self.mode == RouterMode.DIALOGUE:
            if self.llm_handler:
                try:
                    response = self.llm_handler(query)
                    return response if response else "Ответ не получен"
                except Exception as e:
                    return f"Ошибка обращения к LLM: {e}"
            return "LLM обработчик не подключен"

        return "Команда не распознана"

    def _extract_app_launch_query(self, text: str) -> Tuple[bool, str]:
        """Check if query is an app launching command and extract app name.

        Args:
            text: Lowercase query string.

        Returns:
            Tuple of (is_app_launch_command, extracted_app_name).
        """
        prefixes = [
            r"^открой\s+",
            r"^запусти\s+",
            r"^open\s+",
            r"^launch\s+",
            r"^старт\s+",
            r"^start\s+",
        ]

        for prefix in prefixes:
            match = re.search(prefix, text)
            if match:
                extracted = text[match.end():].strip()
                if extracted:
                    return True, extracted

        return False, ""

    def _is_match(self, text: str, patterns: list[str], threshold: float = 75.0) -> bool:
        """Check if query text matches any pattern using exact match or fuzzy similarity.

        Args:
            text: Normalized query string.
            patterns: List of candidate command phrases.
            threshold: Fuzzy match score threshold (0-100). Defaults to 75.0.

        Returns:
            True if text matches any pattern, False otherwise.
        """
        for pattern in patterns:
            if text == pattern:
                return True
            # Partial or ratio fuzzy match
            if fuzz.ratio(text, pattern) >= threshold or fuzz.partial_ratio(text, pattern) >= 85.0:
                return True
        return False
