# The Nogai layout

This is the **proposed LekiTech Nogai layout**. No finished Nogai iPhone
layout existed to copy (see [Agisight](#what-agisight-has-for-nogai)); it
was designed here from letter counts. It is not an Apple keyboard. It has
been checked on a simulator only; a test on an iPhone by the project owner
and a review by Nogai speakers are still open
([open questions](#open-questions)).

## Rows (iPhone)

```
й ц у к е н г ш ъ з х        11 keys
ф ы в а п р о л д ж э        11 keys
⇧ я ч с м и т ь б ю ⌫        9 letters
123 ⚙︎ 😀 🌐  space  ⏎
```

The Russian iOS layout with **one key changed**: the hard sign **ъ** is
where the Russian keyboard has **щ**; **щ** is a long press on ш. Every
other letter is in its Russian place. Key sizes are those of the Russian
keyboard (11 keys per row, 29.9 pt on a 402 pt iPhone, 27.5 pt on a 375 pt
one); the engine draws the grid with `KeyboardGridModel.nativeCells`.

The number and symbol pages are the Russian iOS pages, unchanged:
`1 2 3 4 5 6 7 8 9 0` / `- / : ; ( ) ₽ & @ "` / `#+= . , ? ! ' ⌫` and
`[ ] { } # % ^ * + =` / `_ \ | ~ < > $ € ¥ •` / `123 . , ? ! ' ⌫`.

## The four Nogai letters

| Letter | Typed key by key | Or one long press |
|---|---|---|
| аь | а, ь (two taps, one with each thumb) | hold а |
| нъ | н, ъ (two taps in the top row, the same thumb) | hold н |
| оь | о, ь (two taps, the keys almost under each other) | hold о |
| уь | у, ь (two taps, one with each thumb) | hold у |

Both ways give the same text: «нъ» is always н + ъ (U+043D U+044A), «аь»
а + ь, and so on. There is no single code point for these letters in
Nogai writing, and the keyboard never produces ә, ң, ө or ү. With Shift
the first letter is capital («Нъ», as the alphabet writes it), with Caps
Lock both («НЪ»).

## Long press (complete)

| Key | Options | |
|---|---|---|
| а | аь | letter of the alphabet |
| н | нъ | letter of the alphabet |
| о | оь | letter of the alphabet |
| у | уь | letter of the alphabet |
| е | ё | no key of its own, as on the Russian keyboard |
| ш | щ | no key of its own |
| ь | ъ | the Russian keyboard's habit keeps working |
| 0 | ° | |
| ₽ | $ € £ ¥ ￦ | |
| # | № | |
| . | … | |
| % | ‰ ∞ | |
| = | ≠ ≈ | |
| - | • – — | |
| / | \ | |
| & | § | |
| ? | ¿ | |
| ! | ¡ | |
| ' | ’ ‘ ` | |
| " | ” “ „ » « | |

The four letter options follow the Nogai long-press mapping of
Agisight/rf-keyboard-corpora (`nog_key_mapping.json`: А → Аь, Н → Нъ,
О → Оь, У → Уь). Each key has one option, so there is no order to
decide. The popup shows the key's own letter first, then the option; with
one option the popup has two cells and the finger rests on their border,
so the option is picked with a slight slide to the right. This is General
Keyboard's popup, the same in the sibling keyboards.

Not offered, on purpose: **гъ** and **къ** (letters of the 1938 alphabet,
taken out in 1944), **гь** and **нг** (Kumyk letters, never Nogai ones),
and anything with a palochka: Nogai is a Turkic language and has none.
«нг» occurs in Nogai words only as н + г at a joint («куьн-ге»), typed
with the two keys.

## Nogai spelling the layout is built on

The alphabet in use since 1960 has 37 letters: the 33 Russian ones and
**аь, нъ, оь, уь** (Калмыкова С. А., «Алфавит ногайского языка», 1972, and
«Орфография ногайского языка», 1973, as reported by the Russian Wikipedia
article «Ногайская письменность»; the KNAB 1995 romanization sheet of the
Institute of the Estonian Language lists the same 37). Its history, as far
as it matters for a keyboard:

| Year | Change |
|---|---|
| 1938 | Cyrillic alphabet: the Russian letters without ё, plus **гъ, къ, нъ**; the same year **оь, уь** |
| 1944 | **гъ, къ** taken out: г and к are written instead |
| 1960–61 | **аь** and **ё** added; the alphabet of today |

Front vowels are аь, э (е), и, оь, уь; back vowels а, ы, о, у. ё, ф, ц, ч,
щ, and ъ and ь outside the four letters, stand in Russian loans. The three
dialects (Karanogai, Nogai proper, Aknogai) share this written standard;
nothing in the layout depends on a dialect.

## The evidence

Two sets of counts, both in `layout/analysis.json`
(`python3 -I scripts/analyze_layout.py`):

- **web text**: Agisight's table of the 37 letters in 3,783,628 letters of
  Nogai web text (FineWeb-2), pinned in
  `Tests/NogaiCoreTests/Fixtures/agisight/nog_monocorpus_freq.csv`;
- **dictionary text**: the keyboard's own dictionary, 52,927 word
  occurrences. It over-counts «уь» and «в», because a dictionary cites
  verbs as «-ув», «-уьв».

| Share of all letters, % | нъ | оь | уь | аь | ъ outside нъ | ь outside аь оь уь | щ | ё |
|---|---|---|---|---|---|---|---|---|
| web text | 1.249 | 0.783 | 0.769 | 0.520 | 0.034 | 0.236 | 0.024 | 0.005 |
| dictionary text | 0.692 | 1.091 | 2.601 | 0.168 | 0.001 | 0.031 | 0.004 | 0.003 |

- The four letters together are 3.3 % of web text (4.6 % of dictionary
  text): about one letter in thirty.
- Three of them end in **ь**, which the Russian keyboard has a key for.
  Only **нъ** ends in a character without a key, and it is the most
  frequent of the four in running text.
- **ъ** stands after н in 99.8 % of its occurrences in the dictionary; in
  web text «нъ» is 37 times as frequent as every other ъ together.
- **щ** is fifty times rarer than нъ and stands in Russian loans only.
- гъ and къ occur once each in the dictionary (misprints), гь never.

## Candidates compared

A model of typing, not a measurement of people: letter by letter, no
suggestions; a key is one tap, a letter without a key one long press
(0.3 s delay); two thumbs. Presses and long presses per 100 letters are
counted on web text, the rest on dictionary text.

| | Layout | Keys per row | Narrowest key, 402 / 375 pt | Presses per 100 letters | Long presses per 100 letters | per 100 words (dictionary) | Seconds per 100 letters at 0.25 s a tap |
|---|---|---|---|---|---|---|---|
| A0 | Russian iOS keyboard as it is | 11 · 11 · 9 | 29.9 / 27.5 | 103.3 | 1.288 | 4.09 | 26.2 |
| A | Russian + long presses а н о у (Agisight's mapping) | 11 · 11 · 9 | 29.9 / 27.5 | 102.1 | 1.288 | 4.09 | 25.9 |
| **B** | **ъ on щ's key, щ under ш (chosen)** | 11 · 11 · 9 | 29.9 / 27.5 | 103.3 | **0.029** | **0.04** | 25.8 |
| C | a «нъ» key on щ's key; ъ under ь | 11 · 11 · 9 | 29.9 / 27.5 | 102.1 | 0.063 | 0.05 | 25.5 |
| D | Agisight's draft: a key for each of нъ аь оь уь | 12 · 12 · 11 | 24.4 / 22.3 | 100.0 | 0.039 | 0.02 | 25.0 |
| E | the draft cut to 12-key rows: нъ, уь, оь keys | 12 · 12 · 9 | 26.9 / 24.7 | 100.5 | 0.063 | 0.05 | 25.2 |

Why B:

- **A0, A** leave every «нъ» on a long press: 1.3 long presses per 100
  letters, one in every dozen words of running text. A's long press types
  both characters at once, which saves a tap but not the hold.
- **B** removes them for the price of one moved key: 0.03 long presses per
  100 letters (щ and ё). Every Nogai letter is plain taps, every Russian
  letter but щ is where a Russian typist expects it, and the keys keep
  their native size. It is also the arrangement of the Kumyk keyboard, so
  the two Turkic keyboards of the family agree.
- **C** is B with one tap fewer per «нъ» (1.2 % of presses). It needs a
  key that types two characters, on which Backspace removes half of what
  the key typed, and it sends «ъ» itself back to a long press. The gain is
  small and the key is unusual; kept as an [open question](#open-questions).
- **D**, Agisight's draft, has the fewest presses (3.2 % fewer than B) but
  not on an iPhone: its third row has 11 letters, and with Shift and
  Backspace that is 13 cells where the Russian keyboard has 11. Keys would
  be 24.4 pt wide on a 402 pt phone and 22.3 pt on a 375 pt one, a fifth
  narrower than native, in every row, and no letter would be in its Russian
  place. The model does not count mistyped keys; narrow keys cost more of
  them than a tap saves.
- **E** keeps D's idea within rows Apple itself uses (12 keys, as the
  Ukrainian keyboard and Lezgi's top-row style): 26.9 / 24.7 pt keys in
  two rows, and 22 letters moved from their Russian places, for a 2.7 %
  saving.

## What Agisight has for Nogai

Checked at `ios-system-keyboard` `86e000a` and `rf-keyboard-corpora`
`cd7a94e` (both 2026-11-11, the heads on 2026-11-23); the files used are
pinned in `Tests/NogaiCoreTests/Fixtures/agisight/` (`SOURCE.md` there).

- `ios-system-keyboard` has **no Nogai layout** (no `layout/nog`).
- `rf-keyboard-corpora/data/nog/Renat_Shakhmirzov/` has
  - `frequencies/nog_monocorpus_freq.csv`: the letter counts used above
    (FineWeb-2, collected 2025-08-03). Genuine Nogai counts: unlike the
    Kumyk table of that repository, no other language's file has the same
    content;
  - `mapping/nog_key_mapping.json`: А → Аь, Н → Нъ, О → Оь, У → Уь,
    adopted as the long presses;
  - `keyboard/nog_key_default.json`, «Nogai (customized)»: candidate D, the
    Russian desktop rows with Нъ in ъ's place and Аь, Оь, Уь added at the
    row ends, with `,` `.` `?` `!` on long presses of letters. A draft for
    a wider keyboard, not an iPhone layout;
  - `raw/`: a link to the FineWeb-2 query, no text.

So the layout is LekiTech's own, informed by Agisight's counts and mapping
(scenario B of the project brief).

## Open questions

1. **A «нъ» key instead of the «ъ» key** (candidate C). One tap for the
   most frequent Nogai letter, but a key that types two characters. Would
   Nogai typists rather see «нъ» on the key?
2. **щ on a long press.** Russian text typed on this keyboard needs a hold
   for щ (0.02 % of Nogai letters, about 0.3 % of Russian ones). Is that
   acceptable to people who type both languages without switching
   keyboards?
3. **Long press on ь.** It gives «ъ», as on the Russian keyboard. Nothing
   else is under ь.
4. **Dedicated keys for аь, оь, уь** (candidates D and E) were set aside
   for the key width. If testers ask for them, E is the form that fits an
   iPhone.

## Changing the layout

Rows and long presses are in
`NogaiKeyboard/NogaiKeyboardExtension/NogaiLayout.swift`; the app's screen
repeats them for display in `ContentView.swift`; `NogaiLayoutTests` pins
them. `scripts/analyze_layout.py` holds the candidates of the table above.
