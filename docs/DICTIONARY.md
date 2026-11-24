# The Nogai dictionary (cleanup version 1)

The keyboard ships two read-only SQLite artifacts in the extension,
`nogai_words.sqlite` (17,145 words, 384 KB) and `nogai_bigrams.sqlite`
(2,317 word pairs, 84 KB). The same files are bundled in Debug and Release.
The schema is General Keyboard's artifact contract
(`GeneralKeyboard-iOS/docs/engine/ARTIFACT_CONTRACT.md`): no extra columns,
no duplicate representations.

They are built in two steps, both reproducible from this repository:

1. `scripts/derive_source_repairs.py` reads the sources of the v0 data
   again, the way they are written, and writes what it found to
   `scripts/data/`;
2. `scripts/build_dictionary.py` takes the v0 files and those tables,
   applies three spelling rules, and writes the artifacts and the review
   files of `dictionary/review/`.

## Source data

`keyboard_data_v0.zip` (SHA-256
`8cec9c22b314373386dbcbbbe1680d765b4f212de655162197af019402b8ac31`, folder
`keyboard_data/`, built 2026-10-11 by `build_kb_data.py`), language code
`nog`. The five Nogai files are in `dictionary-source/original-v0/`,
unmodified, with checksums; the three files v0 read to build them are in
`dictionary-source/upstream/`, pinned by commit (`dictionary-source/README.md`,
`dictionary/review/manifest.json`):

| v0 name | What it is | Licence |
|---|---|---|
| `glosbe_phrases`, `glosbe_words` | A **Russian–Nogai dictionary** collected from Glosbe: 24,340 entries (Russian headword, Nogai equivalents, 3,245 Nogai examples with Russian translations). github.com/shakhmirzovrenat, «Dataset-of-nogai-language.», commit `3ff8a74` | MIT |
| `apertium_nog` | The lexicon of the Apertium transducer for Nogai (`apertium-nog.nog.lexc`, commit `09fdef0`): a word list | GPL v3 |
| `ids` | The Nogai list of the Intercontinental Dictionary Series (list 73, M. Khalilov, 2,031 rows, commit `bf6c9f8`): a word list | CC BY 4.0 |

There is **no running text** behind this dictionary: no newspaper, no
book. Every count is a count of occurrences in the equivalents and
examples of one bilingual dictionary. The v0 README said so itself («сильный
перекос в отглагольные имена на -ув/-уьв»).

v0 scoring, kept here: `base_score = 10 × count + min(9, word lists)`. A
multi-word equivalent or an example is a *line* and its words are counted;
a one-word equivalent only puts the word on the `glosbe_words` list. A
pair is two neighbouring words of a line, kept from two occurrences up.

## Audit of the v0 data

| | |
|---|---|
| Words / pairs | 23,090 / 3,564 |
| Words with a count | 19,109 (60,909 occurrences); 3,981 come from a word list only |
| Character inventory | the 33 Russian letters and the hyphen (549 words). No Latin letters, no palochka, no digits, no controls, no U+FFFD |
| Unicode | all NFC, all lowercase, all canonical under the `nogai-cyrillic` profile; no two rows collapse to one form |
| Contract validity | every row passes `Normalization.isValidToken` |
| Duplicates / malformed rows | none; TSV and SQLite agree exactly |
| Pairs | no orphan words, no weight below 2 |
| Most frequent pair | **`переносном значении`** (56): Russian |

The encoding is clean and nothing is scanned: there is no OCR in this
data. What is wrong is **what v0 took for Nogai**. A quarter of the rows
are Russian words, and the top pair is the Russian for «in the figurative
sense».

### How it happened

`derive_source_repairs.py` first replays the v0 builder on the pinned
sources. The replay gives the v0 files exactly: 18,313 lines, 60,909
tokens, 3,720 lines dropped as Russian, 577 duplicates, 23,090 words with
every count, 3,564 pairs with every weight. So the errors below are errors
of that reading, shown on the same data.

