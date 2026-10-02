"""System actions module for controlling Windows system parameters, windows, media, and input primitives.

This module provides volume controls, media controls, window management using pygetwindow,
date/time utilities in Russian, and cursor/keyboard primitives using pyautogui.
"""

import datetime
import locale
import sys
from typing import Any, List, Optional

# Win32 Virtual Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xCD


# --- Helper for Virtual Keys via ctypes ---
def _send_vk(vk_code: int) -> bool:
    """Send a virtual key event via ctypes keybd_event on Windows."""
    if sys.platform == "win32":
        try:
            import ctypes
            KEYEVENTF_KEYUP = 0x0002
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
            return True
        except Exception:
            return False
    return False


# --- Volume Controls ---
def volume_up(step: float = 0.05) -> bool:
    """Increase system volume.

    Attempts to use pycaw if available, falling back to VK_VOLUME_UP virtual key.

    Args:
        step: Volume increase step between 0.0 and 1.0 (for pycaw). Defaults to 0.05.

    Returns:
        True if volume action succeeded, False otherwise.
    """
    if sys.platform == "win32":
        try:
            from comtypes import CLSCTX_ALL  # type: ignore
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            current_vol = volume.GetMasterVolumeLevelScalar()
            new_vol = min(1.0, current_vol + step)
            volume.SetMasterVolumeLevelScalar(new_vol, None)
            return True
        except Exception:
            pass

    # Fallback to VK_VOLUME_UP
    return _send_vk(VK_VOLUME_UP)


def volume_down(step: float = 0.05) -> bool:
    """Decrease system volume.

    Attempts to use pycaw if available, falling back to VK_VOLUME_DOWN virtual key.

    Args:
        step: Volume decrease step between 0.0 and 1.0 (for pycaw). Defaults to 0.05.

    Returns:
        True if volume action succeeded, False otherwise.
    """
    if sys.platform == "win32":
        try:
            from comtypes import CLSCTX_ALL  # type: ignore
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            current_vol = volume.GetMasterVolumeLevelScalar()
            new_vol = max(0.0, current_vol - step)
            volume.SetMasterVolumeLevelScalar(new_vol, None)
            return True
        except Exception:
            pass

    # Fallback to VK_VOLUME_DOWN
    return _send_vk(VK_VOLUME_DOWN)


def mute(status: Optional[bool] = None) -> bool:
    """Toggle or set system volume mute status.

    Args:
        status: If True, mutes. If False, unmutes. If None, toggles mute state.

    Returns:
        True if mute operation succeeded, False otherwise.
    """
    if sys.platform == "win32":
        try:
            from comtypes import CLSCTX_ALL  # type: ignore
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            if status is None:
                current_mute = volume.GetMute()
                volume.SetMute(not current_mute, None)
            else:
                volume.SetMute(bool(status), None)
            return True
        except Exception:
            pass

    # Fallback to VK_VOLUME_MUTE
    return _send_vk(VK_VOLUME_MUTE)


# --- Media Controls ---
def media_play_pause() -> bool:
    """Trigger media play/pause action.

    Returns:
        True if media play/pause key command was sent successfully.
    """
    if _send_vk(VK_MEDIA_PLAY_PAUSE):
        return True
    try:
        import pyautogui
        pyautogui.press("playpause")
        return True
    except Exception:
        return False


def media_next() -> bool:
    """Trigger media next track action.

    Returns:
        True if media next track key command was sent successfully.
    """
    if _send_vk(VK_MEDIA_NEXT_TRACK):
        return True
    try:
        import pyautogui
        pyautogui.press("nexttrack")
        return True
    except Exception:
        return False


def media_prev() -> bool:
    """Trigger media previous track action.

    Returns:
        True if media previous track key command was sent successfully.
    """
    if _send_vk(VK_MEDIA_PREV_TRACK):
        return True
    try:
        import pyautogui
        pyautogui.press("prevtrack")
        return True
    except Exception:
        return False


