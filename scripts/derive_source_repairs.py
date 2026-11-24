#!/usr/bin/env python3
"""Read the sources of the v0 Nogai data again, the way they are written.

The v0 Nogai data (keyboard_data_v0.zip, nog_*) was built by build_kb_data.py
from three sources. This script

  1. replays the v0 reading on the pinned copies of those sources and checks
     that it gives the v0 files exactly (23,090 words, 3,564 pairs, every
     count), which proves they are the data v0 read;
  2. reads them again, repairing what the v0 reader got wrong;
  3. accounts for every v0 token: kept, or removed for a stated reason;
  4. writes the result to scripts/data/ for scripts/build_dictionary.py.

What the v0 reader got wrong

  The main source is a Russian-Nogai dictionary (github.com/shakhmirzovrenat,
  «Dataset-of-nogai-language.», collected from Glosbe). Each entry has a
  Russian headword `ru`, its Nogai equivalents `nog`, and sometimes a Nogai
  example `example1` with its Russian translation `example2`.

  G  The `nog` field explains senses in Russian, in brackets:
     «(очень, крайне) бек». v0 read the bracket as Nogai text, so «очень» and
     «крайне» became Nogai words and «переносном значении» the most frequent
     Nogai word pair. Here a bracket is read only when it holds Nogai words
     («йонып (шабып) тегислев»); see classify_bracket().
  T  `example2` is the Russian translation of `example1`. v0 read both and
     relied on a filter (a line is dropped when 60 % of its words are in a
     Russian word list) to throw the Russian ones out; 749 of 3,237 got
     through. Here `example2` is not read.
  F  The same filter threw out 1,220 Nogai lines: lines with a long Russian
     bracket («(заставить уснуть) уйклатув»), and Nogai lines made of words
     that Russian also has («ак ас», «тик яр», «кара май»). Here the filter
     is not used, and those lines are read.
  A  Suffixes are cited as «-ден», «=тан». v0 read them as the words «ден»,
     «тан». Here a citation with a leading or trailing «-» or «=» is not a
     word.
  L  A word typed with a Latin twin («мeн» with a Latin e) was cut at that
     letter, because v0 looked for Cyrillic letters before it repaired the
     twins. Here the twins are repaired first.
  P  v0 paired every two neighbouring words of a line, also across a comma
     or a bracket («кувув, кувып шыгарув» gave the pair «кувув кувып»).
     Here two words are a pair only when nothing but a space stands between
     them.
  Q  A one-word `nog` field went to a word list as it stood, so «кайда?»
     was rejected for its question mark. Here it is read like any other
     text.
  I  The IDS list stores «й» as «и» + U+0306 COMBINING BREVE. v0 looked for
     Cyrillic letters only, so «кайыр» became «каи» and «ыр». Here the form
     is composed (NFC) first.
  X  In the Apertium lexicon the personal pronouns are stored as a first
     letter («м», «с», «о») plus an ending («ага», «енинъ», «нда»). v0 read
     the endings as words. Here the forms are put together («мага»,
     «сенинъ», «онда») and the endings are not words.

What is NOT changed: which lines are read (v0's own duplicate test is kept,
so a Nogai word keeps the count v0 gave it wherever v0 read it correctly),
the scoring rule, and the rule that a pair needs two occurrences. No count
is estimated: every number is a count of occurrences in the pinned files.

Usage, from the repository root:

    python3 -I scripts/derive_source_repairs.py
    python3 -I scripts/derive_source_repairs.py --refresh-russian PATH/clean_data_with_frequency.csv.zip

Python 3 standard library only. The inputs are pinned by SHA-256; the output
is deterministic, and scripts/build_dictionary.py pins it in turn.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V0 = os.path.join(REPO, "dictionary-source", "original-v0")
UP = os.path.join(REPO, "dictionary-source", "upstream")
DATA = os.path.join(REPO, "scripts", "data")

DATASET = os.path.join(UP, "nogai-dataset-3ff8a74", "nogai_russian_dictionary.json")
LEXC = os.path.join(UP, "apertium-nog-09fdef0", "apertium-nog.nog.lexc")
IDS = os.path.join(UP, "ids-bf6c9f8", "forms_nogai_73.csv")
RUSSIAN = os.path.join(DATA, "russian_words_in_sources.txt")
HAND = os.path.join(DATA, "bracket_decisions.tsv")

PINNED = {
    os.path.join(V0, "nog_words.tsv"): "5e6a3cbc12d719f46e67c65debcc51762535b5a0e0ab40177011c4747652459e",
    os.path.join(V0, "nog_bigrams.tsv"): "08cf7ab0226105ccfaac229e1a7fa7441b2dbd135b59e095265b35d86b097b5d",
    DATASET: "5d7aa550d9504cf2d1449d33f2b4b7bf182a48efd28cedc311c4da0d74ae7f83",
    LEXC: "1af6945cf18d7929d6a8a8a3078cde53030a8eba525fa4b187d5b9d31b07b026",
    IDS: "7f6554891085ad8cb473fec6cbdc9afe1484325dfdded305d1d00becf459c711",
    RUSSIAN: "6b1718a621ab61c0e3c6d2d3d99b94d836263a85246e67a011523042728c93d0",
    HAND: "e227c9e4d592d77c27a99078d3ced0fec22062da68eb7ddde1c14f7c1e59ac3f",
}
# data/clean_data_with_frequency.csv.zip of
# github.com/LingConLab/Cyrillic_languages_identification_models_and_data_store
# at 3c18d336b0258b2bfefaac73ba84da3e667bd101: the word list v0 used as its
# Russian filter (the rows with language «Russian»). Only --refresh-russian
# reads it; the build reads the extract in scripts/data/.
LID_ZIP_SHA256 = "f23b302724fbc53d60fcdd4dc4ccba83b61a32e6a5c52bd8f9ede25b5c788623"

# What v0 reported about its own reading (nog_stats.json).
V0_STATS = {"sentences": 18313, "tokens": 60909, "dropped_russian": 3720, "dup": 577,
            "glosbe_words": 5210, "apertium_nog": 1299, "ids": 1642,
            "words_total": 23090, "bigrams_total": 3564, "bigram_pairs_raw": 36501}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------- the v0 reading
# build_kb_data.py, verbatim in what matters for the Nogai recipe.
_CYR = "Ѐ-ӿ"
TOKEN_RE = re.compile(rf"[{_CYR}]+(?:-[{_CYR}]+)*")
LATIN_TO_CYR = {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
                "k": "к", "m": "м", "t": "т", "b": "ь", "h": "н"}
STD = set("абвгдежзийклмнопрстуфхцчшщъыьэюяё")
_HYPHEN_BREAK = re.compile(rf"([{_CYR}])-\s*\n\s*(?=[а-яёӏӀ])")
_SOFT_HYPHEN = re.compile("[­​‌‍﻿]")
RU_RATIO_DROP = 0.6


def normalize_token(tok):
    tok = unicodedata.normalize("NFC", tok).strip().lower()
    tok = "".join(LATIN_TO_CYR.get(ch, ch) for ch in tok)
    return unicodedata.normalize("NFC", tok)


def valid_token(tok):
    if not tok or len(tok) > 40:
        return False
    if tok.startswith("-") or tok.endswith("-") or "--" in tok:
        return False
    if sum(0 if ch in ("ӏ", "ь", "ъ", "-") else 1 for ch in tok) < 2:
        return False
    return all(ch in STD or ch == "-" for ch in tok)


def repair_text(text):
    text = unicodedata.normalize("NFC", text)
    text = _SOFT_HYPHEN.sub("", text)
    return _HYPHEN_BREAK.sub(r"\1", text)


def v0_tokens(text):
    return [normalize_token(t) for t in TOKEN_RE.findall(text)]


def load_dataset():
    with open(DATASET, encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw[raw.index("["):])


def lexc_entries():
    """(lexicon name, lemma, surface, continuation) of every entry line, as v0 matched them."""
    out = []
    section = None
    with open(LEXC, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"^LEXICON\s+(\S+)", line)
            if m:
                section = m.group(1)
                continue
            line = line.split("!")[0].strip()
            m = re.match(r"^(\S+?)(?:%<[^:]*)?:(\S+)\s+(\S+)\s*;", line)
            if m:
                out.append((section, m.group(1), m.group(2), m.group(3)))
    return out


def _lexc_clean(s):
    return re.sub(r"\{[^}]*\}", "", s.replace("%", ""))


def v0_lexc_words():
    words = []
    for _, lemma, surface, _ in lexc_entries():
        for s in (lemma, surface):
            s = _lexc_clean(s)
            if TOKEN_RE.fullmatch(s):
                words.append(s)
    return words


def ids_rows():
    with open(IDS, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def v0_ids_words(rows):
    words = []
    for row in rows:
        for part in re.split(r"[;,/]", row["Form"]):
            words.extend(TOKEN_RE.findall(part))
    return words


def v0_lexicon(words):
    return {w for w in (normalize_token(x) for x in words) if valid_token(w)}


def dataset_lines(d):
    """v0's src_glosbe_nogai: (kind, entry index, text) of every line, and the one-word fields."""
    lines, single = [], []
    for i, e in enumerate(d):
        nog = (e.get("nog") or "").strip()
        if nog:
            (lines if " " in nog else single).append(("nog", i, nog))
        for k in ("example1", "example2"):
            v = (e.get(k) or "").strip()
            if v:
                lines.append((k, i, v))
    return lines, single