| | What the source has | What v0 did | Here |
|---|---|---|---|
| **G** | The Nogai field explains senses in Russian, in brackets: «(очень, крайне) бек», «(в переносном значении) куьшеюв». 7,452 brackets | read them as Nogai text: 8,357 Russian tokens counted | a bracket is read only when it holds Nogai words |
| **T** | `example2` is the Russian translation of `example1` | read both and trusted a filter to drop the Russian ones; 749 of 3,237 got through (1,517 tokens) | `example2` is not read |
| **F** | Nogai lines with a long Russian bracket, and Nogai lines made of words Russian also has («ак ас», «тик яр», «кара май») | the filter (a line is Russian when 60 % of its words are on a Russian list) threw out 1,220 of them | no filter; the lines are read (2,039 tokens) |
| **A** | Suffixes are cited as «-ден», «=тан» | read them as the words «ден», «тан» (150 tokens) | a citation with a leading or trailing «-» or «=» is not a word |
| **L** | Six words are typed with a Latin letter («мeн», «соpaп») | cut them at that letter | the twelve Latin twins are repaired first |
| **Q** | One-word equivalents with punctuation: «кайда?» | rejected them | read like any other text |
| **I** | The IDS list stores «й» as и + U+0306 (496 forms) | saw Cyrillic letters only: «кайыр» became «каи» + «ыр» | the form is composed (NFC) first |
| **X** | Apertium stores the personal pronouns as a first letter plus an ending (м + «ага») | read 23 endings as words («ага», «енинъ», «нда») | the 43 forms are put together («мага», «сенинъ», «онда») |
| **P** | Equivalents are lists: «кувув, кувып шыгарув» | paired every two neighbours, also across a comma or a bracket: «кувув кувып» | a pair needs nothing but a space between its words |

**Which brackets are Nogai.** 96 % of the brackets are Russian glosses, but
not all: «йонып (шабып) тегислев» gives a Nogai alternative. A bracket is

- a **gloss** when it has a word that only Russian text has (on v0's
  Russian list or in the Russian fields of this dictionary, and nowhere
  outside brackets on the Nogai side): 6,562 brackets;
- **Nogai** when it has a word that only Nogai text has (outside brackets
  on the Nogai side and on no Russian list, or spelled with аь, оь, уь,
  нъ): 291;
- a **suffix list** («(-ден, -тан, -тен)»): 62;
- **undecided** otherwise: 534 brackets (467 different ones). These were
  read by eye: 48 (41 different) are Nogai
  (`scripts/data/bracket_decisions.tsv`, e.g. «(солкылдап)», «(эр киси)»),
  10 are named glosses, and the other 476, Russian words that neither list
  knows («(бездеятельный)»), default to gloss.

Every bracket with its reading and the reason is in
`scripts/data/brackets.tsv`.

**What is deliberately kept from v0**: which lines are read (v0's own
duplicate test), the scoring rule and the two-occurrence rule for pairs.
So a Nogai word keeps exactly the count v0 gave it wherever v0 read it
correctly, and the script checks for every word that

```
count = v0 count − in glosses − in translations − as suffix − as piece
        + in restored lines + read whole
```

## What the build changes

### The source rules

| Rule | Rows removed | Rows restored |
|---|---|---|
| G1 Russian sense gloss in brackets | 4,657 | |
| T1 Russian translation of an example | 992 | |
| G1 + T1 (a word in both) | 251 | |
| A1 suffix citation | 32 | |
| I1 IDS form with a decomposed «й» | 268 pieces | 203 |
| X1 pronoun form of the Apertium lexicon | 15 endings | 6 |
| F1 line v0 dropped as Russian | | 191 |
| Q1 one-word field with punctuation | | 6 |
| **Together** | **6,215** (5,900 Russian words, 315 fragments) | **406** |

- 1,332 kept rows get a **corrected count** (C1). 972 rise because lines
  came back («ер» 149 → 194, «бас» 45 → 68); the rest fall because part of
  their v0 count was Russian («не» 117 → 65: the Russian «не» of the
  glosses) or a suffix citation («ден» 12 → 5).
- 15,543 rows are exactly as in v0.
- **Pairs**: 1,333 v0 pairs are not pairs of the source and are removed:
  368 have a word that is not Nogai («переносном значении», «за что-л»),
  924 never stand next to each other («дай дей» is «дай, дей»; «анълав
  туьсинуьв» is two equivalents), 41 do so once only. 86 pairs are new (they
  reach two occurrences only now: «кол салув», «бас июв», «тувган ер»).
  Each removed pair is in `dictionary/review/removed_pairs.csv` with its
  reason.

### The spelling rules

Three rules merge a variant into the word it stands for. A merge needs the
target to be a row already; nothing is respelled into a form the sources
do not have.

