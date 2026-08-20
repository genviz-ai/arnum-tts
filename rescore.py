#!/usr/bin/env python3
"""Re-score stored transcripts. No synthesis, no ASR - pure.

Author: Syamjith NK

The benchmark's measurement chain is TTS -> Whisper -> a number parser, and only the
last link is ours. When the parser is corrected the honest thing to do is re-derive
every published number from the transcripts that were already recorded, rather than
re-running the engines - re-synthesising would change the audio underneath the change
and make it impossible to say which of the two moved the score.

So this reads `heard` out of each results file, re-runs the scorer over it, and prints
every row that flipped.

    python rescore.py              # dry run, prints the diff
    python rescore.py --write      # rewrite the results files in place

GUARD: the digit forms (`western`, `arabic_indic`) must never move under a
spelled-form scorer fix. If one does, this exits non-zero and writes nothing.
"""
import argparse, json
from pathlib import Path

HERE = Path(__file__).parent
from arnum import recovered_multi as recovered

FORMS = ("western", "arabic_indic", "spelled")
DIGIT_FORMS = ("western", "arabic_indic")

ap = argparse.ArgumentParser()
ap.add_argument("--engines", nargs="*", default=["fish", "apple", "artst"])
ap.add_argument("--file", action="append", default=[],
                help="any other results-shaped jsonl, e.g. the whisper-medium control")
ap.add_argument("--write", action="store_true")
a = ap.parse_args()

failed_guard = []
pending = []

for target in [HERE / f"results_{e}.jsonl" for e in a.engines] + [Path(f) for f in a.file]:
    eng = target.stem.replace("results_", "")
    path = target
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    was = {id(r): bool(r["recovered"]) for r in rows}
    flips = []
    for r in rows:
        r["recovered"] = recovered(r["expect"], r["heard"])
        if r["recovered"] != was[id(r)]:
            flips.append(r)
            if r["form"] in DIGIT_FORMS:
                failed_guard.append(f"{eng}/{r['id']}/{r['form']}")

    print(f"\n=== {eng}")
    for form in FORMS:
        sub = [r for r in rows if r["form"] == form]
        before = sum(was[id(r)] for r in sub)
        now = sum(r["recovered"] for r in sub)
        mark = "" if before == now else "   <-- CHANGED"
        print(f"  {form:14} {before}/{len(sub)} -> {now}/{len(sub)}"
              f"  ({100*now/len(sub):.0f}%){mark}")
    b = sum(was.values()); n = sum(r["recovered"] for r in rows)
    print(f"  {'overall':14} {b}/{len(rows)} -> {n}/{len(rows)}  ({100*n/len(rows):.0f}%)")
    for r in flips:
        print(f"    {'LOST->OK' if r['recovered'] else 'OK->LOST'}  {r['id']:14}"
              f" {r['form']:13} exp={r['expect']:9} | {r['heard'][:80]}")
    pending.append((path, rows))

if failed_guard:
    raise SystemExit(f"\nSTOP: a digit form moved ({', '.join(failed_guard)}). "
                     "Nothing written - a spelled-form fix must not touch these.")

if a.write:
    for path, rows in pending:
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        print(f"\n  wrote {path.name}")
else:
    print("\n(dry run - pass --write to update the results files)")
