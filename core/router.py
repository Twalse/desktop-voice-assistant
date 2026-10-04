"""Command Router module for multi-language voice command dispatching.

Supports Russian and English phrases, wake word activation, phonetic normalization,
pattern extraction, parametric commands, fuzzy matching, and two operation modes:
Strict/Scripted mode and Dialogue/LLM mode.
"""

import re
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from core import system_actions
from core.app_finder import AppFinder, launch_app

# --- Wake Word Variations ---
DEFAULT_WAKE_WORDS: List[str] = [
    "ассистент",
    "асистент",
    "assistant",
    "джарвис",
]

# --- Phonetic Replacement & Alias Dictionaries ---
PHONETIC_REPLACEMENTS: Dict[str, str] = {
    "стин": "steam",
    "с тима": "steam",
    "с тим": "steam",
    "с тем": "steam",
    "фл студио": "FL Studio",
    "кс 2": "CS2",
    "кс2": "CS2",
    "кэс": "CS2",
    "раст": "Rust",
    "осу": "osu!",
    "осо": "osu!",
    "кап кут": "CapCut",
    "капкут": "CapCut",
    "блокбенч": "Blockbench",
    "оуэн тим": "открой steam",
    "а у пэн стоим": "открой steam",
    "дискорт": "discord",
    "хром": "chrome",
    "браузер": "chrome",
    "калькулятор": "calculator",
    "блокнот": "notepad",
    "вижл студио": "Visual Studio Code",
    "вс код": "Visual Studio Code",
    "фотошоп": "Adobe Photoshop",
    "стим": "Steam",
}

