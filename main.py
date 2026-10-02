"""Main entry point for Desktop Voice Assistant.

Initializes application indexing in a background thread, wires the CommandRouter,
LLMClient, AudioListener, and CustomTkinter GUI, and binds global keyboard shortcuts.
"""

import sys
import threading

from audio.listener import AudioListener
from core.app_finder import AppFinder
from core.llm_client import get_llm_response
from core.router import CommandRouter, RouterMode
from gui.app import launch_gui


def init_app_index_background(app_finder: AppFinder) -> None:
    """Scan Start Menu directories in a background thread to prevent startup latency."""
    try:
        app_finder.scan_directories()
    except Exception:
        pass


def setup_global_hotkeys(app_gui) -> None:
    """Bind global hotkey (e.g. Ctrl+Shift+Space) to toggle microphone state safely."""
    def on_hotkey_pressed():
        if app_gui:
            # Use root.after or direct invocation if main thread
            try:
                app_gui.after(0, app_gui._toggle_mic)
            except Exception:
                pass

    try:
        import keyboard  # type: ignore
        keyboard.add_hotkey("ctrl+shift+space", on_hotkey_pressed)
    except Exception:
        # Hotkey listener missing or requires admin privileges on Windows
        pass


def main() -> None:
    """Main application setup and GUI execution loop."""
    # 1. Instantiate AppFinder and start indexing in background thread
    app_finder = AppFinder()
    index_thread = threading.Thread(
        target=init_app_index_background,
        args=(app_finder,),
        daemon=True,
    )
    index_thread.start()

    # 2. Instantiate CommandRouter with LLM callback
    router = CommandRouter(
        app_finder=app_finder,
        llm_handler=get_llm_response,
        mode=RouterMode.STRICT,
    )

    # 3. Instantiate AudioListener with default model
    listener = AudioListener(
        model_size="base",
        device="cuda",
    )

    # 4. Launch CustomTkinter GUI and bind controls
    app = launch_gui(router=router, listener=listener)

    # 5. Setup global hotkey
    setup_global_hotkeys(app)

    # 6. Run Tkinter mainloop
    app.mainloop()


if __name__ == "__main__":
    main()
