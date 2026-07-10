# Keep

A private, on-device assistant for macOS — sees, searches, speaks, and acts.
Nothing leaves your machine.

*This README fills in as each phase lands (demo gif, install instructions,
provenance, benchmarks). Full contract at [contract.md](contract.md).*

## What Keep does

- **Acts** — calendar events, reminders, mail drafts, file search.
- **Searches** — ask questions about your own notes and documents; answers
  come with citations back to the source.
- **Sees** — describes what's on your screen.
- **Speaks** — ask out loud, hear the answer back.

All of it runs on Apple's on-device Foundation Models. No API keys, no
network calls, no cloud.

## Where Keep came from

Keep merges three projects built and shipped separately: **private-agent**
(the agent core), **stacks** (semantic search), **lantern** (screen
description). Their repos stay up as the standalone originals.

## Install

```
pip install git+https://github.com/rajanshxrma/keep
```

(A signed installer isn't available yet — see the first-run notes below
once the packaged `.app` ships.)

## License

MIT
