"""Sanity tests for the normaliser. A scorer that is itself wrong is worse than none.
Author: Syamjith NK

The block at the bottom is the 2026-08-20 scorer correction: four gaps that were
published as known limitations before they were fixed. The tests above it are the
safety net - they are what proves the fix did not buy the spelled form at the cost of
the digit forms.
"""
from arnum import words_to_values, recovered
P=F=0
def ck(name, cond):
    global P,F
    if cond: P+=1; print(f"  ok   {name}")
    else:    F+=1; print(f"  FAIL {name}")
ck("digits", 674 in words_to_values("تمت مراجعة 674 ملفا"))
ck("arabic-indic digits", 2026 in words_to_values("في عام ٢٠٢٦"))
ck("hundreds+units+tens", 674 in words_to_values("ستمائة وأربعة وسبعون ملفا"))
ck("mئتين وخمسين = 250", 250 in words_to_values("بلغت التكلفة مئتين وخمسين درهما"))
ck("ألفين وستة وعشرين = 2026", 2026 in words_to_values("في عام ألفين وستة وعشرين"))
ck("ثلاثين = 30", 30 in words_to_values("خلال ثلاثين يوما"))
ck("مئة وثلاث وعشرين = 123", 123 in words_to_values("مئة وثلاث وعشرين قضية"))
ck("recovers spoken-word form", recovered("674", "ستمائة وأربعة وسبعون ملفا"))
ck("recovers digit form", recovered("674", "تمت مراجعة 674 ملفا"))
ck("rejects gibberish", not recovered("2026", "تخاناتر أغسطس"))
ck("rejects wrong number", not recovered("2026", "في عام 1999"))
ck("ستة مئة واربع وسبعين = 674 (split hundred)", 674 in words_to_values("تمت مراجعة ستة مئة واربع وسبعين ملفا"))
ck("6:30 keeps the minutes", {6,30} <= words_to_values("الساعة 6:30 صباحا"))
ck("6.30 keeps the minutes", {6,30} <= words_to_values("الساعة 6.30 صباحا"))
ck("recovers 6:30 heard as 6.30", recovered("6:30", "يبدأ التصوير في الساعة 6.30 صباحا"))
ck("مئة وستة is still 106", 106 in words_to_values("مئة وستة"))
ck("الف تسعمائة وواحد وسبعون = 1971", 1971 in words_to_values("عام الف تسعمائة وواحد وسبعون وتغير"))
ck("مليون ومئتي الف = 1200000", 1200000 in words_to_values("مليون ومئتي ألف درهم"))
ck("خمسة عشر = 15", 15 in words_to_values("من عشرة الى خمسة عشر دقيقة"))

# --- 2026-08-20 correction: the four gaps, plus what must NOT move -------------
# 1 - fractions of an hour, gated on a time context
ck("السادسة والنصف = 6:30", {6, 30} <= words_to_values("الساعة السادسة والنصف صباحا"))
ck("السادسة والربع = 6:15", {6, 15} <= words_to_values("الساعة السادسة والربع صباحا"))
ck("النصف outside a time is NOT 30", 30 not in words_to_values("أنجزنا نصف المشروع"))
ck("الربع الأول is NOT 15", 15 not in words_to_values("ارتفعت البلاغات خلال الربع الأول"))
# 2 - tanween leaves a trailing alef
ck("سبعونا = 70 (tanween)", 674 in words_to_values("ستمائة وأربعة وسبعونا ملفا"))
ck("tanween tolerance invents nothing", not words_to_values("تمت مراجعة الملفات يوما بعد يوم"))
# 3 - ordinals written as two words
ck("الثانية عشرة = 12", 12 in words_to_values("الساعة الثانية عشرة ظهرا"))
ck("الحادية عشرة = 11 (not 21)", 11 in words_to_values("الساعة الحادية عشرة صباحا"))
# 4 - the hour closes the group
ck("الثانية عشرة وخمسة وأربعين = 12:45",
   {12, 45} <= words_to_values("الساعة الثانية عشرة وخمسة وأربعين"))
ck("الثانية وخمس وأربعين = 2:45", {2, 45} <= words_to_values("الساعة الثانية وخمس وأربعين دقيقة"))
ck("recovers 6:30 said as السادسة والنصف", recovered("6:30", "يبدأ التصوير في الساعة السادسة والنصف صباحا"))
ck("recovers 2:45 said as الثانية وخمس وأربعين",
   recovered("2:45", "الاجتماع في الساعة الثانية وخمس وأربعين دقيقة بعد الظهر"))
# a date ordinal has no ساعة, so it must still ACCUMULATE - this is the guard that
# stops the clock rule from turning the twenty-eighth into {8, 20}
ck("الثامن والعشرين is still 28", 28 in words_to_values("يصادف يوم المرأة الإماراتية الثامن والعشرين من أغسطس"))
ck("المركز الثالث is still 3", 3 in words_to_values("حصل الفريق على المركز الثالث"))
ck("still rejects a wrong time", not recovered("6:30", "الساعة السابعة والنصف صباحا"))

print(f"\n{P} passed, {F} failed")
raise SystemExit(1 if F else 0)