# ----------------------------------------------------------------- the repaired reading
BRACKET = re.compile(r"\(([^()]*)\)")
_LATIN = "A-Za-zÀ-ɏ"
_NOGAI_ONLY = re.compile(r"[аоу]ь|нъ(?![еёюя])")   # аь оь уь нъ: not Russian spellings


def fix_brackets(s):
    """«{» typed for «(» (7 fields), a gloss whose «(» is missing (9), one never closed (1)."""
    s = s.replace("{", "(")
    if ")" in s and ("(" not in s or s.index(")") < s.index("(")):
        s = "(" + s
    if s.count("(") > s.count(")"):
        s = s + ")"
    return s


def split_field(text):
    """[(piece of text, None or the bracket's content)] in order."""
    s = fix_brackets(repair_text(text))
    parts, pos = [], 0
    for m in BRACKET.finditer(s):
        parts.append((s[pos:m.start()], False))
        parts.append((m.group(1), True))
        pos = m.end()
    parts.append((s[pos:], False))
    return parts


def scan(text):
    """Every v0 token of a piece of text with what it is.

    Returns [(kind, token, gap_before_is_space, raw)], kind one of
      word   a Nogai word as written (also a word repaired from Latin twins)
      affix  a suffix or prefix citation («-ден», «=тан», «ал-»)
      cut    a piece of a word typed in two scripts, which v0 read alone
      other  a token v0 did not count (one letter, a letter outside а-я ё)
    and, for a word that v0 could not read because of a Latin twin,
      whole  the repaired word (not a v0 token).
    """
    out = []
    prev_end = 0
    for m in TOKEN_RE.finditer(text):
        a, b = m.span()
        before, after = text[a - 1] if a else "", text[b] if b < len(text) else ""
        gap = text[prev_end:a]
        space_only = bool(out) and gap.strip(" \t") == "" and gap != ""
        prev_end = b
        tok = normalize_token(m.group())
        counted = valid_token(tok)
        if re.match(f"[{_LATIN}]", before or " ") or re.match(f"[{_LATIN}]", after or " "):
            # part of a word typed in two scripts
            start, end = a, b
            while start and re.match(rf"[{_CYR}{_LATIN}\-]", text[start - 1]):
                start -= 1
            while end < len(text) and re.match(rf"[{_CYR}{_LATIN}\-]", text[end]):
                end += 1
            raw = text[start:end]
            out.append(("cut" if counted else "other", tok, False, raw))
            if a == TOKEN_RE.search(text, start).start():      # once per mixed word
                whole = normalize_token(raw)
                if valid_token(whole):
                    out.append(("whole", whole, False, raw))
            continue
        lead = before in "-=" and before != "" and (a < 2 or text[a - 2] in " \t(,;")
        trail = after in "-=" and after != "" and (b + 1 >= len(text) or text[b + 1] in " \t),;")
        if lead or trail:
            out.append(("affix" if counted else "other", tok, False, m.group()))
        else:
            out.append(("word" if counted else "other", tok, space_only, m.group()))
    return out