- **S1** «ъ» typed for «ь» after а, о, у: 9 rows (`соъз` → `соьз`,
  `суъврет` → `суьврет`). Nogai has no vowel + ъ.
- **S2** «нь» typed for «нъ»: 3 rows (`сизинь` → `сизинъ`).
- **M1** the IDS transcription «йа», «йу» for the literary «я», «ю»: 124
  rows (`йулдыз` → `юлдыз`, `йаман` → `яман`, `бийуьв` → `биюв`). The
  dictionary writes «я» 3,374 times and «йа» once, «ю» 1,440 times and
  «йу» never; the IDS list always writes й + vowel. The merged row adds
  the IDS list to the target's word lists.

All 136 are in `dictionary/review/merges.csv`.

### Reconciliation

`dictionary/review/reconciliation.csv`, checked by the build to add up in
every column:

| Step | Words | Occurrences | Score total | Pairs | Pair weight |
|---|---|---|---|---|---|
| v0 | 23,090 | 60,909 | 617,241 | 3,564 | 9,659 |
| Russian glosses and translations removed (G1, T1) | −5,900 | −9,602 | −96,021 | | |
| Fragments removed (A1, I1, X1) | −315 | −76 | −1,055 | | |
| Words restored (F1, I1, Q1, X1) | +406 | +196 | +2,175 | | |
| Counts corrected on kept rows (C1) | | +1,500 | +15,169 | | |
| Pairs removed (P1) | | | | −1,333 | −3,147 |
| Pairs new, weights corrected (P1, F1) | | | | +86 | +225 |
| **The sources read again** | **17,281** | **52,927** | **537,509** | **2,317** | **6,737** |
| Merged (S1, S2, M1) | −136 | 0 | −3 | 0 | 0 |
| **This dictionary** | **17,145** | **52,927** | **537,506** | **2,317** | **6,737** |

The occurrence total falls by 7,982: 8,357 gloss tokens, 1,517 translation
tokens, 150 suffix citations and 2 pieces go; 2,039 tokens of restored
lines and 5 repaired words come.

Result: 17,145 words (13,352 with a count, 3,793 from word lists only),
2,317 pairs; `content_version` 1, `cleanup_version` 1,
`normalization_version` 1, `normalization_profile` `nogai-cyrillic`.

## Normalization

Nogai has its own profile (`NogaiDefinition.normalization`, id
`nogai-cyrillic`, version 1), mirrored in the build script:

