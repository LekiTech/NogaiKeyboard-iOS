#!/usr/bin/env python3
"""Letter statistics of Nogai and a model comparison of layout candidates.

Python 3 standard library only. Two sets of counts:

  * the shipped words artifact (NogaiKeyboardExtension/nogai_words.sqlite):
    the count of a word is its base_score // 10 (the v0 score is
    10 x count + word lists). This is dictionary text: equivalents and
    examples of a Russian-Nogai dictionary, so verbal nouns in «-ув», «-уьв»
    are far more frequent than in running text;
  * the letter counts of Agisight/rf-keyboard-corpora for Nogai
    (Tests/NogaiCoreTests/Fixtures/agisight/nog_monocorpus_freq.csv, counted
    by Renat Shakhmirzov on the Nogai part of FineWeb-2: 3.78 million letters
    of web text). Letters only, no words.

Writes docs/layout/analysis.json and prints the same numbers.

    python3 -I scripts/analyze_layout.py

Everything here is a MODEL of typing, not a measurement of people:

  * a word is typed letter by letter, no suggestion is picked;
  * a key costs one tap, also a key that types two characters («нъ»);
  * a letter without a key costs one long press on its base key; a
    long-press option that yields two letters («нъ» under «н») counts as one
    long press and is used only when one of the two letters has no key;
  * time = taps x t + long presses x (t + delay), with the keyboard's default
    long-press delay of 0.3 s and two tap rates t (0.25 s and 0.18 s);
  * two thumbs: a key belongs to the thumb of its half of the keyboard, and a
    thumb travels in a straight line from the previous key it pressed in the
    same word. Key centres are those of General Keyboard's native grid on a
    402 pt wide iPhone (content width 395 pt, row pitch 54 pt).
"""

import csv
import json
import os
import sqlite3
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORDS = os.path.join(REPO, "NogaiKeyboard", "NogaiKeyboardExtension", "nogai_words.sqlite")
AGISIGHT = os.path.join(REPO, "Tests", "NogaiCoreTests", "Fixtures", "agisight", "nog_monocorpus_freq.csv")
OUT = os.path.join(REPO, "docs", "layout", "analysis.json")

DIGRAPHS = ["аь", "нъ", "оь", "уь"]
VOWELS = "аеёиоуыэюя"
SCREEN = 402.0            # pt, iPhone 18 Pro and the other 6.3" iPhones
SMALL_SCREEN = 375.0      # pt, the narrowest supported iPhones
PAD, INSET, PITCH = 3.5, 3.0, 54.0
LONG_PRESS_DELAY = 0.3    # s, KeyboardSettings.CalloutDelay.normal
TAP_RATES = {"0.25 s per tap": 0.25, "0.18 s per tap": 0.18}

RUSSIAN = [list("йцукенгшщзх"), list("фывапролджэ"), list("ячсмитьбю")]

# name -> rows (a key may type two characters), {letter: base key} for letters
# reached by long press, {two-letter long-press option: base key}.
CANDIDATES = {
    "A0": {
        "title": "Russian iOS keyboard as it is (ъ under ь only)",
        "rows": RUSSIAN,
        "long_press": {"ё": "е", "ъ": "ь"},
        "digraph_options": {},
    },
    "A": {
        "title": "Russian iOS layout + the Agisight long-press mapping (аь нъ оь уь under а н о у)",
        "rows": RUSSIAN,
        "long_press": {"ё": "е", "ъ": "ь"},
        "digraph_options": {"нъ": "н"},
    },
    "B": {
        "title": "ъ on щ's key, щ under ш (chosen)",
        "rows": [list("йцукенгшъзх"), list("фывапролджэ"), list("ячсмитьбю")],
        "long_press": {"ё": "е", "щ": "ш"},
        "digraph_options": {},
    },
    "C": {
        "title": "a «нъ» key on щ's key; ъ under ь, щ under ш",
        "rows": [list("йцукенгш") + ["нъ"] + list("зх"), list("фывапролджэ"), list("ячсмитьбю")],
        "long_press": {"ё": "е", "щ": "ш", "ъ": "ь"},
        "digraph_options": {},
    },
    "D": {
        "title": "the Agisight draft (nog_key_default.json): 12 + 12 + 11 keys, a key for each of нъ аь оь уь",
        "rows": [list("йцукенгшщзх") + ["нъ"], list("фывапролджэ") + ["аь"], list("ячсмитьбю") + ["оь", "уь"]],
        "long_press": {"ё": "е", "ъ": "ь"},
        "digraph_options": {},
    },
    "E": {
        "title": "the draft cut to Apple's 12-key rows: нъ on щ's key, уь and оь as 12th keys, 9 letters below",
        "rows": [list("йцукенгш") + ["нъ"] + list("зх") + ["уь"], list("фывапролджэ") + ["оь"], list("ячсмитьбю")],
        "long_press": {"ё": "е", "щ": "ш", "ъ": "ь"},
        "digraph_options": {},
    },
}


