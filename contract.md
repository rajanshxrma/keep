# Keep v0.1 — contract

Testable assertions that define "done" for the first release. Every item must
be checked before tagging `v0.1.0`.

1. Clean checkout: `pip install -e ".[dev]" && pytest` — zero failures (all
   three ported test suites: agent/router/conversation/tools/voice, search,
   vision).
2. `keep --version` prints `0.1.0`; `scripts/check_version.py` exits 0
   (pyproject version == `keep.__version__` == built app's
   `CFBundleShortVersionString`).
3. `keep "hello"` (no `[mlx]` extra installed) returns a non-empty answer,
   with zero outbound network connections observed during the call.
4. `keep ingest tests/fixtures/sample.pdf` then asking about its contents
   returns an answer containing a `[sample.pdf, page N]`-style citation.
5. "remind me to X tomorrow" creates a real Reminders.app entry dated
   tomorrow, verified by reading it back via AppleScript.
6. `draft_email` never sends: after asking Keep to email someone, Mail.app
   has a new draft and Sent contains nothing new.
7. Typed "what's on my screen" routes to `describe_my_screen` and the answer
   contains a string actually visible on screen (OCR-grounded, not invented).
8. The screenshot temp file is deleted after every `describe_my_screen`
   call, including when the description step raises.
9. Menu bar: "Ask Keep…" round-trips a question with title states
   🤖→⏳→🤖; a second Ask issued mid-flight is refused with a visible
   notice and does not crash or queue.
10. Voice: "Ask Keep (voice)" speaks the answer aloud and the alert displays
    the transcription verbatim as "You said: …"; a transcription failure
    surfaces the `VoiceUnavailableError` text, never a silent hang. **This
    must pass inside the built .app, not just via `pip install`.**
11. `~/.keep/index.json` exists with mode `0600` after ingest; if a legacy
    `~/.stacks/index.json` exists, its chunks are searchable in Keep without
    re-ingesting.
12. `scripts/build_app.sh` produces `Keep.app` that launches on a second
    (clean) macOS user account with no dev tools, shows menu-bar-only (no
    Dock icon), and passes assertions 3, 7, 9, 10 in-bundle.
13. README renders the demo gif above the fold and contains the unsigned-app
    first-run instructions; no AI-attribution text appears anywhere in the
    repo (`grep -ri "claude\|copilot\|generated with"` — only allowed hits
    are third-party lockfile noise).
