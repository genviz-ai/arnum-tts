# One of these reads ٢٠٢٦ as a year. The other reads it as noise.

**Syamjith NK** · 19 August 2026

Arabic is written with two sets of digits. `2026` and `٢٠٢٦` are the same year, and both
are correct Arabic. Newspapers use one, government forms often use the other, and most
writers mix them without thinking about it.

I wanted to know whether text-to-speech systems care. They do — enormously, and not in
the same direction.

## The test

15 Arabic sentences, each written three ways. Same words, same punctuation, same length.
The only thing that changes is how the number is typed:

> في عام **2026** ارتفعت نسبة المشاركة
> في عام **٢٠٢٦** ارتفعت نسبة المشاركة
> في عام **ألفين وستة وعشرين** ارتفعت نسبة المشاركة

45 utterances per engine. Synthesise, transcribe, and ask one narrow question: **could a
listener recover the number?** Not "is the voice pleasant" — whether the figure survived.
Categories are the ones that appear in real work: years, percentages, currency, times,
dates, phone numbers, decimals, large counts.

## The result

| numeral form | Fish Audio `s2.1-pro-free` | Apple `Majed` |
|---|---|---|
| western `2026` | 73% | 80% |
| **arabic-indic `٢٠٢٦`** | **7%** | **80%** |
| spelled out | 87% | 60% |

Apple scores the same on both digit forms, because it converts the numeral before
speaking. Fish drops from 73% to **7%** on identical sentences.

> **Corrected 20 August 2026.** The spelled-out row previously read 73% and 53%. My
> scorer was failing four things that are correct Arabic — half-past
> (`الساعة السادسة والنصف`), a tanween suffix, a two-word ordinal, and a 12-hour time
> it summed instead of splitting. Three utterances re-scored from lost to recovered.
> Every score was re-derived from the transcripts already on file; no audio was
> regenerated, and **neither digit row moved**. Old → new per cell is in the
> [dataset changelog](https://huggingface.co/datasets/syamjithnk/arnum-tts#changelog).

And the failures are not near-misses. `٢٠٢٦` in a date came back as `تخاناتر`. The time
`٢:٤٥` came back as `انفافس اسم مفاعس`. That is not a mispronounced number, it is noise
where a number should be.

## Why this matters more than it sounds

Nobody notices, because **TTS demos do not contain numbers.** You audition a voice on a
paragraph of prose, it sounds excellent, you ship it. The failure only appears in the
deliverable — a price, a date, a phone number, a percentage in an awareness film — and by
then it is in front of a client.

The fix is one line: normalise every numeral to Western digits before synthesis. What is
worth knowing is that you have to *know* to do it.

## A second thing, found by accident

While testing prosody I noticed the same engine sounds mechanical — word by word, evenly
spaced — on plain Arabic text. Written Arabic omits short vowels, so the engine has to
guess how each word is voiced, and when it is unsure it retreats to a flat read.

Add tashkeel and it stops guessing. The same sentence runs 7.8 seconds undiacritized and
10.6 seconds diacritized: it is phrasing rather than marching. A native Emirati speaker,
given three takes blind, chose the diacritized one.

So there are two rules for Arabic TTS, and both cost nothing:
**Western digits. Diacritics.**

## Honesty about the numbers

The absolute percentages understate both engines. The measurement chain is
TTS → Whisper → a number parser, and an error anywhere gets charged to the voice. Three
rounds of fixes to my own scorer moved the Western scores from 47% to 73–80% without a
single audio file changing — most of the early "failure" was my harness, not the engines.
One of those bugs was silently punishing Apple for speaking dates ordinally, which is
correct Arabic.

The 7% vs 80% gap is the robust finding. Transcription noise cannot manufacture that, and
the Arabic-Indic transcripts are visibly gibberish rather than approximations.

Still open: only two engines, and no human listening pass yet — every judgement so far is
a transcriber's, not an ear's.

## Reproduce it

The sentence set, the scorer and the results are published. The audio is not — the free
tiers used carry no redistribution rights, and regenerating it takes a minute anyway,
which makes the benchmark reproducible instead of frozen.

```sh
python build_set.py
python run_bench.py --engine fish
python run_bench.py --engine apple
```

If you work in Arabic audio, run it against your engine. I would like to know which
others get `٢٠٢٦` right.
