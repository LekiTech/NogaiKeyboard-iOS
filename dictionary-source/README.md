# Dictionary sources

Read-only inputs of `scripts/derive_source_repairs.py` and
`scripts/build_dictionary.py`. Nothing here is edited; the checksums are in
each folder's `SHA256SUMS` and are pinned again in the scripts.

## original-v0/

The Nogai files of `keyboard_data_v0.zip` (SHA-256 `8cec9c22…b8ac31`,
folder `keyboard_data/`, built 2026-10-11), as extracted:

| File | What it is |
|---|---|
| `nog_words.tsv`, `nog_words.sqlite` | 23,090 words with their counts and the number of word lists that have them |
| `nog_bigrams.tsv`, `nog_bigrams.sqlite` | 3,564 word pairs with weights |
| `nog_stats.json` | the v0 builder's summary: one text source (`glosbe_phrases`) and three word lists |

The archive's two general files, `README.md` and `build_kb_data.py` (the
v0 builder for all nine languages), are kept beside them in a working
checkout and are not tracked in this repository; `SHA256SUMS` lists them.
To recreate the folder:

```bash
unzip -j keyboard_data_v0.zip 'keyboard_data/nog_*' 'keyboard_data/README.md' \
  'keyboard_data/build_kb_data.py' -d dictionary-source/original-v0
```

## upstream/

The three files v0 read for Nogai, at the commits that were current when
v0 was built. `scripts/derive_source_repairs.py` replays the v0 builder on
them and gets the v0 files exactly, to the last count, so these are the
data v0 read.

| Folder | File | From | Licence |
|---|---|---|---|
| `nogai-dataset-3ff8a74/` | `nogai_russian_dictionary.json` (24,340 entries) | https://github.com/shakhmirzovrenat/Dataset-of-nogai-language. at `3ff8a74c159ab4f594ee556f77dea4137ee44416` (2026-05-11) | MIT (`LICENSE`), Copyright (c) 2026 shakhmirzovrenat |
| `apertium-nog-09fdef0/` | `apertium-nog.nog.lexc` | https://github.com/apertium/apertium-nog at `09fdef073c5900c1f7be2b59c59f53f3a5856b97` (2021-07-20) | GNU GPL v3 (`COPYING`); authors in `AUTHORS` |
| `ids-bf6c9f8/` | `forms_nogai_73.csv`: the 2,031 rows with `Language_ID` 73 of `cldf/forms.csv`, copied byte for byte with the header line | https://github.com/intercontinental-dictionary-series/ids at `bf6c9f8c7d25c15e61e338f3ed29ae46b844c0f8` (2026-10-09); SHA-256 of the whole `forms.csv`: `1ff6caa4…4e9968` | CC BY 4.0 (`LICENSE`) |

Cite the IDS list as: Key, Mary Ritchie & Comrie, Bernard (eds.) 2023.
*The Intercontinental Dictionary Series.* Leipzig: Max Planck Institute
for Evolutionary Anthropology. https://ids.clld.org (list 73, «Nogai»,
author Madzhid Khalilov, data entry Stefan Lange).

A fourth file is not kept here: the word list v0 used as its Russian
filter, `data/clean_data_with_frequency.csv.zip` of
https://github.com/LingConLab/Cyrillic_languages_identification_models_and_data_store
at `3c18d336b0258b2bfefaac73ba84da3e667bd101` (18 MB, SHA-256
`f23b3027…788623`; no licence file). Its 142,284 Russian word forms come
from Universal Dependencies treebanks. The 14,456 of them that occur in
the dictionary are in `scripts/data/russian_words_in_sources.txt`, which is
all the scripts need; `scripts/derive_source_repairs.py --refresh-russian`
rebuilds that extract from the zip.

What the build does with these files, and what it does not read
(`example2`, `definition1`, the Latin-script entries), is in
`docs/DICTIONARY.md`.
