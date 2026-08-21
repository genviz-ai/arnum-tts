---
license: cc-by-4.0
language:
  - ar
task_categories:
  - text-to-speech
tags:
  - arabic
  - tts
  - evaluation
  - numerals
  - speech-synthesis
  - benchmark
  - rtl
  - arabic-nlp
  - reproducible
  - arabic-indic-numerals
  - normalization
pretty_name: ArNum-TTS
size_categories:
  - n<1K
configs:
  - config_name: sentences
    data_files:
      - split: test
        path: data/sentences.jsonl
  - config_name: results_fish
    data_files:
      - split: test
        path: results_fish.jsonl
  - config_name: results_apple
    data_files:
      - split: test
        path: results_apple.jsonl
  - config_name: results_artst
    data_files:
      - split: test
        path: results_artst.jsonl
---

# ArNum-TTS — does the number survive?

**Author:** Syamjith NK
**License:** CC BY 4.0 (data) · MIT (code)

A small evaluation set for one narrow, practical question: **when an Arabic
text-to-speech system reads a sentence containing a number, can a listener recover
the number?**

Not naturalness. Not accent. Not prosody. A voice can be beautiful and still be
unusable for anything containing a date, a price or a percentage — and that failure
is invisible in every TTS demo, because demos do not contain numbers.