class Reader:
    """Classifies brackets and reads fields. Needs the whole dataset first (evidence)."""

    def __init__(self, d, russian, hand):
        self.russian = russian
        self.hand = hand
        self.ru_side = set()
        for e in d:
            for k in ("ru", "example2", "definition2"):
                self.ru_side.update(v0_tokens(repair_text(e.get(k) or "")))
        # Nogai evidence: what stands outside every bracket of a Nogai field.
        self.outside = Counter()
        self.brackets = Counter()
        self.bracket_where = {}
        for e in d:
            for k in ("nog", "example1"):
                for piece, br in split_field(e.get(k) or ""):
                    if br:
                        self.brackets[piece] += 1
                        self.bracket_where.setdefault(piece, (e.get("ru") or "", e.get(k) or ""))
                    else:
                        self.outside.update(t for kind, t, *_ in scan(piece) if kind in ("word", "whole"))
        self.bracket_class = {seg: self._classify(seg) for seg in self.brackets}

    def is_russian(self, tok):
        return tok in self.russian or tok in self.ru_side

    def _classify(self, seg):
        """(class, basis). class: gloss (Russian, not read) | nogai (read) | affixes (suffix list)."""
        toks = [t for kind, t, *_ in scan(seg) if kind in ("word", "whole")]
        if not toks:
            return ("affixes" if any(kind == "affix" for kind, *_ in scan(seg)) else "gloss", "no word in it")
        rus = [t for t in toks if self.is_russian(t) and not self.outside[t]]
        nog = [t for t in toks if (self.outside[t] and not self.is_russian(t)) or _NOGAI_ONLY.search(t)]
        if rus and not nog:
            return "gloss", "a word that only Russian text has"
        if nog and not rus:
            return "nogai", "a word that only Nogai text has"
        decided = self.hand.get(seg)
        if decided:
            return decided, "checked by hand"
        return "gloss", "undecided: no word known to either side; read as a gloss, as 96 % of brackets are"

    def read(self, text):
        """[(kind, token, joins_previous, raw, capital)] of a field; kind as scan() plus gloss."""
        out = []
        for piece, br in split_field(text):
            cls = self.bracket_class[piece][0] if br else "nogai"
            first = True
            for kind, tok, space_only, raw in scan(piece):
                if cls == "gloss" and kind in ("word", "affix", "cut"):
                    out.append(("gloss", tok, False, raw))
                elif cls == "gloss":
                    if kind != "whole":
                        out.append((kind, tok, False, raw))
                else:
                    out.append((kind, tok, space_only and not first, raw))
                first = False
        return out