# Explicit App Aliases mapping extracted spoken app terms to exact binary/shortcut names
APP_ALIASES: Dict[str, str] = {
    "фл студио": "FL Studio",
    "кап кут": "CapCut",
    "капкут": "CapCut",
    "кс 2": "CS2",
    "кс2": "CS2",
    "кэс": "CS2",
    "раст": "Rust",
    "осу": "osu!",
    "осо": "osu!",
    "блокбенч": "Blockbench",
    "вижл студио": "Visual Studio Code",
    "вс код": "Visual Studio Code",
    "фотошоп": "Adobe Photoshop",
    "дискорд": "Discord",
    "стим": "Steam",
    "steam": "Steam",
    "браузер": "Chrome",
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
        wake_words: Optional[List[str]] = None,
        require_wake_word: bool = True,
        phonetic_replacements: Optional[Dict[str, str]] = None,
        app_aliases: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize CommandRouter.

        Args:
            app_finder: AppFinder instance. Defaults to new instance or module level handler.
            llm_handler: Optional callback function for LLM/Dialogue processing.
            mode: Operating mode (RouterMode.STRICT or RouterMode.DIALOGUE).
            wake_words: List of wake word activation triggers. Defaults to DEFAULT_WAKE_WORDS.
            require_wake_word: If True, ignores input unless it starts with a wake word.
            phonetic_replacements: Dictionary of phonetic corrections. Defaults to PHONETIC_REPLACEMENTS.
            app_aliases: Dictionary mapping spoken app names to canonical app names. Defaults to APP_ALIASES.
        """
        self.app_finder = app_finder
        self.llm_handler = llm_handler
        self.mode = mode
        self.wake_words = wake_words if wake_words is not None else DEFAULT_WAKE_WORDS
        self.require_wake_word = require_wake_word
        self.phonetic_replacements = phonetic_replacements if phonetic_replacements is not None else PHONETIC_REPLACEMENTS
        self.app_aliases = app_aliases if app_aliases is not None else APP_ALIASES

    def set_mode(self, mode: RouterMode) -> None:
        """Change current operation mode.

        Args:
            mode: RouterMode.STRICT or RouterMode.DIALOGUE.
        """
        self.mode = mode

    def _strip_wake_word(self, text: str) -> Tuple[bool, str]:
        """Check for wake word at beginning of phrase and strip it.

        Args:
            text: Lowercase input string.

        Returns:
            Tuple of (wake_word_found, stripped_text).
        """
        if not self.require_wake_word:
            return True, text

        normalized_input = text.strip().lower()

        for wake_word in self.wake_words:
            pattern = re.compile(r"^" + re.escape(wake_word.lower()) + r"[\s,.:!]*", re.IGNORECASE)
            if pattern.search(normalized_input):
                stripped = pattern.sub("", normalized_input).strip()
                return True, stripped

        return False, text

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

        raw_text = query.strip().lower()

        # Check and strip wake word
        wake_found, stripped_text = self._strip_wake_word(raw_text)
        if not wake_found:
            return "Игнорировано (нет ключевого слова)"

        # Apply phonetic normalization pre-processing on stripped text
        text = self._normalize_text(stripped_text)
        if not text:
            return "Слушаю..."

        # 1. Parametric Volume Commands
        vol_match = re.search(r"(?:поставь|установи|сделай)?\s*громкость\s*(?:на)?\s*(\d{1,3})\s*(?:процентов|процента|%)?", text)
        if vol_match:
            try:
                target_level = int(vol_match.group(1))
                system_actions.set_volume(target_level)
                return f"Громкость установлена на {target_level}%"
            except Exception:
                pass

        # 2. Web Search Commands
        search_match = re.search(r"^(?:найди в интернете|загугли|поищи|найди|search)\s+(.+)", text)
        if search_match:
            search_query = search_match.group(1).strip()
            if search_query:
                system_actions.search_web(search_query)
                return f"Ищу в интернете: '{search_query}'"

        # 3. App Launching Patterns
        app_match, extracted_name = self._extract_app_launch_query(text)
        if app_match:
            # Check explicit app aliases
            app_name = self.app_aliases.get(extracted_name.lower(), extracted_name)

            launched = False
            if self.app_finder:
                launched = self.app_finder.launch_app(app_name)
            else:
                launched = launch_app(app_name)

            if launched:
                return f"Запускаю {app_name.capitalize()}"
            else:
                return f"Приложение '{app_name}' не найдено"

        # 4. System Commands (Power, Screenshots)
        if self._is_match(text, ["выключи компьютер", "выключи пк", "завершение работы", "выключить пк", "shutdown"]):
            system_actions.shutdown_pc()
            return "Завершение работы ПК"

        if self._is_match(text, ["перезагрузи", "рестарт", "перезагрузи компьютер", "restart"]):
            system_actions.restart_pc()
            return "Перезагрузка ПК"

        if self._is_match(text, ["сделай скриншот", "сделай снимок экрана", "скриншот", "screenshot"]):
            system_actions.take_screenshot()
            return "Скриншот сохранен"

        # 5. Time/Date Info Queries
        if self._is_match(text, ["сколько времени", "который час", "какое время", "what time is it", "what's the time"]):
            current_time = system_actions.get_current_time()
            return f"Сейчас {current_time}"

        if self._is_match(text, ["какое число", "какой сегодня день", "дата", "what date is it", "today's date"]):
            current_date = system_actions.get_current_date()
            return f"Сегодня {current_date}"

        # 6. Media Controls
        if self._is_match(text, ["пауза", "плей", "останови видео", "воспроизведение", "pause", "resume", "play"]):
            system_actions.media_play_pause()
            return "Воспроизведение/Пауза"

        if self._is_match(text, ["следующий трек", "следующая песня", "дальше", "next", "next track"]):
            system_actions.media_next()
            return "Следующий трек"

        if self._is_match(text, ["предыдущий трек", "назад", "prev", "previous track"]):
            system_actions.media_prev()
            return "Предыдущий трек"

        # 7. Step Volume Controls
        if self._is_match(text, ["громче", "сделай громче", "увеличь звук", "volume up", "louder"]):
            system_actions.volume_up()
            return "Громкость увеличена"

        if self._is_match(text, ["тише", "сделай тише", "уменьши звук", "volume down", "quieter"]):
            system_actions.volume_down()
            return "Громкость уменьшена"

        if self._is_match(text, ["выключи звук", "без звука", "мут", "mute", "unmute"]):
            system_actions.mute()
            return "Звук переключен"

        # 8. Window Management
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

        # 9. Mode 2: Dialogue / LLM fallback
        if self.mode == RouterMode.DIALOGUE:
            if self.llm_handler:
                try:
                    response = self.llm_handler(stripped_text)
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
