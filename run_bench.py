#!/usr/bin/env python3
"""Run ArNum-TTS: synthesise, listen back, score numeral recovery.

Author: Syamjith NK

Method
------
1. Synthesise each utterance with the TTS under test.
2. Transcribe it with Whisper (large enough to be a fair listener, run locally).
3. Ask ONE question: does the number survive?

Scoring is deliberately narrow. It does not judge accent, prosody or naturalness -
only whether a listener could recover the figure. A system can sound beautiful and
still be unusable for anything with a date or a price in it, and that is exactly the
failure this set is built to catch.

`--engine` is pluggable so the set can be run against other systems; the numbers
published here were produced with fish/s2.1-pro-free.
"""
import argparse
import json
import zlib
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
from arnum import recovered_multi as recovered   # compares VALUES, not spellings - see arnum.py


def synth_apple(text: str, out: Path, _key: str) -> float:
    """macOS `say` with Majed (ar_001). Apple's Arabic voice ships on every iPhone
    and Mac, so how it handles numerals matters to more listeners in this region
    than any API does. Offline, $0, and a fair second data point."""
    import subprocess, tempfile
    t0 = time.time()
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff = tmp.name
    subprocess.run(["say", "-v", "Majed", "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff,
                    "-ar", "16000", "-ac", "1", str(out)], check=True)
    Path(aiff).unlink(missing_ok=True)
    return time.time() - t0