def runs_of(items):
    """Runs of words with nothing but spaces between them."""
    runs, cur = [], []
    for kind, tok, joins, _ in items:
        if kind in ("word", "whole"):
            if joins and cur and kind == "word":
                cur.append(tok)
            else:
                if cur:
                    runs.append(cur)
                cur = [tok]
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


# ----------------------------------------------------------------- Apertium, IDS
def lexc_words():
    """(words, endings v0 read as words, pronoun forms put together)."""
    entries = lexc_entries()
    order = []
    for sec, *_ in entries:
        if sec not in order:
            order.append(sec)
    # The pronoun paradigms: entries without a lemma, whose surface is an ending.
    endings = defaultdict(list)
    for sec, lemma, surface, _ in entries:
        if sec.startswith("PRON-") and lemma.startswith("%<"):
            s = _lexc_clean(surface)
            if TOKEN_RE.fullmatch(s):
                endings[sec].append(s)
    words, pieces, composed = [], set(), set()
    for sec, lemma, surface, cont in entries:
        if sec.startswith("PRON-") and lemma.startswith("%<"):
            s = _lexc_clean(surface)
            if TOKEN_RE.fullmatch(s) and valid_token(normalize_token(s)):
                pieces.add(normalize_token(s))
            continue
        for s in (lemma, surface):
            s = _lexc_clean(s)
            if TOKEN_RE.fullmatch(s):
                words.append(s)
        if cont in endings:
            stem = _lexc_clean(surface)
            for ending in endings[cont]:
                form = normalize_token(stem + ending)
                if valid_token(form):
                    words.append(form)
                    composed.add(form)
    return words, pieces, composed