Write-up: **[One of these reads ٢٠٢٦ as a year. The other reads it as noise.](https://syamjithnk.com/arabic-tts-numerals)**

## Why it exists

Arabic is written with two numeral systems. The same year is `2026` or `٢٠٢٦`, and
both are correct Arabic. Nothing in the literature says whether TTS systems handle
them equally, and every Arabic deliverable — a government awareness film, a bank's
IVR, a news read — is full of them.

## Design

15 sentences × 3 numeral forms = **45 utterances**. Each sentence is identical across
the three forms except for how the number is written:

| form | example |
|---|---|
| `western` | في عام **2026** |
| `arabic_indic` | في عام **٢٠٢٦** |
| `spelled` | في عام **ألفين وستة وعشرين** |

Holding the sentence constant is the whole point: any difference in score is caused by
numeral form and nothing else. Categories are the ones that break real work — years,
percentages, decimals, currency, times, dates, phone numbers, ordinals, ranges, large
counts.

## Results — three engines

| numeral form | fish `s2.1-pro-free` | Apple `Majed` (ar_001) | ArTST `speecht5_tts_clartts_ar` |
|---|---|---|---|
| western `2026` | 11/15 (73%) | 12/15 (80%) | **0/15 (0%)** |
| arabic_indic `٢٠٢٦` | **1/15 (7%)** | **12/15 (80%)** | **0/15 (0%)** |
| spelled `ألفين وستة وعشرين` | 13/15 (87%) | 9/15 (60%) | 4/15 (27%) |
| overall | 25/45 (56%) | 33/45 (73%) | 4/45 (9%) |

fish + Apple measured 2026-08-18 · ArTST added 2026-08-20 · **spelled-form figures
revised 2026-08-20 by a scorer correction — see the [Changelog](#changelog).**

Three engines, three different behaviours on the *same* sentences:

**Apple normalises the numeral before speaking it** and is therefore form-agnostic —
identical 80% on `2026` and `٢٠٢٦`. It is the existence proof that this is solvable.

**fish handles Western digits and collapses on Arabic-Indic** — 73% to 7% on sentences
that differ in nothing but how the number is typed. The failures are not
mispronunciations but noise: `٢٠٢٦` in a date came back as `تخاناتر`, `٢:٤٥` as
`انفافس اسم مفاعس`.

**ArTST speaks neither digit form** — 0/30. And because it is open weights, the failure
can be explained rather than just observed: the Arabic-Indic digits `٠-٩` are **absent
from its 87-token vocabulary**, so `٢٠٢٦` collapses to a single `<unk>` and is deleted
before synthesis starts. Western digits *are* in the vocabulary, tokenise cleanly, and
still produce ~0.19 s of audio where the same model spends 1.41 s saying the number
spelled out. Two different mechanisms, one outcome.

Full analysis, including a Whisper-free duration control:
**[FINDING_artst_numerals.md](./FINDING_artst_numerals.md)**.

**Practical rule this yields:** normalise every numeral before it reaches an Arabic TTS
engine — to Western digits for fish, and all the way to Arabic *words* for ArTST.

## What this benchmark does NOT yet establish

Stated plainly, because the absolute percentages above are weaker than the comparison:

- **The measurement chain is TTS → Whisper → a number parser**, and an error anywhere
  in it is charged to the TTS. Three rounds of parser fixes moved the Western scores
  from 47% to 73–80% without a single audio file changing, which shows how much of the
  early "failure" was the harness. `arnum.py` now handles split hundreds, ordinals
  (Arabic says times and dates ordinally), spelling variants and summed times — the
  ordinal gap in particular was silently penalising Apple for speaking correctly.
- **The relative gap is robust** — 7% vs 80% cannot be produced by transcription noise,
  and the Arabic-Indic transcripts are visibly gibberish rather than near-misses.
- **Three engines** have been run (fish, Apple, ArTST). The set is engine-agnostic
  (`--engine`) and still needs ElevenLabs, Azure and Google before any claim about
  Arabic TTS *as a field* is made.
- **ArTST is being run off-domain.** It is fine-tuned on ClArTTS (Classical Arabic) and
  this set is Modern Standard Arabic news copy, which is why its spelled-form baseline
  is only 27%. Its numeral-specific effect is the drop from 27% to 0%, not the whole
  of the 0% — see the finding for why that distinction matters.
- No human listening pass yet. A 45-item set should be human-verified before the
  absolute numbers are quoted anywhere.
- **The scorer gaps listed here on 2026-08-20 have since been fixed and the affected
  numbers revised** — see the [Changelog](#changelog). What replaces them is a narrower
  gap: the clock rules are gated on the transcript literally containing `ساعة`, so when
  an engine's output is garbled enough that Whisper writes `الساعدة`, a correct
  half-past reading is still scored LOST. That is deliberate — `نصف` means "half" in
  any context and reading it as 30 unconditionally would be a worse bug than the one
  it fixes.

## Files

| | |
|---|---|
| `build_set.py` | generates `data/sentences.jsonl` |
| `run_bench.py` | synthesise → transcribe → score |
| `arnum.py` | Arabic number-word → value normaliser |
| `test_arnum.py` | 34 tests for the normaliser |
| `rescore.py` | re-derives every result from the stored transcripts, no re-synthesis |
| `artst_duration_control.py` | Whisper-free check that ArTST emits no audio for digits |
| `results_{fish,apple,artst}.jsonl` | per-utterance results, one file per engine |
| `data/artst_tokens.json` | what ArTST's tokenizer actually received per utterance |

`arnum.py` exists because the first version of this benchmark scored only digit
strings, and therefore marked correct spoken Arabic (`ستمائة وأربعة وسبعون`) as a
failure. That bug understated every form. It is called out here because a benchmark
whose scorer is wrong is worse than no benchmark.

## Changelog

### 2026-08-20 — scorer correction, `spelled` form only

Four gaps in `arnum.py` were charging correct speech as a failure. They were published
as known limitations before they were fixed; they are now fixed, and every result has
been **re-derived from the transcripts already stored in the results files** — no audio
was re-synthesised, so nothing moved underneath the change. `rescore.py` reproduces
this, and refuses to write if a digit-form score moves.

What was wrong:

1. **Fractions of an hour were absent.** `النصف` and `الربع` were in no dictionary, so
   `6:30` spoken correctly as `الساعة السادسة والنصف` parsed as `{6}` and scored LOST.
   Now read as 30 and 15 — **only when the sentence contains `ساعة`**, because `نصف` is
   "half" in every other context.
2. **Tanween left a trailing alef.** The diacritic was stripped but not the alef under
   it, so `سبعونًا` missed the tens table and `674` parsed as `604`. Lookup now retries
   without one trailing `ا`.
3. **Ordinals written as two words could not match.** `الثانية عشرة` (twelfth) can only
   live in a dictionary pre-joined, so the pair is now joined before lookup. This also
   fixes `الحادية عشرة`, which used to read as 11 + 10 = 21.
4. **The group never closed after a clock hour.** `الثانية عشرة وخمسة وأربعين`
   accumulated 12+5+40 into a single `57`. The hour now closes the group, so the hour
   and the minutes are separate values. Gated the same way, which is what keeps the
   date ordinal `الثامن والعشرين` equal to 28 rather than `{8, 20}`.

Old → new:

| cell | before | after |
|---|---|---|
| fish `spelled` | 11/15 (73%) | **13/15 (87%)** |
| fish overall | 23/45 (51%) | **25/45 (56%)** |
| Apple `spelled` | 8/15 (53%) | **9/15 (60%)** |
| Apple overall | 32/45 (71%) | **33/45 (73%)** |
| ArTST `spelled` | 4/15 (27%) | 4/15 (27%) — unchanged |
| ArTST whisper-medium control, `spelled` | 5/15 (33%) | **6/15 (40%)** |
| all six digit-form cells | — | **unchanged, as required** |

Three rows flipped in total, every one of them `spelled`, every one of them LOST → OK:
`time_0630` for fish and Apple, and `big_674` for fish. **No row went the other way**,
and the digit forms are byte-identical — which is the guarantee that matters, because
the headline finding (7% vs 80% on Arabic-Indic digits) lives entirely in those forms
and is untouched. `test_arnum.py` grew from 19 tests to 34; the original 19 still pass.

Neither the ranking nor any conclusion in this card changes. fish is still stronger on
the spelled form than Apple, Apple is still the only form-agnostic engine, ArTST still
scores 0/30 on digits.

## Reproduce

```sh
python build_set.py
FISH_API_KEY=... python run_bench.py --engine fish
python run_bench.py --engine apple

# ArTST needs torch + transformers to synthesise and faster_whisper to score; if those
# live in different environments, split the run:
python run_bench.py --engine artst --synth-only
python run_bench.py --engine artst

python test_arnum.py

# re-derive every score from the stored transcripts, without re-synthesising
python rescore.py
```

<!-- series-block -->
## Does Arabic Survive the Pipeline?

This is one of three reproducible benchmarks, one per stage of a real production pipeline.
Each measures an Arabic failure that looks correct to anyone who does not read Arabic — which
is exactly why it ships.

- [ArNum-TTS](https://huggingface.co/datasets/syamjithnk/arnum-tts) — do numbers survive speech synthesis? **← you are here**
- [ArShape](https://huggingface.co/datasets/syamjithnk/arshape) — does the standard reshaping recipe survive rendering?
- [ArPDF](https://huggingface.co/datasets/syamjithnk/arpdf) — does Arabic survive a PDF round trip?

All three are CC BY 4.0 and ship the scorer, the raw per-item results, and an explicit statement
of what the measurement does *not* establish. Code is MIT (see `LICENSE`).
<!-- series-block -->

<!-- citation-block -->
## Citation

```bibtex
@misc{syamjithnk_arnum_2026,
  author       = {Syamjith NK},
  title        = {ArNum-TTS: numeral handling in Arabic speech synthesis},
  year         = {2026},
  publisher    = {Hugging Face},
  howpublished = {\url{https://huggingface.co/datasets/syamjithnk/arnum-tts}},
  note         = {Data CC BY 4.0; code MIT}
}
```
<!-- citation-block -->