# --- Window Management ---
def get_open_windows() -> List[str]:
    """Get list of titles of all currently open and visible windows.

    Returns:
        List of visible non-empty window title strings.
    """
    try:
        import pygetwindow as gw  # type: ignore

        windows = gw.getAllWindows()
        titles: List[str] = []
        for win in windows:
            # Check for visible windows with non-empty titles
            if hasattr(win, "title") and win.title:
                is_visible = getattr(win, "visible", True)
                if is_visible and win.title.strip():
                    titles.append(win.title.strip())
        return titles
    except Exception:
        return []


def minimize_active_window() -> bool:
    """Minimize the currently active window.

    Returns:
        True if active window was minimized or Win+Down was sent, False on error.
    """
    try:
        import pygetwindow as gw  # type: ignore

        active = gw.getActiveWindow()
        if active:
            active.minimize()
            return True
    except Exception:
        pass

    try:
        import pyautogui
        pyautogui.hotkey("win", "down")
        return True
    except Exception:
        return False


def maximize_active_window() -> bool:
    """Maximize the currently active window.

    Returns:
        True if active window was maximized or Win+Up was sent, False on error.
    """
    try:
        import pygetwindow as gw  # type: ignore

        active = gw.getActiveWindow()
        if active:
            active.maximize()
            return True
    except Exception:
        pass

    try:
        import pyautogui
        pyautogui.hotkey("win", "up")
        return True
    except Exception:
        return False


def close_active_window() -> bool:
    """Close the currently active window using Alt+F4.

    Returns:
        True if close hotkey command was sent, False on error.
    """
    try:
        import pygetwindow as gw  # type: ignore

        active = gw.getActiveWindow()
        if active and hasattr(active, "close"):
            try:
                active.close()
                return True
            except Exception:
                pass
    except Exception:
        pass

    try:
        import pyautogui
        pyautogui.hotkey("alt", "f4")
        return True
    except Exception:
        return False


# --- Basic Utility Queries ---
MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

DAYS_RU = {
    0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг",
    4: "пятница", 5: "суббота", 6: "воскресенье"
}


def get_current_time() -> str:
    """Get current system time formatted in Russian (e.g., '14:30').

    Returns:
        Formatted time string.
    """
    now = datetime.datetime.now()
    return now.strftime("%H:%M")


def get_current_date() -> str:
    """Get current system date formatted in Russian (e.g., '12 октября 2023, четверг').

    Returns:
        Formatted Russian date string.
    """
    now = datetime.datetime.now()
    day = now.day
    month = MONTHS_RU.get(now.month, "")
    year = now.year
    weekday = DAYS_RU.get(now.weekday(), "")
    return f"{day} {month} {year} г., {weekday}"


# --- Cursor and Keyboard Primitives ---
def move_cursor(x: int, y: int) -> bool:
    """Move cursor to screen coordinates (x, y).

    Args:
        x: Horizontal coordinate in pixels.
        y: Vertical coordinate in pixels.

    Returns:
        True if cursor was moved successfully, False on error.
    """
    try:
        import pyautogui
        pyautogui.moveTo(x, y)
        return True
    except Exception:
        return False


def click(button: str = "left") -> bool:
    """Click mouse button at current cursor position.

    Args:
        button: Mouse button to click ('left', 'right', 'middle'). Defaults to 'left'.

    Returns:
        True if click executed successfully, False on error.
    """
    try:
        import pyautogui
        pyautogui.click(button=button)
        return True
    except Exception:
        return False


def press_hotkey(*keys: str) -> bool:
    """Press a key combination or hotkey.

    Args:
        *keys: Key names as expected by pyautogui (e.g., 'ctrl', 'c').

    Returns:
        True if hotkey was pressed successfully, False on error.
    """
    if not keys:
        return False
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
        return True
    except Exception:
        return False
