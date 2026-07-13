"""Simple CLI entrypoint for testing the agent without the menu bar shell."""

import sys


def _load_run():
    """Lazily imports keep.agent.run -- it transitively imports
    ChatAppleFoundationModels, which hard-links Apple's FoundationModels
    framework (macOS 26+, Apple Intelligence enabled). Importing it at
    module level meant every command -- including --version and ingest,
    which need no LLM at all -- crashed with a raw dyld traceback on any
    unsupported Mac. Deferred here so only the commands that actually need
    the model pay that cost, with one clean message instead of a traceback."""
    try:
        from keep.agent import run

        return run
    except ImportError as e:
        print(
            "Keep's on-device model isn't available on this Mac "
            "(requires macOS 26+ with Apple Intelligence enabled).\n"
            f"Underlying error: {e}"
        )
        sys.exit(1)


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--version":
        from keep import __version__

        print(__version__)
        return

    if args and args[0] == "--voice":
        from keep.voice import listen, speak

        run = _load_run()
        print("Listening...")
        prompt = listen()
        if not prompt:
            print("Heard nothing.")
            return
        print(f"You said: {prompt}")
        answer = run(prompt)
        print(answer)
        speak(answer)
        return

    if args and args[0] == "ingest":
        from keep.search.ingest import ingest_path

        if len(args) < 2:
            print("Usage: keep ingest <path>")
            sys.exit(1)
        result = ingest_path(args[1])
        print(f"Indexed {len(result['indexed_files'])} file(s), {result['total_chunks']} chunks.")
        if result["skipped_files"]:
            print(f"Skipped {len(result['skipped_files'])} file(s) (empty or unreadable).")
        print(f"Index now has {result['index_size']} total chunks.")
        return

    if args and args[0] == "see":
        from keep.tools.screen import describe_my_screen

        print(describe_my_screen())
        return

    prompt = " ".join(args)
    if not prompt:
        print("Usage: keep <prompt>  |  keep --voice  |  keep ingest <path>  |  keep see")
        sys.exit(1)
    run = _load_run()
    print(run(prompt))


if __name__ == "__main__":
    main()