def ids_words(rows):
    words = []
    for row in rows:
        form = unicodedata.normalize("NFC", row["Form"])
        for part in re.split(r"[;,/]", form):
            words.extend(TOKEN_RE.findall(part))
    return words


# ----------------------------------------------------------------- output
def write(name, header, rows):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        wr = csv.writer(f, delimiter="\t", lineterminator="\n")
        wr.writerow(header)
        wr.writerows(rows)
    return path


def refresh_russian(zip_path):
    """scripts/data/russian_words_in_sources.txt: the words of v0's Russian filter that occur in the sources."""
    if sha256(zip_path) != LID_ZIP_SHA256:
        raise SystemExit("this is not the pinned clean_data_with_frequency.csv.zip")
    ru = set()
    with zipfile.ZipFile(zip_path) as z:
        with z.open("clean_data_with_frequency.csv") as raw:
            r = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
            next(r)
            for row in r:
                if row[5] == "Russian":
                    try:
                        if int(row[6]) >= 1:
                            ru.add(row[1].lower())
                    except ValueError:
                        pass
    seen = set()
    for e in load_dataset():
        for v in e.values():
            seen.update(v0_tokens(repair_text(v or "")))
    keep = sorted(ru & seen)
    os.makedirs(DATA, exist_ok=True)
    with open(RUSSIAN, "w", encoding="utf-8") as f:
        f.write("\n".join(keep) + "\n")
    print(f"Russian filter: {len(ru)} words, {len(keep)} of them occur in the dataset")
    print(f'    RUSSIAN: "{sha256(RUSSIAN)}"')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh-russian", metavar="ZIP",
                    help="rebuild scripts/data/russian_words_in_sources.txt from the LingConLab zip")
    ap.add_argument("--print-pins", action="store_true", help="print the SHA-256 of the inputs and stop")
    args = ap.parse_args()
    if args.refresh_russian:
        refresh_russian(args.refresh_russian)
        return 0
    if args.print_pins:
        for path in PINNED:
            print(f'    {os.path.relpath(path, REPO)}: "{sha256(path)}"')
        return 0
    for path, digest in PINNED.items():
        if sha256(path) != digest:
            print(f"error: {os.path.relpath(path, REPO)} is not the pinned file (sha256 {sha256(path)})",
                  file=sys.stderr)
            return 2

    with open(RUSSIAN, encoding="utf-8") as f:
        russian = set(f.read().split())
    with open(HAND, encoding="utf-8", newline="") as f:
        hand = {r["bracket"]: r["reading"] for r in csv.DictReader(f, delimiter="\t")}
    with open(os.path.join(V0, "nog_words.tsv"), encoding="utf-8", newline="") as f:
        v0_words = {r["word"]: (int(r["count"]), int(r["lexicon_sources"]))
                    for r in csv.DictReader(f, delimiter="\t")}
    with open(os.path.join(V0, "nog_bigrams.tsv"), encoding="utf-8", newline="") as f:
        v0_pairs = {(r["prev"], r["word"]): int(r["weight"]) for r in csv.DictReader(f, delimiter="\t")}

    d = load_dataset()
    lines, single = dataset_lines(d)
    rows = ids_rows()
    reader = Reader(d, russian, hand)

    # ---- 1. replay v0 and, on the same lines, read again
    seen = set()
    v0_uni, v0_bi = Counter(), Counter()
    count = Counter()
    acc = defaultdict(Counter)        # word -> what happened to its v0 occurrences
    pairs = Counter()
    capital, upper, occurrences = Counter(), Counter(), Counter()
    first_ru = {}
    stat = Counter()
    line_log = []
    for kind, i, s in lines:
        text = repair_text(s)
        toks = [t for t in v0_tokens(text) if valid_token(t) or t in russian]
        if not toks:
            stat["lines without a token"] += 1
            continue
        key = " ".join(toks)
        if key in seen:
            stat["v0: duplicate lines, not read"] += 1
            continue
        seen.add(key)
        dropped = len(toks) >= 2 and sum(1 for t in toks if t in russian) / len(toks) >= RU_RATIO_DROP
        valid = [t for t in toks if valid_token(t)]
        if dropped:
            stat["v0: lines dropped as Russian"] += 1
        else:
            stat["v0: lines read"] += 1
            stat["v0: tokens"] += len(valid)
            v0_uni.update(valid)
            v0_bi.update(zip(valid, valid[1:]))
        if kind == "example2":
            stat["example2 (Russian translations): read by v0" if not dropped
                 else "example2 (Russian translations): dropped by v0"] += 1
            if not dropped:
                stat["tokens removed: Russian translation (example2)"] += len(valid)
                for t in valid:
                    acc[t]["translation"] += 1
            continue
        items = reader.read(s)
        # every v0 token of this line is accounted for, in order
        assert [t for k, t, *_ in items if k in ("word", "gloss", "affix", "cut")] == valid, (s, items, valid)
        kept = [(k, t, raw) for k, t, _, raw in items if k in ("word", "whole")]
        if not dropped:
            for k, t, *_ in items:
                if k == "gloss":
                    acc[t]["gloss"] += 1
                    stat["tokens removed: Russian gloss in brackets"] += 1
                elif k == "affix":
                    acc[t]["affix"] += 1
                    stat["tokens removed: suffix citation"] += 1
                elif k == "cut":
                    acc[t]["cut"] += 1
                    stat["tokens removed: piece of a word typed in two scripts"] += 1
                elif k == "whole":
                    acc[t]["whole"] += 1
                    stat["tokens restored: word typed with a Latin twin"] += 1
            stat[f"lines read again ({kind})"] += 1
        else:
            if not kept:
                stat["v0-dropped lines with no Nogai word after the repair"] += 1
                continue
            for k, t, _ in kept:
                acc[t]["restored"] += 1
            stat["lines restored (v0 dropped them as Russian)"] += 1
            stat["tokens restored: lines v0 dropped as Russian"] += len(kept)
            if len(line_log) < 100000:
                line_log.append((kind, d[i].get("ru") or "", s, " ".join(t for _, t, _ in kept)))
        for k, t, raw in kept:
            count[t] += 1
            occurrences[t] += 1
            first_ru.setdefault(t, d[i].get("ru") or "")
            if raw[:1].isupper():
                capital[t] += 1
            if raw.isupper() and len(raw) > 1:
                upper[t] += 1
        for run in runs_of(items):
            pairs.update(zip(run, run[1:]))
    stat["tokens of the repaired reading"] = sum(count.values())

    # ---- 2. the word lists
    v0_lex = {"glosbe_words": v0_lexicon(t for _, _, t in single),
              "apertium_nog": v0_lexicon(v0_lexc_words()),
              "ids": v0_lexicon(v0_ids_words(rows))}
    glosbe = set()
    for _, i, s in single:
        for k, t, _, raw in reader.read(s):
            if k in ("word", "whole"):
                glosbe.add(t)
                occurrences[t] += 1
                first_ru.setdefault(t, d[i].get("ru") or "")
                if raw[:1].isupper():
                    capital[t] += 1
                if raw.isupper() and len(raw) > 1:
                    upper[t] += 1
    lexc, lexc_pieces, lexc_composed = lexc_words()
    lex = {"glosbe_words": glosbe, "apertium_nog": v0_lexicon(lexc), "ids": v0_lexicon(ids_words(rows))}

    # ---- 3. the replay must be v0, to the last count
    prior0 = Counter()
    for ws in v0_lex.values():
        prior0.update(ws)
    replay = {w: (v0_uni[w], prior0[w]) for w in set(v0_uni) | set(prior0)}
    replay_pairs = {k: v for k, v in v0_bi.items() if v >= 2 and k[0] in replay and k[1] in replay}
    got = {"sentences": stat["v0: lines read"], "tokens": stat["v0: tokens"],
           "dropped_russian": stat["v0: lines dropped as Russian"], "dup": stat["v0: duplicate lines, not read"],
           "glosbe_words": len(v0_lex["glosbe_words"]), "apertium_nog": len(v0_lex["apertium_nog"]),
           "ids": len(v0_lex["ids"]), "words_total": len(replay), "bigrams_total": len(replay_pairs),
           "bigram_pairs_raw": len(v0_bi)}
    if got != V0_STATS or replay != v0_words or replay_pairs != v0_pairs:
        raise SystemExit(f"the replay does not reproduce v0: {got}")

    # ---- 4. every v0 count is accounted for
    for w in set(v0_uni) | set(count):
        a = acc[w]
        if count[w] != v0_uni[w] - a["gloss"] - a["translation"] - a["affix"] - a["cut"] + a["restored"] + a["whole"]:
            raise SystemExit(f"the counts of {w!r} do not add up")

    prior = Counter()
    for ws in lex.values():
        prior.update(ws)
    final = sorted(w for w in set(count) | set(prior) if count[w] or prior[w])
    final_set = set(final)
    kept_pairs = {k: v for k, v in pairs.items() if v >= 2}
    assert all(a in final_set and b in final_set for a, b in kept_pairs)

    # ---- 5. write
    os.makedirs(DATA, exist_ok=True)

    def lists(w, table):
        return "".join(c for c, name in (("g", "glosbe_words"), ("a", "apertium_nog"), ("i", "ids")) if w in table[name])

    word_rows = []
    for w in final:
        a = acc[w]
        word_rows.append([w, count[w], lists(w, lex), v0_uni[w] if w in v0_words else "",
                          lists(w, v0_lex) if w in v0_words else "",
                          a["gloss"], a["translation"], a["affix"], a["cut"], a["restored"], a["whole"],
                          1 if reader.is_russian(w) else 0, occurrences[w], capital[w], upper[w],
                          first_ru.get(w, "")])
    removed_rows = []
    for w in sorted(set(v0_words) - final_set):
        a = acc[w]
        lost = [name for name in ("glosbe_words", "apertium_nog", "ids") if w in v0_lex[name]]
        if a["gloss"] and a["translation"]:
            reason = "Russian: in sense glosses and in translations of examples"
        elif a["gloss"]:
            reason = "Russian: in sense glosses (brackets) only"
        elif a["translation"]:
            reason = "Russian: in translations of examples only"
        elif a["affix"]:
            reason = "suffix citation"
        elif a["cut"]:
            reason = "piece of a word typed in two scripts"
        elif w in lexc_pieces and "apertium_nog" in lost:
            reason = "ending of a pronoun form in the Apertium lexicon"
        elif "ids" in lost:
            reason = "piece of an IDS form cut at «й» (и + U+0306)"
        elif "glosbe_words" in lost:
            reason = "piece of a one-word field"
        else:
            raise SystemExit(f"{w!r} left the data for no stated reason")
        removed_rows.append([w, v0_words[w][0], lists(w, v0_lex), a["gloss"], a["translation"], a["affix"], a["cut"],
                             reason, 1 if reader.is_russian(w) else 0])
    pair_rows = [[a, b, v, v0_pairs.get((a, b), "")] for (a, b), v in sorted(kept_pairs.items())]
    gone_rows = []
    for (a, b), v in sorted(v0_pairs.items()):
        if (a, b) in kept_pairs:
            continue
        if a not in final_set or b not in final_set:
            reason = "a word of the pair is not a Nogai word"
        elif pairs[(a, b)] == 1:
            reason = "next to each other once only; elsewhere a comma or a bracket stands between them"
        else:
            reason = "never next to each other: a comma, a bracket or a removed word stands between them"
        gone_rows.append([a, b, v, pairs[(a, b)], reason])
    bracket_rows = [[seg, n, reader.bracket_class[seg][0], reader.bracket_class[seg][1],
                     reader.bracket_where[seg][0], reader.bracket_where[seg][1]]
                    for seg, n in sorted(reader.brackets.items())]
    ids_changed = []
    for row in rows:
        old = sorted(v0_lexicon(v0_ids_words([row])))
        new = sorted(v0_lexicon(ids_words([row])))
        if old != new:
            ids_changed.append([row["ID"], unicodedata.normalize("NFC", row["Form"]), " ".join(old), " ".join(new)])
    restored_lines = sorted(set(line_log))

    written = [
        write("source_words.tsv",
              ["word", "count", "lists", "v0_count", "v0_lists", "in_gloss", "in_translation", "as_affix",
               "as_cut_piece", "in_restored_lines", "as_repaired_word", "on_russian_lists", "occurrences",
               "capitalized", "all_capitals", "first_headword"], word_rows),
        write("v0_removed_words.tsv",
              ["word", "v0_count", "v0_lists", "in_gloss", "in_translation", "as_affix", "as_cut_piece", "reason",
               "on_russian_lists"], removed_rows),
        write("source_pairs.tsv", ["prev", "word", "weight", "v0_weight"], pair_rows),
        write("v0_removed_pairs.tsv", ["prev", "word", "v0_weight", "adjacent_occurrences", "reason"], gone_rows),
        write("brackets.tsv", ["bracket", "occurrences", "reading", "basis", "headword", "field"], bracket_rows),
        write("ids_repaired_forms.tsv", ["ids_id", "form", "v0_reading", "reading"], ids_changed),
        write("restored_lines.tsv", ["field", "headword", "text", "words_read"], restored_lines),
    ]
    by_class = Counter()
    for seg, n in reader.brackets.items():
        by_class[reader.bracket_class[seg][0] + " / " + reader.bracket_class[seg][1]] += n
    summary = {
        "v0_replayed_exactly": True,
        "v0": V0_STATS,
        "dataset_entries": len(d),
        "lines": dict(sorted(stat.items())),
        "brackets": {"occurrences": sum(reader.brackets.values()), "distinct": len(reader.brackets),
                     "by_reading": dict(sorted(by_class.items()))},
        "word_lists": {name: {"v0": len(v0_lex[name]), "read_again": len(lex[name]),
                              "restored": len(lex[name] - v0_lex[name]), "removed": len(v0_lex[name] - lex[name])}
                       for name in lex},
        "apertium_pronoun_forms_put_together": sorted(lexc_composed),
        "apertium_endings_not_words": sorted(lexc_pieces),
        "ids_forms_read_differently": len(ids_changed),
        "words": {"v0": len(v0_words), "read_again": len(final), "removed": len(removed_rows),
                  "restored": len(final_set - set(v0_words)),
                  "kept": len(final_set & set(v0_words))},
        "pairs": {"v0": len(v0_pairs), "v0_weight": sum(v0_pairs.values()), "read_again": len(kept_pairs),
                  "read_again_weight": sum(kept_pairs.values()), "removed": len(gone_rows),
                  "new": len(set(kept_pairs) - set(v0_pairs)),
                  "adjacent_pairs_before_threshold": len(pairs)},
    }
    path = os.path.join(DATA, "source_reading.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
        f.write("\n")
    written.append(path)
    print(json.dumps({k: summary[k] for k in ("lines", "brackets", "word_lists", "words", "pairs")},
                     ensure_ascii=False, indent=1))
    for p in written:
        print(f'    "{os.path.basename(p)}": "{sha256(p)}",')
    return 0


if __name__ == "__main__":
    sys.exit(main())