- NFC, trim, lowercase, NFC again (the engine's fixed pipeline);
- **no palochka**: Nogai is Turkic. Nothing is ever repaired into ӏ, and a
  Latin `I` or `l` inside a Cyrillic word makes the token invalid;
- the twelve Latin twins (`a c e o p x y k m t b h`) are repaired inside
  Cyrillic tokens;
- digraph tails **ь ъ**: аь, нъ, оь, уь count as one letter each. A word
  needs two letters to be learned or stored, so «уьй» is a word and «аь»
  alone is not;
- the four letters stay two characters. «аь» typed with the а and ь keys
  and «аь» from the long press are the same string, and both match the
  dictionary;
- ё, э and е, and аь and а, are different letters and never folded.

The engine was not changed for this.

## Review files (`dictionary/review/`)

- `flagged.csv`: **1,211 entries kept as they are and listed for a Nogai
  speaker**. `high_priority.csv`: the **47** to look at first.

  | Category | Entries | Priority |
  |---|---|---|
  | IDS transcription «й» + а, у with no literary spelling in the sources (`вентилйатор`, `дерийа`, `йатмак`) | 30 | high |
  | «къ», «гъ» or «гь», not letters of today's alphabet (`къуллыкъ`, `сувдыкъ`, `ангъламайман`) | 12 | high |
  | a Russian grammatical label of the dictionary (`частица`, `союз`, `глагол`) | 3 | high |
  | «ъ» where Nogai spelling has none (`этсуърткиш`, `билииъиз`) | 2 | high |
  | Nogai words in a garbled bracket, not an entry («аттьшъ», probably «аттынъ») | 1 | high |
  | capitalized in the source: a name or a title (`ногай`, `поттер`, `абдулла`) | 822 | normal |
  | also a Russian word, seen once and in no word list (`авторитет`, `багаж`, `куда`) | 231 | normal |
  | «ь» after a consonant: a Russian loan with a Nogai ending, or a misprint (`властьлик`, `айтарсьнъ`) | 41 | normal |
  | Russian infinitive or adjective (`печатать`, `страховать`, `научный`) | 37 | normal |
  | abbreviation, in capitals in the source (`бму`, `ссср`) | 36 | normal |
  | two-letter word outside the word lists | 16 | normal |
  | no vowel, the same letter three times, very long | 13 | normal |

- `corrections.csv`: every row removed, restored or recounted (7,953),
  with its rule and the reason.
- `merges.csv`: the 136 merges. `removed_pairs.csv`: the 1,333 pairs.
- `reconciliation.csv`, `manifest.json` (sources, commits, checksums,
  licences), `summary.json` (the audit and every count above).

## What to know about the content

- **Dictionary text, not running text.** The most frequent words are the
  verbal nouns a dictionary cites (`этуьв`, `алув`, `болув`, `беруьв`);
  finite verb forms and case forms are thin. Suggestions get better as the
  keyboard learns from typing (a word is learned after three uses by
  default). A count from real Nogai text is the obvious next step; see
  below.
- **The source has misprints of its own** that no rule here catches
  (`бермейгаган` for «бермейтаган», `коьтеринкн`). The build does not
  guess corrections; they are for a reader.
- **Russian words that stay.** 971 rows are also on a Russian list. Most
  are Nogai words that look the same (`мен`, `ер`, `бас`, `да`) or loans
  the dictionary gives as equivalents (`закон`, `машина`, `билет`). The
  dictionary also uses Russian infinitives inside Nogai phrases («печатать
  этуьв»); those are flagged, not removed.
- **Glosbe is edited by its users.** Next to the bulk of an older printed
  dictionary there are recent entries: film titles (`юлдыз согыслары`,
  `харри поттер`), place names, religious names. They are flagged as
  names.
- **The IDS list is a phonemic transcription** (й + vowel, some «къ»).
  Where the literary form is known it was merged (M1); 30 words are left
  in transcription and flagged high.
- Words are stored in lowercase; a name is suggested capitalized only when
  its first letter is typed as a capital.
- Hyphenated words (484 rows: `ян-якка`, `туьрли-туьрли`) are suggested
  from the part before the hyphen and inserted whole. The engine's
  tokenizer treats `-` as a separator while typing, so a hyphen typed by
  hand starts a new word (General Keyboard backlog).
- Not read, as in v0: `definition1` (958 short notes on the Nogai side:
  «ат», «Оьзбекстандагы кала», «(устаревшее)») and the 98 entries in the
  Latin alphabet.
- The layout covers every character the dictionary uses.

## Open questions

1. **A real corpus.** The newspapers «Шоьл тавысы» and «Ногай давысы» and
   the Nogai part of FineWeb-2 would give running-text counts and far more
   pairs. That needs a decision on sources and, for the newspapers, the
   publishers' consent. Agisight's FineWeb-2 letter counts were used for
   the layout only.
2. **The Apertium words are GPL v3.** The lexicon gives 1,315 words; 782
   of them are also in the Glosbe dictionary or the IDS list, and 533 rows
   (names, mostly) have no other source. The release owner should decide
   whether those 533 stay.
3. The 47 high-priority entries, above all the 30 words left in IDS
   transcription: what is their literary spelling?
4. Should the Russian infinitives («печатать», «страховать») be offered
   by a Nogai keyboard?

## Rebuilding

```bash
# from the repository root
python3 -I scripts/derive_source_repairs.py           # reads dictionary-source/, writes scripts/data/
SOURCE_DATE_EPOCH=1795478400 python3 -I scripts/build_dictionary.py
python3 -I scripts/build_dictionary.py --validate     # checks the shipped files
```

Both scripts verify the SHA-256 of every input. `derive_source_repairs.py`
stops if its replay is not v0 to the last count, or if the counts of any
word do not add up. `build_dictionary.py` refuses data that breaks its
assumptions, checks that the reconciliation adds up, writes the two
artifacts (page size 4096, vacuumed, `row_count` in `meta`) and the review
files, and validates the result. With `SOURCE_DATE_EPOCH` set the output
is byte-identical on every run (the shipped files were built with the
value above, 2026-11-24T00:00:00Z). A change of rule changes the tables or
the script, bumps `CLEANUP_VERSION` and `CONTENT_VERSION`, and needs the
new checksums pinned; the v0 inputs and the upstream files never change.
