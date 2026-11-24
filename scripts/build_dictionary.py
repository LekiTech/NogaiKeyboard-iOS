#!/usr/bin/env python3
"""Build the Nogai keyboard dictionary from the v0 data (cleanup version 1).

Deterministic, Python 3 standard library only. Reads (never writes) the five
v0 Nogai files of keyboard_data_v0.zip, checked against pinned SHA-256 sums:

    nog_words.sqlite  nog_bigrams.sqlite  nog_words.tsv  nog_bigrams.tsv  nog_stats.json

and the tables of scripts/data/ that scripts/derive_source_repairs.py wrote
when it read the v0 sources again (also pinned).

Writes:

    <out>/nogai_words.sqlite        words(word, base_score) + meta   (General Keyboard artifact)
    <out>/nogai_bigrams.sqlite      bigrams(prev, word, weight) + meta
    <review>/manifest.json          the sources: archive, files, upstream commits, checksums, licences
    <review>/corrections.csv        every row removed, restored or recounted, with the rule and the reason
    <review>/merges.csv             every spelling variant merged into the attested word
    <review>/removed_pairs.csv      every v0 word pair that is not a pair of the source
    <review>/flagged.csv            entries kept as they are and listed for a linguistic review
    <review>/high_priority.csv      the flagged entries to look at first
    <review>/reconciliation.csv     rows, counts and weights of v0, of every rule and of the result
    <review>/summary.json           counts of the audit, the changes and the flags

Usage, from the repository root:

    python3 -I scripts/build_dictionary.py               # build + validate
    python3 -I scripts/build_dictionary.py --validate    # validate the shipped artifacts only
    python3 -I scripts/build_dictionary.py --source DIR --out DIR --review DIR

Set SOURCE_DATE_EPOCH to make meta.generated_at (and so the sqlite bytes)
reproducible; the rows are identical on every run regardless. The build
refuses to replace artifacts that carry a newer cleanup or content version
than this script (an obsolete checkout cannot overwrite approved data).

The rules are documented in docs/DICTIONARY.md. In short:

  * The v0 Nogai data is not scanned text. Its main source is a
    Russian-Nogai dictionary, and what is wrong with v0 came from how its
    builder read that dictionary (scripts/derive_source_repairs.py names
    each error and proves the replay). The source rules:
      G1  Russian sense glosses in brackets are not Nogai text;
      T1  the Russian translations of examples are not Nogai text;
      A1  suffix citations («-ден», «=тан») are not words;
      L1  a word typed with a Latin twin is read whole;
      F1  Nogai lines that v0's Russian filter threw out are read;
      Q1  one-word fields with punctuation («кайда?») are read;
      I1  IDS forms with a decomposed «й» are read whole;
      X1  the pronoun forms of the Apertium lexicon are put together;
      P1  two words are a pair only with nothing but a space between them.
  * Three spelling rules merge a variant into the attested word:
      S1  «ъ» typed for «ь» after а, о, у («соъз» -> «соьз»);
      S2  «нь» typed for «нъ» («сизинь» -> «сизинъ»);
      M1  the IDS transcription «йа», «йу» -> the literary «я», «ю»
          («йулдыз» -> «юлдыз»).
    A merge needs the target to be a row already. Nothing is respelled
    into a form the sources do not have.
  * No count is estimated. base_score keeps the v0 formula,
    10 x occurrences in the source lines + min(9, word lists).
  * Doubtful entries stay as they are and are written to flagged.csv.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.join(REPO, "dictionary-source", "original-v0")
DEFAULT_OUT = os.path.join(REPO, "NogaiKeyboard", "NogaiKeyboardExtension")
DEFAULT_REVIEW = os.path.join(REPO, "docs", "dictionary", "review")
DATA = os.path.join(REPO, "scripts", "data")

# keyboard_data_v0.zip, folder keyboard_data/, built 2026-10-11. The v0
# language code is nog (ISO 639-3).
ARCHIVE_SHA256 = "8cec9c22b314373386dbcbbbe1680d765b4f212de655162197af019402b8ac31"
V0_SHA256 = {
    "nog_words.sqlite": "386c67373a074dd7383655dce949dd02207209f5bd2b9322670e48a752b92951",
    "nog_bigrams.sqlite": "73c1cd4bc43931f21dd3638b4b5357c1621953851dff0fccc50c07e3d1bb4e56",
    "nog_words.tsv": "5e6a3cbc12d719f46e67c65debcc51762535b5a0e0ab40177011c4747652459e",
    "nog_bigrams.tsv": "08cf7ab0226105ccfaac229e1a7fa7441b2dbd135b59e095265b35d86b097b5d",
    "nog_stats.json": "8d3ef6345cb8b3bd633aa99824778825d59fe6918e726328404360ff82ef028d",
}
# scripts/data/, written by scripts/derive_source_repairs.py from the pinned sources.
REPAIR_SHA256 = {
    "source_words.tsv": "7c47f1dd65de4b5b7b87a7e1eb80863e7665ae7f670e0043c3a1fe008b17a1d7",
    "v0_removed_words.tsv": "4f4ac95bf559fbc750cdab115139cefbbf88ee65b81e27cf6aa39ec61f1c33b9",
    "source_pairs.tsv": "41bfa5e6ca1dc07f643df2be8f35a0142b52c07f8d41da46d6c2907013df20f6",
    "v0_removed_pairs.tsv": "2c2fde60719adecc34f310af1be583aee26c09ca1f087bc28d3797380f263fc5",
    "source_reading.json": "6fb3b9951473ceec2328afbb231987cfd64c3c7a96b3a7cf95ea41e80b54a35e",
    "brackets.tsv": "91bd8d22ca95b1cb0c1301387915e4ca0ee845df389557d6e2141ab34d4c68c7",
    "ids_repaired_forms.tsv": "b9e4778d18448b4877a366e9d98f5a07fc38fe7ac750daa992b7e1937bcb7463",
    "restored_lines.tsv": "3177de1d2ee1bbcaf542f0af02cda70cae254175e1f89be6b4eb0be738787e83",
    "bracket_decisions.tsv": "e227c9e4d592d77c27a99078d3ced0fec22062da68eb7ddde1c14f7c1e59ac3f",
    "russian_words_in_sources.txt": "6b1718a621ab61c0e3c6d2d3d99b94d836263a85246e67a011523042728c93d0",
}
# The sources themselves (dictionary-source/upstream/), which only
# derive_source_repairs.py reads.
UPSTREAM = {
    "nogai_russian_dictionary": {
        "repository": "https://github.com/shakhmirzovrenat/Dataset-of-nogai-language.",
        "commit": "3ff8a74c159ab4f594ee556f77dea4137ee44416",
        "commit_date": "2026-05-11",
        "file": "nogai_russian_dictionary.json",
        "copy": "dictionary-source/upstream/nogai-dataset-3ff8a74/nogai_russian_dictionary.json",
        "sha256": "5d7aa550d9504cf2d1449d33f2b4b7bf182a48efd28cedc311c4da0d74ae7f83",
        "what": "24,340 entries of a Russian-Nogai dictionary collected from Glosbe: Russian headword, "
                "Nogai equivalents, 3,245 Nogai examples with Russian translations",
        "licence": "MIT, Copyright (c) 2026 shakhmirzovrenat (Shakhmirzov Renat Safarovich)",
    },
    "apertium_nog": {
        "repository": "https://github.com/apertium/apertium-nog",
        "commit": "09fdef073c5900c1f7be2b59c59f53f3a5856b97",
        "commit_date": "2021-07-20",
        "file": "apertium-nog.nog.lexc",
        "copy": "dictionary-source/upstream/apertium-nog-09fdef0/apertium-nog.nog.lexc",
        "sha256": "1af6945cf18d7929d6a8a8a3078cde53030a8eba525fa4b187d5b9d31b07b026",
        "what": "the lexicon of the Apertium morphological transducer for Nogai; a word list of 1,315 words",
        "licence": "GNU GPL v3 (COPYING); authors in AUTHORS",
    },
    "ids": {
        "repository": "https://github.com/intercontinental-dictionary-series/ids",
        "commit": "bf6c9f8c7d25c15e61e338f3ed29ae46b844c0f8",
        "commit_date": "2026-10-09",
        "file": "cldf/forms.csv",
        "file_sha256": "1ff6caa439d27d05c0ce7e72b656bfae5595bc5d12ae57b494e481e90e4e9968",
        "copy": "dictionary-source/upstream/ids-bf6c9f8/forms_nogai_73.csv",
        "sha256": "7f6554891085ad8cb473fec6cbdc9afe1484325dfdded305d1d00becf459c711",
        "what": "Language_ID 73 «Nogai» (author Madzhid Khalilov, data entry Stefan Lange), 2,031 rows; "
                "a word list of 1,694 words",
        "licence": "CC BY 4.0",
        "citation": "Key, Mary Ritchie & Comrie, Bernard (eds.) 2023. The Intercontinental Dictionary Series. "
                    "Leipzig: Max Planck Institute for Evolutionary Anthropology. https://ids.clld.org",
    },
    "russian_filter": {
        "repository": "https://github.com/LingConLab/Cyrillic_languages_identification_models_and_data_store",
        "commit": "3c18d336b0258b2bfefaac73ba84da3e667bd101",
        "commit_date": "2023-11-10",
        "file": "data/clean_data_with_frequency.csv.zip",
        "file_sha256": "f23b302724fbc53d60fcdd4dc4ccba83b61a32e6a5c52bd8f9ede25b5c788623",
        "copy": "scripts/data/russian_words_in_sources.txt",
        "what": "the 142,284 Russian word forms v0 used as its Russian filter (Universal Dependencies "
                "treebanks); kept here: the 14,456 of them that occur in the dictionary. Not a source of "
                "words, only of the knowledge that a word is also Russian",
        "licence": "no licence file in the repository; the extract is a list of Russian word forms",
    },
}

LANGUAGE = "nog"
WORDS_ARTIFACT = "nogai_words"
BIGRAMS_ARTIFACT = "nogai_bigrams"
SCHEMA_VERSION = 1
CONTENT_VERSION = 1
NORMALIZATION_PROFILE = "nogai-cyrillic"   # NogaiDefinition.swift, NormalizationProfile.id
NORMALIZATION_VERSION = 1
MIN_READER_SCHEMA = 1
CLEANUP_VERSION = 1
MIN_PAIR_WEIGHT = 2                         # the v0 rule, unchanged

# The CREATE statements of the v0 files, which are the General Keyboard
# artifact shape (docs/engine/ARTIFACT_CONTRACT.md §1). The build checks that
# the v0 files carry exactly these and writes them unchanged.
WORDS_SQL = "CREATE TABLE words(word TEXT PRIMARY KEY, base_score INTEGER NOT NULL DEFAULT 0) WITHOUT ROWID"
BIGRAMS_SQL = ("CREATE TABLE bigrams(prev TEXT NOT NULL, word TEXT NOT NULL, weight INTEGER NOT NULL, "
               "PRIMARY KEY(prev, word)) WITHOUT ROWID")
META_SQL = "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)"

SOURCES = {
    "glosbe_phrases": "Russian-Nogai dictionary collected from Glosbe (github.com/shakhmirzovrenat, MIT): "
                      "the Nogai equivalents of more than one word and the Nogai examples; the only source "
                      "of counts and of word pairs",
    "glosbe_words": "the one-word Nogai equivalents of the same dictionary (word list)",
    "apertium_nog": "Apertium Nogai lexicon apertium-nog.nog.lexc (word list, GPL v3)",
    "ids": "Intercontinental Dictionary Series, CLDF, list 73 «Nogai» (M. Khalilov), CC BY 4.0 (word list)",
}
LIST_NAMES = {"g": "glosbe_words", "a": "apertium_nog", "i": "ids"}

VOWELS = "аеёиоуыэюя"
CONSONANTS = "бвгджзйклмнпрстфхцчшщ"
ALPHABET_RE = re.compile(r"[а-яё]+(?:-[а-яё]+)*")

# ----------------------------------------------------------------- the GK contract
# Mirror of GeneralKeyboard's Normalization.swift with the Nogai profile of
# NogaiDefinition.swift (no palochka, the twelve Latin homoglyphs, digraph
# tails ъ ь). Used only to CHECK the rows.
_SWIFT_WHITESPACE = "\t\n\x0b\x0c\r\x85" + "".join(
    chr(cp) for cp in range(0x110000) if unicodedata.category(chr(cp)) in ("Zs", "Zl", "Zp"))
_HOMOGLYPHS = {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х",
               "y": "у", "k": "к", "m": "м", "t": "т", "b": "ь", "h": "н"}
_TAILS = {"ь", "ъ"}
_PALOCHKAS = {"Ӏ", "ӏ"}   # never part of Nogai


def canonical(token):
    t = unicodedata.normalize("NFC", token).strip(_SWIFT_WHITESPACE).lower()
    if any(0x0400 <= ord(ch) <= 0x04FF for ch in t):
        t = "".join(_HOMOGLYPHS.get(ch, ch) for ch in t)
    return unicodedata.normalize("NFC", t)


def letter_count(token):
    return sum(0 if ch in _TAILS else 1 for ch in token)


def is_valid_token(token):
    """Normalization.isValidToken for a canonical token."""
    if not token or len(token) > 64:
        return False
    if any(ch.isspace() or ch.isdigit() for ch in token) or any(ch in token for ch in "@/."):
        return False
    if any(ch.isascii() and ch.isalpha() for ch in token):
        return False
    if any(unicodedata.category(ch) in ("Cc", "Cf") for ch in token):
        return False
    return letter_count(token) >= 2


# ----------------------------------------------------------------- input
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def table_sql(con):
    return {name: sql for name, sql in con.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")}


class Fail(Exception):
    pass


def load(source):
    for name, digest in V0_SHA256.items():
        path = os.path.join(source, name)
        if not os.path.exists(path):
            raise Fail(f"missing v0 file {path}")
        if sha256(path) != digest:
            raise Fail(f"{name}: SHA-256 differs from the pinned v0 file")

    wc, bc = ro(os.path.join(source, "nog_words.sqlite")), ro(os.path.join(source, "nog_bigrams.sqlite"))
    if table_sql(wc) != {"words": WORDS_SQL, "meta": META_SQL}:
        raise Fail("nog_words.sqlite: unexpected schema")
    if table_sql(bc) != {"bigrams": BIGRAMS_SQL, "meta": META_SQL}:
        raise Fail("nog_bigrams.sqlite: unexpected schema")
    sqlite_words = dict(wc.execute("SELECT word, base_score FROM words"))
    sqlite_pairs = {(a, b): w for a, b, w in bc.execute("SELECT prev, word, weight FROM bigrams")}
    v0_meta = dict(wc.execute("SELECT key, value FROM meta"))
    wc.close()
    bc.close()
    if v0_meta.get("language") != LANGUAGE:
        raise Fail(f"nog_words.sqlite: meta.language is {v0_meta.get('language')!r}, expected {LANGUAGE!r}")

    words = {}
    with open(os.path.join(source, "nog_words.tsv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            words[r["word"]] = {
                "score": int(r["base_score"]), "count": int(r["count"]), "clean": int(r["clean_count"]),
                "ocr": int(r["ocr_count"]), "extra": int(r["extra_count"]), "lex": int(r["lexicon_sources"]),
            }
    if {w: r["score"] for w, r in words.items()} != sqlite_words:
        raise Fail("nog_words.tsv and nog_words.sqlite disagree")
    with open(os.path.join(source, "nog_bigrams.tsv"), encoding="utf-8", newline="") as f:
        tsv_pairs = {(r["prev"], r["word"]): int(r["weight"]) for r in csv.DictReader(f, delimiter="\t")}
    if tsv_pairs != sqlite_pairs:
        raise Fail("nog_bigrams.tsv and nog_bigrams.sqlite disagree")
    with open(os.path.join(source, "nog_stats.json"), encoding="utf-8") as f:
        stats = json.load(f)
    return words, sqlite_pairs, v0_meta, stats


def load_repairs():
    for name, digest in REPAIR_SHA256.items():
        path = os.path.join(DATA, name)
        if not os.path.exists(path):
            raise Fail(f"missing table {path}")
        if sha256(path) != digest:
            raise Fail(f"{name}: SHA-256 differs from the pinned table (re-run derive_source_repairs.py "
                       "only against the pinned sources, then pin its output here)")

    def rows(name):
        with open(os.path.join(DATA, name), encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f, delimiter="\t"))

    with open(os.path.join(DATA, "source_reading.json"), encoding="utf-8") as f:
        reading = json.load(f)
    return {"words": rows("source_words.tsv"), "removed": rows("v0_removed_words.tsv"),
            "pairs": rows("source_pairs.tsv"), "removed_pairs": rows("v0_removed_pairs.tsv"),
            "brackets": rows("brackets.tsv"), "reading": reading}


def score_of(count, lists):
    """base_score of the v0 builder: 10 x corpus count + min(9, word lists)."""
    return 10 * count + min(9, len(lists))


# ----------------------------------------------------------------- audit of v0
def audit(words, pairs):
    inventory = Counter()
    for w in words:
        inventory.update(w)
    canon_groups = defaultdict(list)
    for w in words:
        canon_groups[canonical(w)].append(w)
    return {
        "words": len(words),
        "bigrams": len(pairs),
        "corpus_tokens": sum(r["count"] for r in words.values()),
        "base_score_total": sum(r["score"] for r in words.values()),
        "bigram_weight_total": sum(pairs.values()),
        "words_with_a_count": sum(1 for r in words.values() if r["count"] > 0),
        "word_lists_only": sum(1 for r in words.values() if r["count"] == 0),
        "character_inventory": {f"{ch} U+{ord(ch):04X}": n for ch, n in
                                sorted(inventory.items(), key=lambda kv: (-kv[1], kv[0]))},
        "not_nfc": sorted(w for w in words if unicodedata.normalize("NFC", w) != w),
        "not_lowercase": sorted(w for w in words if w != w.lower()),
        "not_canonical": sorted(w for w in words if canonical(w) != w),
        "canonical_collisions": sorted(ws for ws in canon_groups.values() if len(ws) > 1),
        "contract_invalid": sorted(w for w in words if not is_valid_token(w)),
        "outside_alphabet": sorted(w for w in words if not ALPHABET_RE.fullmatch(w)),
        "latin_letters": sorted(w for w in words if any(ch.isascii() and ch.isalpha() for ch in w)),
        "palochka": sorted(w for w in words if any(ch in _PALOCHKAS for ch in w)),
        "replacement_or_control_chars": sorted(
            w for w in words if any(ch == "�" or unicodedata.category(ch) in ("Cc", "Cf", "Co", "Cs")
                                    for ch in w)),
        "hyphenated": sum(1 for w in words if "-" in w),
        "with_ae": sum(1 for w in words if "аь" in w),
        "with_ng": sum(1 for w in words if "нъ" in w),
        "with_oe": sum(1 for w in words if "оь" in w),
        "with_ue": sum(1 for w in words if "уь" in w),
        "score_formula_mismatch": sorted(w for w, r in words.items()
                                         if r["score"] != 10 * r["count"] + min(9, r["lex"])),
        "count_mismatch": sorted(w for w, r in words.items()
                                 if r["count"] != r["clean"] + r["ocr"] + r["extra"]),
        "bigram_orphans": sum(1 for a, b in pairs if a not in words or b not in words),
        "bigram_weight_below_2": sum(1 for v in pairs.values() if v < 2),
        "top_pair": max(pairs.items(), key=lambda kv: kv[1])[0],
    }


# ----------------------------------------------------------------- the source rules
G1 = "G1 Russian sense gloss in brackets"
T1 = "T1 Russian translation of an example"
GT = "G1 + T1 Russian: glosses and translations"
A1 = "A1 suffix citation"
L1 = "L1 word typed with a Latin twin"
F1 = "F1 line v0 dropped as Russian"
Q1 = "Q1 one-word field with punctuation"
I1 = "I1 IDS form with a decomposed «й»"
X1 = "X1 pronoun form of the Apertium lexicon"
C1 = "C1 count corrected"
REMOVAL_RULE = {
    "Russian: in sense glosses and in translations of examples": GT,
    "Russian: in sense glosses (brackets) only": G1,
    "Russian: in translations of examples only": T1,
    "suffix citation": A1,
    "piece of a word typed in two scripts": L1,
    "ending of a pronoun form in the Apertium lexicon": X1,
    "piece of an IDS form cut at «й» (и + U+0306)": I1,
    "piece of a one-word field": Q1,
}


def apply_source_reading(words, pairs, repairs):
    """The rows and pairs of the repaired reading, and the log of every difference from v0."""
    log = []          # (rule, action, entry, v0_base_score, base_score, note)
    final = {}
    for r in repairs["words"]:
        w = r["word"]
        rec = {"count": int(r["count"]), "lists": r["lists"], "russian": r["on_russian_lists"] == "1",
               "occurrences": int(r["occurrences"]), "capitalized": int(r["capitalized"]),
               "all_capitals": int(r["all_capitals"]), "headword": r["first_headword"]}
        rec["score"] = score_of(rec["count"], rec["lists"])
        final[w] = rec
        old = words.get(w)
        if old is None:
            if int(r["as_repaired_word"]):
                rule, why = L1, "typed with a Latin letter in the source; v0 read its pieces"
            elif int(r["in_restored_lines"]):
                rule, why = F1, "stands only in lines that v0 dropped as Russian"
            elif "i" in rec["lists"]:
                rule, why = I1, "v0 cut the IDS form at «й»"
            elif "a" in rec["lists"]:
                rule, why = X1, "put together from the first letter and the ending"
            elif "g" in rec["lists"]:
                rule, why = Q1, "v0 rejected the field for its punctuation"
            else:
                raise Fail(f"{w!r} is new for no stated reason")
            where = f"; Russian headword «{rec['headword']}»" if rec["headword"] else ""
            log.append((rule, "row restored", w, "", rec["score"], why + where))
            continue
        if (old["count"], old["lex"]) != (rec["count"], len(rec["lists"])):
            parts = []
            for key, text in (("in_gloss", "in Russian glosses"), ("in_translation", "in Russian translations"),
                              ("as_affix", "as a suffix citation"), ("as_cut_piece", "as a piece of a cut word")):
                if int(r[key]):
                    parts.append(f"-{r[key]} {text}")
            for key, text in (("in_restored_lines", "in lines v0 dropped"), ("as_repaired_word", "read whole")):
                if int(r[key]):
                    parts.append(f"+{r[key]} {text}")
            if old["lex"] != len(rec["lists"]):
                parts.append(f"word lists {old['lex']} -> {len(rec['lists'])}")
            log.append((C1, "count corrected", w, old["score"], rec["score"],
                        f"count {old['count']} -> {rec['count']}: " + ", ".join(parts)))
    for r in repairs["removed"]:
        w = r["word"]
        if w in final or w not in words:
            raise Fail(f"{w!r}: the removed-words table does not fit the data")
        log.append((REMOVAL_RULE[r["reason"]], "row removed", w, words[w]["score"], "", r["reason"]))
    if set(words) - set(final) != {r["word"] for r in repairs["removed"]}:
        raise Fail("the tables do not account for every v0 row")
    final_pairs = {(r["prev"], r["word"]): int(r["weight"]) for r in repairs["pairs"]}
    gone = {(r["prev"], r["word"]) for r in repairs["removed_pairs"]}
    if set(pairs) - set(final_pairs) != gone:
        raise Fail("the tables do not account for every v0 pair")
    return final, final_pairs, log


# ----------------------------------------------------------------- the spelling rules
S1 = "S1 «ъ» typed for «ь» after а, о, у"
S2 = "S2 «нь» typed for «нъ»"
M1 = "M1 IDS transcription «йа», «йу» for «я», «ю»"


def plan_merges(final):
    """[(rule, source, target)]: the source is a variant of the attested target."""
    merges = []
    for w in sorted(final):
        rec = final[w]
        if re.search("[аоу]ъ", w) and not rec["lists"].replace("g", ""):
            t = re.sub("([аоу])ъ", r"\1ь", w)
            if t in final and final[t]["count"] >= rec["count"]:
                merges.append((S1, w, t))
                continue
        if "нь" in w and not rec["lists"] and not rec["russian"]:
            t = w.replace("нь", "нъ")
            if t in final and final[t]["count"] >= rec["count"]:
                merges.append((S2, w, t))
                continue
        if rec["lists"] == "i" and rec["count"] == 0 and re.search("й[ау]", w):
            t = re.sub("йуь?", "ю", w.replace("йа", "я"))
            if t in final and (final[t]["count"] or final[t]["lists"].replace("i", "")):
                merges.append((M1, w, t))
    return merges


def apply_merges(final, pairs, merges):
    rows = []
    for rule, src, dst in merges:
        s, d = final[src], final[dst]
        before = d["score"]
        d["count"] += s["count"]
        d["lists"] = "".join(c for c in "gai" if c in d["lists"] or c in s["lists"])
        d["score"] = score_of(d["count"], d["lists"])
        rows.append((src, dst, rule, s["score"], before, d["score"]))
        del final[src]
    target = {src: dst for _, src, dst in merges}
    out = Counter()
    rekeyed = 0
    for (a, b), v in pairs.items():
        na, nb = target.get(a, a), target.get(b, b)
        rekeyed += (na, nb) != (a, b)
        out[(na, nb)] += v
    return dict(out), rows, rekeyed


# ----------------------------------------------------------------- flags
F_OLD = "«къ», «гъ» or «гь»: not letters of today's alphabet"
F_IDS_J = "IDS transcription «й» + а, у; no literary spelling in the sources"
F_HARD = "«ъ» where Nogai spelling has none"
F_NG = "«нь» in a Nogai word: possibly «нъ»"
F_SOFT = "«ь» after a consonant: a Russian loan with a Nogai ending, or a misprint"
F_LABEL = "a Russian grammatical label of the dictionary"
F_RU_FORM = "Russian infinitive or adjective form"
F_RUS = "also a Russian word, seen once and in no word list: a loan, or Russian text"
F_NAME = "capitalized in the source: a name or a title"
F_ABBR = "abbreviation: written in capitals in the source"
F_TWO = "two-letter word outside the word lists"
F_NO_VOWEL = "no vowel"
F_TRIPLE = "the same letter three times"
F_LONG = "very long word"
F_BRACKET = "Nogai words in a garbled bracket, not in the dictionary"
HIGH = {F_OLD, F_IDS_J, F_HARD, F_NG, F_LABEL, F_BRACKET}
LABELS = {"частица", "союз", "предлог", "наречие", "междометие", "местоимение", "глагол", "приставка"}
RU_ENDING = re.compile(r"(ться|ать|ять|ить|еть|уть|овать|ый|ий|ая|яя|ое|ее|ые|ие|ной)$")


def flag_entries(final):
    """Entries kept unchanged and listed for review: {word: [(category, note)]}."""
    flags = defaultdict(list)
    for w, rec in final.items():
        in_lists = bool(rec["lists"])
        if re.search("къ|гъ|гь", w):
            flags[w].append((F_OLD, "«гъ» and «къ» left the alphabet in 1944, «гь» was never in it; "
                                    "today's spelling has «г», «к»"
                                    + (", and «нъ» where this is a misprint of it" if "къ" in w else "")))
        if rec["lists"] == "i" and rec["count"] == 0 and re.search("й[ау]", w):
            flags[w].append((F_IDS_J, "the dictionary writes «я» 3,374 times and «йа» once, «ю» 1,440 times "
                                      "and «йу» never; the literary form of this word, probably «"
                                      + re.sub("йуь?", "ю", w.replace("йа", "я")) + "», is in no source"))
        if re.search("(?<!н)ъ", w) and not rec["russian"] and "a" not in rec["lists"] and not re.search("къ|гъ", w):
            flags[w].append((F_HARD, "«ъ» stands after «н» only (the letter «нъ»), or in a Russian loan"))
        if re.search("нь(?![яюеёи])", w) and not rec["russian"] and not in_lists:
            flags[w].append((F_NG, "Nogai spells the sound with «нъ»; «нь» stands in Russian loans"))
        elif re.search("(?<![аоу])ь", w) and not rec["russian"] and not in_lists:
            flags[w].append((F_SOFT, "«ь» belongs to «аь», «оь», «уь»; elsewhere it comes with a Russian stem"))
        if w in LABELS:
            flags[w].append((F_LABEL, "the dictionary writes it before a bracket («частица (только) тек»)"))
        elif rec["russian"] and RU_ENDING.search(w) and not in_lists:
            flags[w].append((F_RU_FORM, "the dictionary uses such forms inside Nogai phrases "
                                        "(«печатать этуьв»), and a few are stray Russian"))
        elif rec["russian"] and not in_lists and rec["count"] <= 1:
            flags[w].append((F_RUS, f"Russian headword «{rec['headword']}»" if rec["headword"] else ""))
        if rec["occurrences"] and rec["all_capitals"] == rec["occurrences"]:
            flags[w].append((F_ABBR, "the dictionary keeps lowercase rows"))
        elif rec["occurrences"] and rec["capitalized"] == rec["occurrences"] and "a" not in rec["lists"]:
            flags[w].append((F_NAME, "the dictionary keeps lowercase rows; the keyboard writes the capital "
                                     "when the word is typed with one"))
        if len(w) == 2 and not in_lists:
            flags[w].append((F_TWO, ""))
        if not any(ch in VOWELS for ch in w) and not (rec["occurrences"] and rec["all_capitals"] == rec["occurrences"]):
            flags[w].append((F_NO_VOWEL, ""))
        if re.search(r"(.)\1\1", w):
            flags[w].append((F_TRIPLE, ""))
        if len(w) >= 20:
            flags[w].append((F_LONG, ""))
    return flags


# ----------------------------------------------------------------- output
def generated_at():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    t = datetime.fromtimestamp(int(epoch), timezone.utc) if epoch else datetime.now(timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def guard_existing(out):
    """Refuse to replace artifacts built by a newer cleanup or content version."""
    for artifact_name in (WORDS_ARTIFACT, BIGRAMS_ARTIFACT):
        path = os.path.join(out, artifact_name + ".sqlite")
        if not os.path.exists(path):
            continue
        con = ro(path)
        try:
            meta = dict(con.execute("SELECT key, value FROM meta"))
        except sqlite3.Error:
            meta = {}
        finally:
            con.close()
        for key, ours in (("cleanup_version", CLEANUP_VERSION), ("content_version", CONTENT_VERSION),
                          ("schema_version", SCHEMA_VERSION)):
            theirs = meta.get(key)
            if theirs is not None and theirs.isdigit() and int(theirs) > ours:
                raise Fail(f"{path} has {key} {theirs}, newer than this script's {ours}: "
                           "refusing to overwrite it with older data")


def write_artifacts(out, final, pairs):
    os.makedirs(out, exist_ok=True)
    common = [
        ("schema_version", str(SCHEMA_VERSION)), ("content_version", str(CONTENT_VERSION)),
        ("normalization_version", str(NORMALIZATION_VERSION)), ("normalization_profile", NORMALIZATION_PROFILE),
        ("min_reader_schema", str(MIN_READER_SCHEMA)), ("cleanup_version", str(CLEANUP_VERSION)),
        ("generated_at", generated_at()), ("language", LANGUAGE),
        ("sources", json.dumps(SOURCES, ensure_ascii=False, sort_keys=True)),
    ]
    specs = [
        (WORDS_ARTIFACT, WORDS_SQL, "INSERT INTO words(word, base_score) VALUES(?, ?)",
         sorted((w, r["score"]) for w, r in final.items()),
         ["nog_words.sqlite", "nog_words.tsv", "source_words.tsv", "v0_removed_words.tsv"]),
        (BIGRAMS_ARTIFACT, BIGRAMS_SQL, "INSERT INTO bigrams(prev, word, weight) VALUES(?, ?, ?)",
         sorted((a, b, v) for (a, b), v in pairs.items()),
         ["nog_bigrams.sqlite", "nog_bigrams.tsv", "source_pairs.tsv", "v0_removed_pairs.tsv"]),
    ]
    digests = {**V0_SHA256, **REPAIR_SHA256}
    for artifact_name, create, insert, rows, inputs in specs:
        path = os.path.join(out, artifact_name + ".sqlite")
        tmp = path + ".tmp"
        if os.path.exists(tmp):
            os.remove(tmp)
        con = sqlite3.connect(tmp)
        con.execute("PRAGMA page_size = 4096")
        con.execute(create)
        con.execute(META_SQL)
        con.executemany(insert, rows)
        derived = json.dumps({n: digests[n] for n in inputs}, sort_keys=True)
        meta = [("artifact", artifact_name)] + common + [("row_count", str(len(rows))), ("derived_from", derived)]
        con.executemany("INSERT INTO meta(key, value) VALUES(?, ?)", sorted(meta))
        con.commit()
        con.execute("VACUUM")
        con.close()
        os.replace(tmp, path)


FLAG_HEADER = ["priority", "status", "word", "count", "word_lists", "base_score", "categories", "notes"]


def flag_rows(final, flags, repairs):
    rows = []
    for w, items in flags.items():
        rec = final[w]
        prio = "high" if any(c in HIGH for c, _ in items) else "normal"
        rows.append([prio, "entry", w, rec["count"], " ".join(LIST_NAMES[c] for c in rec["lists"]), rec["score"],
                     "; ".join(c for c, _ in items), "; ".join(n for _, n in items if n)])
    for r in repairs["brackets"]:
        if r["bracket"] == "аттьшъ":
            rows.append(["high", "not an entry", r["bracket"], "", "", "", F_BRACKET,
                         f"«{r['field']}» (Russian headword «{r['headword']}»): probably «аттынъ»; "
                         "read as a gloss, so it adds no word"])
    rows.sort(key=lambda row: (row[0] != "high", row[6], -(row[3] or 0) if isinstance(row[3], int) else 0, row[2]))
    return rows


def write_reviews(review, log, merge_rows, removed_pairs, rows, reconciliation, manifest, summary):
    os.makedirs(review, exist_ok=True)

    def table(name, header, body):
        with open(os.path.join(review, name), "w", encoding="utf-8", newline="") as f:
            wr = csv.writer(f, lineterminator="\n")
            wr.writerow(header)
            wr.writerows(body)

    table("corrections.csv", ["rule", "action", "entry", "v0_base_score", "base_score", "note"],
          sorted(log, key=lambda r: (r[0], r[1], r[2])))
    table("merges.csv", ["source", "target", "rule", "source_base_score", "target_base_score_before",
                         "target_base_score_after"], merge_rows)
    table("removed_pairs.csv", ["prev", "word", "v0_weight", "adjacent_occurrences", "reason"],
          [[r["prev"], r["word"], r["v0_weight"], r["adjacent_occurrences"], r["reason"]] for r in removed_pairs])
    table("flagged.csv", FLAG_HEADER, rows)
    table("high_priority.csv", FLAG_HEADER, [r for r in rows if r[0] == "high"])
    table("reconciliation.csv", ["step", "words", "corpus_count_total", "base_score_total", "bigrams",
                                 "bigram_weight_total"], reconciliation)
    for name, payload in (("manifest.json", manifest), ("summary.json", summary)):
        with open(os.path.join(review, name), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1, sort_keys=False)
            f.write("\n")


# ----------------------------------------------------------------- validation
# Pinned so that a rule change cannot slip through unnoticed.
EXPECTED_WORDS = 17145
EXPECTED_BIGRAMS = 2317
EXPECTED_SCORE_TOTAL = 537506
EXPECTED_BIGRAM_WEIGHT = 6737


def validate(out):
    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    wp, bp = os.path.join(out, WORDS_ARTIFACT + ".sqlite"), os.path.join(out, BIGRAMS_ARTIFACT + ".sqlite")
    wc, bc = ro(wp), ro(bp)
    for con, table, artifact_name, create, expected in ((wc, "words", WORDS_ARTIFACT, WORDS_SQL, EXPECTED_WORDS),
                                                        (bc, "bigrams", BIGRAMS_ARTIFACT, BIGRAMS_SQL,
                                                         EXPECTED_BIGRAMS)):
        meta = dict(con.execute("SELECT key, value FROM meta"))
        n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        check(f"{artifact_name}: meta.artifact", meta.get("artifact") == artifact_name, meta.get("artifact"))
        check(f"{artifact_name}: meta.row_count == COUNT(*) ({n})", meta.get("row_count") == str(n),
              meta.get("row_count"))
        check(f"{artifact_name}: {expected} rows (cleanup version {CLEANUP_VERSION})", n == expected, str(n))
        for k, v in (("schema_version", SCHEMA_VERSION), ("content_version", CONTENT_VERSION),
                     ("normalization_version", NORMALIZATION_VERSION),
                     ("normalization_profile", NORMALIZATION_PROFILE), ("min_reader_schema", MIN_READER_SCHEMA),
                     ("cleanup_version", CLEANUP_VERSION), ("language", LANGUAGE)):
            check(f"{artifact_name}: meta.{k} == {v}", meta.get(k) == str(v), meta.get(k))
        for k in ("generated_at", "sources", "derived_from"):
            check(f"{artifact_name}: meta.{k} present", bool(meta.get(k)))
        check(f"{artifact_name}: schema is the General Keyboard artifact shape",
              table_sql(con) == {table: create, "meta": META_SQL})
        check(f"{artifact_name}: page_size 4096", con.execute("PRAGMA page_size").fetchone()[0] == 4096)
        check(f"{artifact_name}: vacuumed", con.execute("PRAGMA freelist_count").fetchone()[0] == 0)
        check(f"{artifact_name}: integrity_check", con.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    words = dict(wc.execute("SELECT word, base_score FROM words"))
    pairs = list(bc.execute("SELECT prev, word, weight FROM bigrams"))
    bad = [w for w in words if canonical(w) != w]
    check("every word is canonical under the Nogai profile", not bad, ", ".join(bad[:5]))
    bad = [w for w in words if not is_valid_token(w)]
    check("every word passes the token contract", not bad, ", ".join(bad[:5]))
    bad = [w for w in words if not ALPHABET_RE.fullmatch(w)]
    check("every word uses only а–я, ё and inner hyphens", not bad, ", ".join(bad[:5]))
    check("no palochka (U+04C0, U+04CF) anywhere", not any(ch in _PALOCHKAS for w in words for ch in w))
    check("no combining mark is left in a word", not any(unicodedata.combining(ch) for w in words for ch in w))
    check("no two signs in a row", not any(re.search("[ьъ]{2}", w) for w in words))
    for w in ("соьз", "уьйкен", "куьн", "аьр", "сенинъ", "мага", "онынъ", "юлдыз", "кайда", "уйклатув", "тири"):
        check(f"«{w}» is a row", w in words)
    for w in ("переносном", "значении", "очень", "сделать", "что-л", "улдыз", "енинъ", "нга", "йулдыз", "соъз",
              "сизинь"):
        check(f"«{w}» is not a row", w not in words)
    total = sum(words.values())
    check(f"base scores add up to {EXPECTED_SCORE_TOTAL}", total == EXPECTED_SCORE_TOTAL, str(total))
    check("every base_score >= 1", all(s >= 1 for s in words.values()))
    bad = [(a, b) for a, b, _ in pairs if a not in words or b not in words]
    check("both words of every pair are rows of the words artifact", not bad, str(bad[:3]))
    check(f"every pair weight >= {MIN_PAIR_WEIGHT}", all(v >= MIN_PAIR_WEIGHT for _, _, v in pairs))
    total = sum(v for _, _, v in pairs)
    check(f"pair weights add up to {EXPECTED_BIGRAM_WEIGHT}", total == EXPECTED_BIGRAM_WEIGHT, str(total))
    keys = {(a, b) for a, b, _ in pairs}
    check("«бир аз» and «йок этуьв» are pairs", ("бир", "аз") in keys and ("йок", "этуьв") in keys)
    check("«переносном значении» and «дай дей» are not pairs",
          ("переносном", "значении") not in keys and ("дай", "дей") not in keys)
    wc.close()
    bc.close()
    return results


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=DEFAULT_SOURCE, help="folder with the five v0 nog_* files")
    ap.add_argument("--out", default=DEFAULT_OUT, help="where the two artifacts are written")
    ap.add_argument("--review", default=DEFAULT_REVIEW, help="where the review files are written")
    ap.add_argument("--validate", action="store_true", help="only validate the artifacts in --out")
    ap.add_argument("--print-pins", action="store_true", help="print the SHA-256 of scripts/data and stop")
    args = ap.parse_args()

    def report(results):
        for name, ok, detail in results:
            print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
        return 0 if all(ok for _, ok, _ in results) else 1

    if args.print_pins:
        for name in REPAIR_SHA256:
            print(f'    "{name}": "{sha256(os.path.join(DATA, name))}",')
        return 0
    if args.validate:
        return report(validate(args.out))
    try:
        guard_existing(args.out)
        words, pairs, v0_meta, stats = load(args.source)
        repairs = load_repairs()
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    a = audit(words, pairs)
    hard = {k: a[k] for k in ("not_nfc", "not_lowercase", "not_canonical", "canonical_collisions",
                              "contract_invalid", "outside_alphabet", "latin_letters", "palochka",
                              "replacement_or_control_chars", "score_formula_mismatch", "count_mismatch")
            if a[k]}
    if hard or a["bigram_orphans"] or a["bigram_weight_below_2"]:
        print("error: the v0 data breaks an assumption of this build:",
              json.dumps(hard, ensure_ascii=False)[:2000], file=sys.stderr)
        return 2

    try:
        reread, reread_pairs, log = apply_source_reading(words, pairs, repairs)
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    def totals(ws, ps):
        return [len(ws), sum(r["count"] for r in ws.values()), sum(r["score"] for r in ws.values()),
                len(ps), sum(ps.values())]

    # ---- reconciliation of the source reading, step by step
    by_rule = defaultdict(lambda: [0, 0, 0])      # words, count, score
    for r in repairs["removed"]:
        rule = REMOVAL_RULE[r["reason"]]
        by_rule[("removed", rule)][0] -= 1
        by_rule[("removed", rule)][1] -= words[r["word"]]["count"]
        by_rule[("removed", rule)][2] -= words[r["word"]]["score"]
    for rule, action, w, _, score, _ in log:
        if action == "row restored":
            by_rule[("restored", rule)][0] += 1
            by_rule[("restored", rule)][1] += reread[w]["count"]
            by_rule[("restored", rule)][2] += score
        elif action == "count corrected":
            by_rule[("corrected", rule)][1] += reread[w]["count"] - words[w]["count"]
            by_rule[("corrected", rule)][2] += reread[w]["score"] - words[w]["score"]
    reconciliation = [["v0 (keyboard_data_v0.zip, nog)"] + totals(words, pairs)]
    labels = {"removed": "rows removed", "restored": "rows restored", "corrected": "rows kept, count corrected"}
    for (kind, rule), (n, c, s) in sorted(by_rule.items(), key=lambda kv: (["removed", "restored", "corrected"].index(kv[0][0]), kv[0][1])):
        reconciliation.append([f"{labels[kind]}: {rule}", n, c, s, 0, 0])
    gone = repairs["removed_pairs"]
    for reason in sorted({r["reason"] for r in gone}):
        sel = [r for r in gone if r["reason"] == reason]
        reconciliation.append([f"P1 pairs removed: {reason}", 0, 0, 0, -len(sel), -sum(int(r["v0_weight"]) for r in sel)])
    new = {k: v for k, v in reread_pairs.items() if k not in pairs}
    reconciliation.append(["P1 + F1 pairs new (weight 2 or more only after the repair)", 0, 0, 0, len(new), sum(new.values())])
    delta = sum(v - pairs[k] for k, v in reread_pairs.items() if k in pairs)
    reconciliation.append(["P1 + F1 pairs kept, weight corrected", 0, 0, 0, 0, delta])
    reconciliation.append(["the sources read again"] + totals(reread, reread_pairs))
    mid = len(reconciliation) - 1
    for i in range(1, 6):
        if sum(r[i] for r in reconciliation[:-1]) != reconciliation[-1][i]:
            print(f"error: the reconciliation of the source reading does not add up (column {i})", file=sys.stderr)
            return 2

    # ---- the spelling rules
    final = {w: dict(r) for w, r in reread.items()}
    merges = plan_merges(final)
    final_pairs, merge_rows, rekeyed = apply_merges(final, reread_pairs, merges)
    for rule in (S1, S2, M1):
        sel = [m for m in merge_rows if m[2] == rule]
        if sel:
            reconciliation.append([f"merged: {rule}", -len(sel), 0,
                                   sum(m[5] - m[4] - m[3] for m in sel), 0, 0])
    reconciliation.append(["pairs re-keyed by the merges", 0, 0, 0, len(final_pairs) - len(reread_pairs), 0])
    reconciliation.append(["this dictionary"] + totals(final, final_pairs))
    for i in range(1, 6):
        if sum(r[i] for r in reconciliation[mid:-1]) != reconciliation[-1][i]:
            print(f"error: the reconciliation of the merges does not add up (column {i})", file=sys.stderr)
            return 2

    flags = flag_entries(final)
    rows = flag_rows(final, flags, repairs)

    manifest = {
        "archive": {"file": "keyboard_data_v0.zip", "sha256": ARCHIVE_SHA256, "folder": "keyboard_data/",
                    "built": v0_meta.get("generated_at"), "language": LANGUAGE},
        "v0_files": V0_SHA256,
        "v0_sources": stats.get("sources"),
        "upstream": UPSTREAM,
        "source_reading_tables": REPAIR_SHA256,
        "not_used": {
            "example2": "the Russian translations of the examples (v0 read them)",
            "definition1": "958 short notes on the Nogai side of the same dictionary («ат», «Оьзбекстандагы "
                           "кала», «(устаревшее)»); v0 did not read them and neither does this build",
            "latin_entries": "98 entries of the dictionary written in the Latin alphabet",
            "agisight_frequencies": "the letter counts of Agisight/rf-keyboard-corpora (FineWeb-2): used for "
                                    "the layout, not for the dictionary",
        },
    }
    by_action = Counter((rule, action) for rule, action, *_ in log)
    by_cat = Counter(c for items in flags.values() for c, _ in items)
    russian_removed = [r for r in repairs["removed"] if r["reason"].startswith("Russian")]
    summary = {
        "input": {"v0_generated_at": v0_meta.get("generated_at"), "v0_sources": stats.get("sources"),
                  "v0_replayed_exactly": repairs["reading"]["v0_replayed_exactly"],
                  "source_reading": repairs["reading"]},
        "audit_of_v0": a,
        "changes": {
            "by_rule_and_action": {f"{rule}: {action}": n for (rule, action), n in sorted(by_action.items())},
            "rows_removed": len(repairs["removed"]),
            "rows_removed_russian": len(russian_removed),
            "rows_removed_fragments": len(repairs["removed"]) - len(russian_removed),
            "rows_restored": sum(1 for _, action, *_ in log if action == "row restored"),
            "rows_recounted": sum(1 for _, action, *_ in log if action == "count corrected"),
            "rows_unchanged": sum(1 for w, r in reread.items()
                                  if w in words and (words[w]["count"], words[w]["lex"]) == (r["count"], len(r["lists"]))),
            "merged": dict(Counter(m[2] for m in merge_rows)),
            "pairs_removed": len(gone),
            "pairs_new": len(new),
            "pairs_rekeyed_by_merges": rekeyed,
            "respelled": 0,
        },
        "flags": {"listed": len(rows),
                  "entries": len(flags),
                  "high_priority": sum(1 for r in rows if r[0] == "high"),
                  "by_category": dict(sorted(by_cat.items(), key=lambda kv: (-kv[1], kv[0])))},
        "output": {"words": len(final), "bigrams": len(final_pairs),
                   "words_with_a_count": sum(1 for r in final.values() if r["count"]),
                   "word_lists_only": sum(1 for r in final.values() if not r["count"]),
                   "corpus_count_total": sum(r["count"] for r in final.values()),
                   "corpus_count_total_v0": a["corpus_tokens"],
                   "base_score_total": sum(r["score"] for r in final.values()),
                   "base_score_total_v0": a["base_score_total"],
                   "bigram_weight_total": sum(final_pairs.values()),
                   "bigram_weight_total_v0": a["bigram_weight_total"],
                   "with_ae": sum(1 for w in final if "аь" in w), "with_ng": sum(1 for w in final if "нъ" in w),
                   "with_oe": sum(1 for w in final if "оь" in w), "with_ue": sum(1 for w in final if "уь" in w),
                   "hyphenated": sum(1 for w in final if "-" in w),
                   "top_words": [w for w, _ in sorted(final.items(), key=lambda kv: (-kv[1]["score"], kv[0]))[:30]],
                   "top_pairs": [f"{x} {y}" for (x, y), _ in
                                 sorted(final_pairs.items(), key=lambda kv: (-kv[1], kv[0]))[:20]]},
    }
    write_artifacts(args.out, final, final_pairs)
    write_reviews(args.review, log, merge_rows, gone, rows, reconciliation, manifest, summary)
    results = validate(args.out)
    print(json.dumps({k: summary[k] for k in ("changes", "flags", "output")}, ensure_ascii=False, indent=1))
    for r in reconciliation:
        print("   ", r)
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
