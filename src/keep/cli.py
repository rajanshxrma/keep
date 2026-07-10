"""Simple CLI entrypoint for testing the agent without the menu bar shell."""

import sys

from keep.agent import run


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--version":
        from keep import __version__

        print(__version__)
        return

    if args and args[0] == "--voice":
        from keep.voice import listen, speak

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

    prompt = " ".join(args)
    if not prompt:
        print("Usage: keep <prompt>  |  keep --voice  |  keep ingest <path>")
        sys.exit(1)
    print(run(prompt))


if __name__ == "__main__":
    main()
