#!/usr/bin/env python3
"""Control: does ArTST emit ANY audio for a Western digit run?

Author: Syamjith NK

Synthesise each `western` sentence twice - as written, and with the numeral deleted.
If the model speaks the number, the first must be audibly longer. If the durations
match, the digits produce nothing at all, and the 0/15 is a deletion rather than a
mispronunciation. Independent of Whisper.
"""
import json, re, sys, wave, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_bench as rb
ctrl = HERE / "audio_control"; ctrl.mkdir(exist_ok=True)
rows = [json.loads(l) for l in (HERE/"data/sentences.jsonl").read_text().splitlines() if l.strip()]

def dur(p):
    with wave.open(str(p)) as w: return w.getnframes()/w.getframerate()

print(f"{'id':14} {'with digits':>12} {'digits removed':>15} {'delta':>8}")
out=[]
for r in [x for x in rows if x["form"]=="western"]:
    stripped = re.sub(r"\s*[0-9٠-٩][0-9٠-٩.,:٫]*\s*", " ", r["text"]).strip()
    seed = zlib.crc32((r["id"]+"__"+r["form"]).encode())
    a = HERE/"audio"/f"artst__{r['id']}__western.wav"
    b = ctrl/f"artst__{r['id']}__western_NODIGITS.wav"
    if not b.exists(): rb.synth_artst(stripped, b, "", seed=seed)
    da, db = dur(a), dur(b)
    out.append({"id": r["id"], "with_digits_s": round(da,3), "no_digits_s": round(db,3),
                "delta_s": round(da-db,3), "stripped_text": stripped})
    print(f"{r['id']:14} {da:11.2f}s {db:14.2f}s {da-db:+7.2f}s")

d=[o["delta_s"] for o in out]
print(f"\nmean delta {sum(d)/len(d):+.2f}s   min {min(d):+.2f}s   max {max(d):+.2f}s")
(HERE/"data/artst_duration_control.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
