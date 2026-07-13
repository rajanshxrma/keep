"""Menu bar shell for Keep, built with rumps."""

import multiprocessing
import threading

import rumps
from PyObjCTools import AppHelper

_UNAVAILABLE_MESSAGE = (
    "Keep's on-device model isn't available on this Mac "
    "(requires macOS 26+ with Apple Intelligence enabled)."
)


def _new_conversation():
    """Lazily imports/constructs Conversation. keep.conversation imports
    keep.agent, which imports ChatAppleFoundationModels -- that hard-links
    Apple's FoundationModels framework, so on an unsupported Mac the OLD
    module-level `from keep.conversation import Conversation` crashed the
    entire app before rumps.App.run() ever started the event loop: no menu
    bar icon, no dialog, no console for a packaged .app -- a completely
    silent launch failure. Deferred so the icon always appears; unavailable
    is now just a state the Ask handlers check, not a startup crash.
    Returns (conversation_or_None, error_message_or_None)."""
    try:
        from keep.conversation import Conversation

        return Conversation(), None
    except ImportError as e:
        return None, f"{_UNAVAILABLE_MESSAGE}\nUnderlying error: {e}"


class KeepApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Keep", icon=None, title="\U0001f916")
        self._conversation, self._unavailable_reason = _new_conversation()
        # Single-in-flight guard: a queued second ask against a model that
        # can take 6-13s is a footgun (the user gets an answer to a question
        # they've forgotten asking), so a second Ask while busy is refused
        # with a visible notice rather than queued or silently dropped.
        self._busy = False

    def _try_start_busy(self) -> bool:
        if self._busy:
            rumps.notification("Keep", "", "Still working on the last one…")
            return False
        self._busy = True
        return True

    @rumps.clicked("Ask...")
    def ask(self, _sender: rumps.MenuItem) -> None:
        if self._conversation is None:
            rumps.alert(title="Keep", message=self._unavailable_reason)
            return
        if not self._try_start_busy():
            return

        window = rumps.Window(
            message="What do you need?",
            title="Keep",
            default_text="",
            ok="Ask",
            cancel="Cancel",
            dimensions=(320, 60),
        )
        response = window.run()
        if not response.clicked or not response.text.strip():
            self._busy = False
            return

        prompt = response.text.strip()
        self.title = "⏳"

        def _run_and_show() -> None:
            try:
                answer = self._conversation.ask(prompt)
            except Exception as exc:  # surfaced to the user, not swallowed
                answer = f"Something went wrong: {exc}"

            def _show_on_main_thread() -> None:
                # rumps.alert() creates an NSAlert, and AppKit requires all
                # UI to be instantiated on the main thread -- calling it
                # directly from this background worker thread crashes with
                # NSInternalInconsistencyException, silently killing the
                # thread before self.title is ever reset (confirmed by a
                # real crash: the icon stuck on the "thinking" hourglass
                # forever, no alert ever shown).
                rumps.alert(title="Keep", message=answer)
                self.title = "\U0001f916"
                self._busy = False

            AppHelper.callAfter(_show_on_main_thread)

        threading.Thread(target=_run_and_show, daemon=True).start()

    @rumps.clicked("Ask (voice)")
    def ask_voice(self, _sender: rumps.MenuItem) -> None:
        if self._conversation is None:
            rumps.alert(title="Keep", message=self._unavailable_reason)
            return
        if not self._try_start_busy():
            return

        self.title = "\U0001f3a4"  # microphone emoji while listening

        def _run_and_show() -> None:
            from keep.voice import VoiceUnavailableError, listen, speak

            try:
                prompt = listen()
            except VoiceUnavailableError as exc:

                def _show_error() -> None:
                    rumps.alert(title="Keep", message=str(exc))
                    self.title = "\U0001f916"
                    self._busy = False

                AppHelper.callAfter(_show_error)
                return

            if not prompt:

                def _show_nothing_heard() -> None:
                    self.title = "\U0001f916"
                    self._busy = False

                AppHelper.callAfter(_show_nothing_heard)
                return

            def _set_thinking() -> None:
                self.title = "⏳"

            AppHelper.callAfter(_set_thinking)

            try:
                answer = self._conversation.ask(prompt)
            except Exception as exc:  # surfaced to the user, not swallowed
                answer = f"Something went wrong: {exc}"

            def _show_and_speak() -> None:
                rumps.alert(title="Keep", message=f"You said: {prompt}\n\n{answer}")
                self.title = "\U0001f916"
                self._busy = False

            AppHelper.callAfter(_show_and_speak)
            speak(answer)

        threading.Thread(target=_run_and_show, daemon=True).start()

    @rumps.clicked("Describe my screen")
    def describe_screen(self, _sender: rumps.MenuItem) -> None:
        if not self._try_start_busy():
            return

        self.title = "⏳"

        def _run_and_show() -> None:
            from keep.tools.screen import describe_my_screen

            try:
                description = describe_my_screen()
            except Exception as exc:  # surfaced to the user, not swallowed
                description = f"Something went wrong: {exc}"

            def _show_on_main_thread() -> None:
                rumps.alert(title="Keep", message=description)
                self.title = "\U0001f916"
                self._busy = False

            AppHelper.callAfter(_show_on_main_thread)

        threading.Thread(target=_run_and_show, daemon=True).start()

    @rumps.clicked("New Conversation")
    def new_conversation(self, _sender: rumps.MenuItem) -> None:
        # Asks accumulate context (see conversation.py) so follow-ups like
        # "make it 3pm instead" work -- this is the explicit way to drop that
        # context and start clean, since it isn't safe to reset automatically.
        # If the model was never available (see _new_conversation), this is
        # a harmless no-op re-check rather than a crash.
        self._conversation, self._unavailable_reason = _new_conversation()

    @rumps.clicked("Quit")
    def quit_app(self, _sender: rumps.MenuItem) -> None:
        rumps.quit_application()


def main() -> None:
    # Required for voice.py's spawned transcription subprocess (see its
    # module docstring) to work correctly once this app is frozen into a
    # py2app bundle -- without this, a frozen app re-executing itself via
    # multiprocessing's spawn start method can recursively relaunch the
    # whole app instead of just the worker function.
    multiprocessing.freeze_support()
    KeepApp().run()


if __name__ == "__main__":
    main()