def synth_fish(text: str, out: Path, key: str) -> float:
    body = json.dumps({"text": text, "format": "mp3",
                       "model": "s2.1-pro-free"}).encode()
    req = urllib.request.Request(
        "https://api.fish.audio/v1/tts", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json", "model": "s2.1-pro-free"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        out.write_bytes(r.read())
    return time.time() - t0


# ---------------------------------------------------------------------------
# ArTST / MBZUAI speecht5_tts_clartts_ar
# ---------------------------------------------------------------------------
# SpeechT5 fine-tuned on ClArTTS (Classical Arabic), CC BY-NC 4.0. Unlike fish and
# Apple this one is open weights, so when it fails we can say WHY rather than just
# that it did - see the vocab note in the README.
#
# Two things this engine needs that the API engines do not:
#   * a vocoder (microsoft/speecht5_hifigan) - the model emits a mel spectrogram
#   * a 512-d x-vector speaker embedding; we pin ONE speaker (validation row 105,
#     the index the model card itself uses) so voice identity is held constant
#     across all 45 utterances and cannot confound the numeral comparison.
#
# SpeechT5 keeps its decoder prenet dropout ACTIVE at inference by design, so two
# runs of the same text give different audio. A benchmark that cannot be re-run to
# the same number is not a benchmark, so the seed is derived from the utterance id
# with crc32 - str.__hash__ is salted per process and would NOT reproduce.
_ARTST = {}
_ARTST_SPEAKER_ROW = 105


def _artst_load():
    if _ARTST:
        return _ARTST
    import torch
    from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq

    repo = "MBZUAI/speecht5_tts_clartts_ar"
    _ARTST["proc"] = SpeechT5Processor.from_pretrained(repo)
    _ARTST["model"] = SpeechT5ForTextToSpeech.from_pretrained(repo).eval()
    _ARTST["vocoder"] = SpeechT5HifiGan.from_pretrained("microsoft/speecht5_hifigan").eval()
    pq_path = hf_hub_download("herwoww/arabic_xvector_embeddings",
                              "data/validation-00000-of-00001.parquet", repo_type="dataset")
    row = pq.read_table(pq_path).slice(_ARTST_SPEAKER_ROW, 1).to_pylist()[0]
    _ARTST["spk"] = torch.tensor(row["speaker_embeddings"]).unsqueeze(0)
    _ARTST["torch"] = torch
    return _ARTST


ARTST_TOKENS = HERE / "data/artst_tokens.json"


def _numeral_as_written(row: dict) -> str:
    """The numeral exactly as it appears in the sentence - digits for the two digit
    forms, the longest spelled run for `spelled`."""
    if row["form"] == "spelled":
        return ""                      # words, always in-vocab; nothing to check
    m = re.findall(r"[0-9\u0660-\u0669]+", row["text"])
    return max(m, key=len) if m else ""


def artst_token_report(text: str, numeral: str = "") -> dict:
    """What the model actually receives. The tokenizer is character-level with an
    87-entry vocab, so a character it does not know is not mispronounced - it is
    replaced by <unk> and the information is gone before synthesis starts.

    Written to disk during the synth pass so the scoring pass, which runs in a venv
    with whisper but no torch, can attach it without loading the model."""
    from transformers import SpeechT5Processor
    tk = SpeechT5Processor.from_pretrained("MBZUAI/speecht5_tts_clartts_ar").tokenizer
    ids = tk(text)["input_ids"]
    seen = tk.decode(ids, skip_special_tokens=True)
    # Every sentence in the set ends in ".", which is ALSO outside the vocab, so a
    # raw unk count does not isolate the numeral. Ask the question that matters
    # directly: did the numeral, exactly as written, reach the model at all?
    return {"n_unk": sum(1 for i in ids if i == tk.unk_token_id),
            "numeral_reached_model": (numeral in seen) if numeral else None,
            "seen_by_model": seen}


def synth_artst(text: str, out: Path, _key: str, seed: int = 0) -> float:
    m = _artst_load()
    torch = m["torch"]
    t0 = time.time()
    torch.manual_seed(seed)
    inputs = m["proc"](text=text, return_tensors="pt")
    with torch.no_grad():
        wav = m["model"].generate_speech(inputs["input_ids"], m["spk"], vocoder=m["vocoder"])
    _write_wav16(out, wav.numpy(), 16000)
    return time.time() - t0


def _write_wav16(out: Path, samples, rate: int) -> None:
    """16-bit mono PCM via the stdlib - avoids a soundfile/libsndfile dependency
    for what is three lines of work."""
    import wave, numpy as np
    x = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((x * 32767.0).astype("<i2").tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="fish")
    ap.add_argument("--key-file", default=str(Path.home() / "jarvis/.credentials/fish_audio_key"))
    ap.add_argument("--whisper", default="small")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--synth-only", action="store_true",
                    help="synthesise and stop - lets the TTS run in a venv that has "
                         "torch while the ASR pass runs in the one that has whisper")
    a = ap.parse_args()

    rows = [json.loads(l) for l in (HERE / "data/sentences.jsonl").read_text().splitlines() if l.strip()]
    if a.limit:
        rows = rows[:a.limit]
    key = Path(a.key_file).read_text().strip() if Path(a.key_file).exists() else ""
    audio = HERE / "audio"; audio.mkdir(exist_ok=True)

    asr = None
    if not a.synth_only:
        from faster_whisper import WhisperModel
        asr = WhisperModel(a.whisper, device="cpu", compute_type="int8")

    SYNTH = {"apple": synth_apple, "fish": synth_fish, "artst": synth_artst}
    if a.engine not in SYNTH:
        raise SystemExit(f"unknown engine {a.engine!r}; have {sorted(SYNTH)}")

    tok_cache = json.loads(ARTST_TOKENS.read_text()) if (
        a.engine == "artst" and ARTST_TOKENS.exists() and not a.synth_only) else {}

    out = []
    for i, r in enumerate(rows, 1):
        ext = "mp3" if a.engine == "fish" else "wav"
        f = audio / f"{a.engine}__{r['id']}__{r['form']}.{ext}"
        if not f.exists():
            if a.engine == "artst":
                synth_artst(r["text"], f, key, seed=zlib.crc32((r["id"] + "__" + r["form"]).encode()))
            else:
                SYNTH[a.engine](r["text"], f, key)
        if a.synth_only:
            if a.engine == "artst":
                tok_cache[f"{r['id']}__{r['form']}"] = artst_token_report(
                    r["text"], _numeral_as_written(r))
            print(f"  [{i}/{len(rows)}] synth {f.name}")
            continue
        segs, _ = asr.transcribe(str(f), language="ar", beam_size=5)
        heard = " ".join(s.text.strip() for s in segs).strip()
        ok = recovered(r["expect"], heard)
        rec = {**r, "heard": heard, "recovered": ok}
        rec.update(tok_cache.get(f"{r['id']}__{r['form']}", {}))
        out.append(rec)
        print(f"  [{i}/{len(rows)}] {r['id']:14} {r['form']:13} {'OK ' if ok else 'LOST'}  {heard[:60]}")

    if a.synth_only:
        if a.engine == "artst":
            prev = json.loads(ARTST_TOKENS.read_text()) if ARTST_TOKENS.exists() else {}
            prev.update(tok_cache)          # merge: a --limit run must not truncate it
            ARTST_TOKENS.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
            print(f"  wrote {ARTST_TOKENS.name}")
        print(f"\nsynthesised {len(rows)} utterances into {audio}/ - now run the "
              f"same command without --synth-only in a venv that has faster_whisper")
        return

    (HERE / f"results_{a.engine}.jsonl").write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n")

    print("\nnumeral recovery by form")
    for form in ("western", "arabic_indic", "spelled"):
        sub = [o for o in out if o["form"] == form]
        if sub:
            n = sum(o["recovered"] for o in sub)
            print(f"  {form:14} {n}/{len(sub)}  ({100*n/len(sub):.0f}%)")


if __name__ == "__main__":
    main()
