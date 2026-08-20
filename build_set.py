#!/usr/bin/env python3
"""Build the ArNum-TTS evaluation set.

Author: Syamjith NK

Every item is ONE sentence rendered three ways, identical except for how the number
is written:

    arabic_indic   ٢٠٢٦        the digits native to Arabic script
    western        2026        the digits most Arabic publishing actually uses
    spelled        ألفان وستة وعشرون   the number written as words

Holding the sentence constant is the whole design. If a system scores differently
across the three, the difference is caused by numeral FORM and nothing else - not by
vocabulary, not by sentence length, not by prosody.

Categories are the ones that break real deliverables: years, percentages, currency,
times, dates, phone numbers, ordinals, decimals, large counts.
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

W2A = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# (id, category, sentence template with {n}, western numeral, spelled-out Arabic)
ITEMS = [
    ("year_2026", "year",
     "في عام {n} ارتفعت نسبة المشاركة في البرنامج الوطني.",
     "2026", "ألفين وستة وعشرين"),
    ("year_1971", "year",
     "تأسس الاتحاد في عام {n} وتغير كل شيء بعدها.",
     "1971", "ألف وتسعمائة وواحد وسبعين"),
    ("pct_47", "percentage",
     "ارتفعت نسبة البلاغات إلى {n} بالمئة خلال الربع الأول.",
     "47", "سبعة وأربعين"),
    ("pct_3_5", "decimal",
     "بلغ معدل النمو {n} بالمئة هذا العام.",
     "3.5", "ثلاثة وخمسة من عشرة"),
    ("count_123", "count",
     "تم إغلاق {n} قضية خلال ثلاثين يوماً فقط.",
     "123", "مئة وثلاث وعشرين"),
    ("count_1500", "count",
     "شارك أكثر من {n} موظف في ورش العمل.",
     "1500", "ألف وخمسمائة"),
    ("money_250", "currency",
     "بلغت التكلفة {n} درهماً لكل مشارك.",
     "250", "مئتين وخمسين"),
    ("money_1200000", "currency",
     "خصصت الميزانية {n} درهم لهذا المشروع.",
     "1200000", "مليون ومئتي ألف"),
    ("time_0630", "time",
     "يبدأ التصوير في الساعة {n} صباحاً.",
     "6:30", "السادسة والنصف"),
    ("time_1445", "time",
     "الاجتماع في الساعة {n} بعد الظهر.",
     "2:45", "الثانية وخمس وأربعين دقيقة"),
    ("date_28_08", "date",
     "يصادف يوم المرأة الإماراتية {n} أغسطس من كل عام.",
     "28", "الثامن والعشرين من"),
    ("phone_971", "phone",
     "للاستفسار يرجى الاتصال على الرقم {n}.",
     "800 555", "ثمانمائة خمسة خمسة خمسة"),
    ("ord_3", "ordinal",
     "حصل الفريق على المركز {n} على مستوى الدولة.",
     "3", "الثالث"),
    ("range_10_15", "range",
     "تستغرق العملية من {n} دقيقة.",
     "10 إلى 15", "عشر إلى خمس عشرة"),
    ("big_674", "count",
     "تمت مراجعة {n} ملفاً قبل التسليم النهائي.",
     "674", "ستمائة وأربعة وسبعين"),
]


def build():
    rows = []
    for iid, cat, tmpl, west, spelled in ITEMS:
        rows.append({"id": iid, "category": cat, "form": "western",
                     "text": tmpl.format(n=west), "expect": west})
        rows.append({"id": iid, "category": cat, "form": "arabic_indic",
                     "text": tmpl.format(n=west.translate(W2A)),
                     "expect": west})
        rows.append({"id": iid, "category": cat, "form": "spelled",
                     "text": tmpl.format(n=spelled), "expect": west})
    p = OUT / "sentences.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    print(f"{len(rows)} utterances ({len(ITEMS)} sentences x 3 numeral forms) -> {p}")


if __name__ == "__main__":
    build()
