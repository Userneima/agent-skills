#!/usr/bin/env python3
"""Transcribe an already-cut file, writing .srt / .txt / _transcript.json beside it.

The batch script refuses a file that carries the cut mark, which is the right
guard for a second batch run but leaves no way to transcribe a cut that was
rendered on its own. This is that way.

Run it from a fluentflow-local checkout (https://github.com/Userneima/fluentflow-local)
with that project's venv, not the system python -- whisper lives there:

    cd <fluentflow-local>
    .venv/bin/python <this> <cut-file> [model_size]

`model_size` defaults to "medium", which is what is fully cached locally. Ask
for "large-v3" only after checking its cache is complete: a half-downloaded
model sends the run to the HF Hub and it can sit there at 0% indefinitely.
Set HF_HUB_OFFLINE=1 to make that failure loud instead of slow.
"""
import argparse
import importlib.util
import os
import sys
import traceback
from pathlib import Path

# Where the fluentflow-local checkout lives: the directory you run this from,
# unless FLUENTFLOW_PROJECT points somewhere else.
PROJECT = os.environ.get("FLUENTFLOW_PROJECT") or os.getcwd()


def main() -> int:
    if not Path(PROJECT, "scripts", "debreath_batch.py").is_file():
        print(f"{PROJECT} is not a fluentflow-local checkout: run this from one, "
              "or set FLUENTFLOW_PROJECT to its path.", file=sys.stderr)
        return 2
    media = Path(sys.argv[1])
    model_size = sys.argv[2] if len(sys.argv) > 2 else "medium"

    sys.path.insert(0, PROJECT)
    spec = importlib.util.spec_from_file_location(
        "debreath_batch", f"{PROJECT}/scripts/debreath_batch.py")
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)

    try:
        result = batch.transcribe(
            media, argparse.Namespace(model_size=model_size, language=None))
    except Exception:
        traceback.print_exc()
        return 1
    print("DONE", result, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
