# Keep

A private, on-device assistant for macOS — sees, searches, speaks, and acts.
Nothing leaves your machine.

![Keep CLI demo: ingesting a note, then asking a question answered from its contents](assets/demo.gif)

## What Keep does

- **Acts** — calendar events, reminders, mail drafts, file search.
- **Searches** — ask questions about your own notes and documents (`keep ingest <path>`); answers come with citations back to the source.
- **Sees** — describes what's on your screen (`keep see`, or ask out loud).
- **Speaks** — ask by voice, hear the answer back.

All of it runs on Apple's on-device Foundation Models. No API keys, no
network calls, no cloud. You can check that claim yourself — watch a
network monitor (Little Snitch, Activity Monitor's Network tab, `nettop`)
while Keep answers a question with no `[mlx]` extra installed, and you'll
see nothing leave the machine. Privacy you can check beats privacy you have
to trust.

## Install

```
pip install git+https://github.com/rajanshxrma/keep
keep-menubar   # launches the menu bar app
```

or run it without the menu bar shell:

```
keep "what's on my calendar today"
keep ingest ~/Documents/some-notes
keep see
keep --voice
```

### Prebuilt app (unsigned)

A prebuilt `Keep.app` is attached to each [release](https://github.com/rajanshxrma/keep/releases).
It isn't signed — I'm a student, and Apple's $99/year developer program
isn't something I can justify for a free project yet. macOS will say the
app "cannot be verified" or is "damaged" on first launch. That's Gatekeeper
being cautious about unsigned software, not a real problem with the app:

1. Right-click `Keep.app` → **Open** → **Open** (this one-time step is all
   it takes — after that it launches normally like anything else).
2. If macOS still refuses: **System Settings → Privacy & Security**, scroll
   down, click **Open Anyway**.
3. If you're comfortable in a terminal, this does the same thing in one
   line: `xattr -dr com.apple.quarantine Keep.app`

This happens once. Keep never touches the network — you can watch.

## Where Keep came from

Keep merges three projects built and shipped separately: **[private-agent](https://github.com/rajanshxrma/private-agent)**
(the agent core — tool-calling, calendar/reminders/mail, the voice front-end),
**[stacks](https://github.com/rajanshxrma/stacks)** (semantic search over
your own files), **[lantern](https://github.com/rajanshxrma/lantern)**
(on-device screen description). Their repos stay up as the standalone
originals; this is where the three converge into one product.

## Research

Building the agent core surfaced a real, measured finding about on-device
tool-calling and self-computed dates — see
[docs/eval-findings.md](docs/eval-findings.md) for the full numbers and
methodology (63 real trials, no mocks, every created artifact verified then
cleaned up). It's the reason `_dates.py` never lets a model compute its own
relative date.

## Contributing

`contract.md` is the release gate — every testable assertion a release has
to pass. `pip install -e ".[dev]" && pytest` runs the real (no-mock) test
suite; most tests touch the real Calendar/Reminders/Mail apps and the real
on-device model, and clean up after themselves.

## License

MIT