def load():
    con = sqlite3.connect(f"file:{WORDS}?mode=ro", uri=True)
    rows = [(w, s // 10) for w, s in con.execute("SELECT word, base_score FROM words") if s >= 10]
    meta = dict(con.execute("SELECT key, value FROM meta"))
    con.close()
    return rows, meta


def load_agisight():
    """{alphabet letter: count}; the table counts НЪ ОЬ УЬ АЬ as letters and Ъ Ь apart from them."""
    with open(AGISIGHT, encoding="utf-8", newline="") as f:
        return {r["letter"].lower(): int(r["frequency"]) for r in csv.DictReader(f)}


def units(word):
    """The word as alphabet letters: the four digraphs are one letter each."""
    out, i = [], 0
    while i < len(word):
        if word[i:i + 2] in DIGRAPHS:
            out.append(word[i:i + 2])
            i += 2
        else:
            out.append(word[i])
            i += 1
    return out


def pct(n, total):
    return round(100.0 * n / total, 3)


# ----------------------------------------------------------------- statistics
def statistics(rows):
    chars, letters, lengths = Counter(), Counter(), Counter()
    before_hard, before_soft = Counter(), Counter()
    tokens = 0
    for word, n in rows:
        tokens += n
        lengths[len(units(word.replace("-", "")))] += n
        for ch in word:
            if ch != "-":
                chars[ch] += n
        for u in units(word):
            if u != "-":
                letters[u] += n
        for i, ch in enumerate(word):
            if ch == "ъ":
                before_hard[word[i - 1] if i else "^"] += n
            if ch == "ь":
                before_soft[word[i - 1] if i else "^"] += n
    total_chars, total_letters = sum(chars.values()), sum(letters.values())
    hard, soft = chars["ъ"], chars["ь"]
    return {
        "word_types": len(rows),
        "word_tokens": tokens,
        "characters": total_chars,
        "alphabet_letters": total_letters,
        "mean_word_length_letters": round(total_letters / tokens, 2),
        "alphabet_letter_percent": {u: pct(n, total_letters) for u, n in letters.most_common()},
        "digraph_percent_of_letters": {d: pct(letters[d], total_letters) for d in DIGRAPHS},
        "digraphs_together_percent_of_letters": pct(sum(letters[d] for d in DIGRAPHS), total_letters),
        "hard_sign": {
            "percent_of_characters": pct(hard, total_chars),
            "rank_among_characters": [ch for ch, _ in chars.most_common()].index("ъ") + 1,
            "after_percent": {k: pct(v, hard) for k, v in before_hard.most_common(5)},
            "outside_нъ_percent_of_letters": pct(letters["ъ"], total_letters),
        },
        "soft_sign": {
            "percent_of_characters": pct(soft, total_chars),
            "after_percent": {k: pct(v, soft) for k, v in before_soft.most_common(6)},
            "outside_аь_оь_уь_percent_of_letters": pct(letters["ь"], total_letters),
        },
        "rare_letters_percent_of_letters": {ch: pct(letters[ch], total_letters) for ch in "щёфцчжхюэ"},
        "old_or_foreign_digraphs_tokens": {d: sum(n * w.count(d) for w, n in rows) for d in ("гъ", "къ", "гь", "нг")},
    }


def agisight_statistics(table):
    total = sum(table.values())
    return {
        "source": "Agisight/rf-keyboard-corpora, data/nog/Renat_Shakhmirzov/frequencies/nog_monocorpus_freq.csv "
                  "(FineWeb-2, Nogai; collected 2025-08-03)",
        "alphabet_letters": total,
        "alphabet_letter_percent": {k: pct(v, total) for k, v in sorted(table.items(), key=lambda kv: -kv[1])},
        "digraph_percent_of_letters": {d: pct(table[d], total) for d in DIGRAPHS},
        "digraphs_together_percent_of_letters": pct(sum(table[d] for d in DIGRAPHS), total),
        "hard_sign_outside_нъ_percent_of_letters": pct(table["ъ"], total),
        "soft_sign_outside_аь_оь_уь_percent_of_letters": pct(table["ь"], total),
        "rare_letters_percent_of_letters": {ch: pct(table[ch], total) for ch in "щёфцчжхюэ"},
    }


# ----------------------------------------------------------------- the typing model
def geometry(rows, screen):
    """Key centres (pt) of the native grid: equal cells in every row; the
    third row has shift and backspace cells around its letters."""
    content = screen - 2 * PAD
    centres = {}
    for r, row in enumerate(rows):
        cells = len(row) + (2 if r == 2 else 0)
        for i, key in enumerate(row):
            column = i + (1 if r == 2 else 0)
            centres[key] = (PAD + (column + 0.5) * content / cells, r * PITCH)
    return centres


def key_width(cells, screen):
    return round((screen - 2 * PAD) / cells - 2 * INSET, 2)


def keystrokes(letters, cand):
    """[(key, is_long_press)] for a word given as alphabet letters (hyphens skipped)."""
    keys = {k for row in cand["rows"] for k in row}
    out = []
    for u in letters:
        if u == "-":
            continue
        if u in keys:
            out.append((u, False))
        elif len(u) == 2:
            a, b = u
            if b not in keys and u in cand["digraph_options"]:
                out.append((cand["digraph_options"][u], True))
            else:
                for ch in (a, b):
                    out.append((ch, False) if ch in keys else (cand["long_press"][ch], True))
        else:
            out.append((cand["long_press"][u], True))
    return out


def evaluate(rows, table, cand):
    centres = geometry(cand["rows"], SCREEN)
    taps = long_presses = tokens = letters = words_with_lp = 0
    travel = same_thumb = transitions = 0.0
    for word, n in rows:
        us = [u for u in units(word) if u != "-"]
        strokes = keystrokes(us, cand)
        lp = sum(1 for _, held in strokes if held)
        tokens += n
        letters += n * len(us)
        taps += n * (len(strokes) - lp)
        long_presses += n * lp
        words_with_lp += n if lp else 0
        last = {}
        previous_thumb = None
        for key, _ in strokes:
            x, y = centres[key]
            thumb = "left" if x < SCREEN / 2 else "right"
            if thumb in last:
                px, py = last[thumb]
                travel += n * ((x - px) ** 2 + (y - py) ** 2) ** 0.5
            if previous_thumb is not None:
                transitions += n
                same_thumb += n if previous_thumb == thumb else 0
            last[thumb] = (x, y)
            previous_thumb = thumb
    # The same key-press count on the Agisight letter table (letters only).
    web_total = sum(table.values())
    web_taps = web_lp = 0
    for u, n in table.items():
        strokes = keystrokes([u], cand)
        lp = sum(1 for _, held in strokes if held)
        web_taps += n * (len(strokes) - lp)
        web_lp += n * lp
    cells = [len(cand["rows"][0]), len(cand["rows"][1]), len(cand["rows"][2]) + 2]
    russian = geometry(RUSSIAN, SCREEN)
    return {
        "title": cand["title"],
        "rows": [" ".join(r) for r in cand["rows"]],
        "keys_per_row": [len(r) for r in cand["rows"]],
        "cells_in_the_widest_row": max(cells),
        "narrowest_key_pt": {f"{int(SCREEN)} pt screen": key_width(max(cells), SCREEN),
                             f"{int(SMALL_SCREEN)} pt screen": key_width(max(cells), SMALL_SCREEN)},
        "dictionary_text": {
            "key_presses_per_word": round((taps + long_presses) / tokens, 3),
            "key_presses_per_100_letters": round(100.0 * (taps + long_presses) / letters, 2),
            "long_presses_per_100_words": round(100.0 * long_presses / tokens, 2),
            "long_presses_per_100_letters": round(100.0 * long_presses / letters, 3),
            "words_needing_a_long_press_percent": pct(words_with_lp, tokens),
            "thumb_travel_pt_per_letter": round(travel / letters, 2),
            "same_thumb_transitions_percent": pct(same_thumb, transitions),
            "seconds_per_100_words": {
                name: round(100.0 * (taps * t + long_presses * (t + LONG_PRESS_DELAY)) / tokens, 1)
                for name, t in TAP_RATES.items()},
        },
        "web_text_agisight": {
            "key_presses_per_100_letters": round(100.0 * (web_taps + web_lp) / web_total, 2),
            "long_presses_per_100_letters": round(100.0 * web_lp / web_total, 3),
            "seconds_per_100_letters": {
                name: round(100.0 * (web_taps * t + web_lp * (t + LONG_PRESS_DELAY)) / web_total, 2)
                for name, t in TAP_RATES.items()},
        },
        "keys_not_in_their_russian_place": sorted(
            k for k in russian if russian[k] != centres.get(k)),
        "letters_without_a_key": sorted(cand["long_press"]),
    }


def digraph_paths(cand):
    keys = {k for row in cand["rows"] for k in row}
    centres = geometry(cand["rows"], SCREEN)
    out = {}
    for d in DIGRAPHS:
        if d in keys:
            out[d] = "1 tap, its own key"
        elif all(ch in keys for ch in d):
            (x1, y1), (x2, y2) = centres[d[0]], centres[d[1]]
            thumbs = ["left" if x < SCREEN / 2 else "right" for x in (x1, x2)]
            out[d] = (f"2 taps, {'alternating thumbs' if thumbs[0] != thumbs[1] else 'same thumb'}, "
                      f"{round(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)} pt apart")
        elif d in cand["digraph_options"]:
            out[d] = f"long press on {d[0]}"
        else:
            out[d] = f"tap {d[0]}, long press on {cand['long_press'][d[1]]}"
    return out


def main():
    rows, meta = load()
    table = load_agisight()
    report = {
        "source": {"artifact": "nogai_words.sqlite", "content_version": meta.get("content_version"),
                   "cleanup_version": meta.get("cleanup_version"),
                   "note": "token-weighted; count of a word = base_score // 10; words known only from a "
                           "word list (count 0) are left out"},
        "statistics_dictionary_text": statistics(rows),
        "statistics_web_text": agisight_statistics(table),
        "model": {"screen_pt": SCREEN, "long_press_delay_s": LONG_PRESS_DELAY, "tap_rates_s": TAP_RATES,
                  "note": "model-based estimates, not measured typing speed"},
        "candidates": {},
    }
    for name, cand in CANDIDATES.items():
        result = evaluate(rows, table, cand)
        result["digraph_entry"] = digraph_paths(cand)
        report["candidates"][name] = result
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
        f.write("\n")
    s = report["statistics_dictionary_text"]
    print("dictionary text:", s["word_tokens"], "tokens,", s["mean_word_length_letters"], "letters per word")
    print(" digraphs %:", s["digraph_percent_of_letters"], "rare %:", s["rare_letters_percent_of_letters"])
    print(" ъ:", s["hard_sign"], "\n ь:", s["soft_sign"], "\n old digraph tokens:", s["old_or_foreign_digraphs_tokens"])
    w = report["statistics_web_text"]
    print("web text:", w["alphabet_letters"], "letters; digraphs %:", w["digraph_percent_of_letters"],
          "rare %:", w["rare_letters_percent_of_letters"], "ъ alone", w["hard_sign_outside_нъ_percent_of_letters"],
          "ь alone", w["soft_sign_outside_аь_оь_уь_percent_of_letters"])
    for name, c in report["candidates"].items():
        d, wt = c["dictionary_text"], c["web_text_agisight"]
        print(f"{name}: keys {c['keys_per_row']} narrowest {c['narrowest_key_pt']} | dict: "
              f"{d['key_presses_per_word']} presses/word, {d['long_presses_per_100_words']} LP/100 words, "
              f"{d['words_needing_a_long_press_percent']} % words, travel {d['thumb_travel_pt_per_letter']}, "
              f"same thumb {d['same_thumb_transitions_percent']} %, s/100 words {d['seconds_per_100_words']} | web: "
              f"{wt['key_presses_per_100_letters']} presses/100 letters, {wt['long_presses_per_100_letters']} LP/100 letters, "
              f"{wt['seconds_per_100_letters']} | moved {c['keys_not_in_their_russian_place']} | {c['digraph_entry']}")


if __name__ == "__main__":
    main()
