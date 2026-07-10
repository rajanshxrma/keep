"""Simple CLI entrypoint for testing the agent without the menu bar shell."""

import sys

from keep.agent import run


def main() -> None:
    args = sys.argv[1:]
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

    prompt = " ".join(args)
    if not prompt:
        print("Usage: keep <prompt>  |  keep --voice")
        sys.exit(1)
    print(run(prompt))


if __name__ == "__main__":
    main()
