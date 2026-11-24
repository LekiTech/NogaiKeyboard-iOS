# Pinned upstream files

Unmodified copies, used by `NogaiLayoutTests` and `scripts/analyze_layout.py`
and kept for attribution.

| File | Repository | Path | Commit |
|---|---|---|---|
| `rus-3-rows.yaml` | https://github.com/Agisight/ios-system-keyboard | `layout/rus/rus-3-rows.yaml` | `86e000a966d5d5aa5282617d5f6d90c69890e8db` (2026-11-11) |
| `rus-longpress.yaml` | https://github.com/Agisight/ios-system-keyboard | `layout/rus/rus-longpress.yaml` | same |
| `nog_key_mapping.json` | https://github.com/Agisight/rf-keyboard-corpora | `data/nog/Renat_Shakhmirzov/mapping/nog_key_mapping.json` | `cd7a94ee8318b1abb7690b93755242fd73aaf1b5` (2026-11-11) |
| `nog_monocorpus_freq.csv` | same | `data/nog/Renat_Shakhmirzov/frequencies/nog_monocorpus_freq.csv` | same |
| `nog_key_default.json` | same | `data/nog/Renat_Shakhmirzov/keyboard/nog_key_default.json` | same |
| `nog_metadata.json` | same | `data/nog/Renat_Shakhmirzov/metadata.json` | same |

Both repositories are MIT licensed: `LICENSE-ios-system-keyboard`
(Copyright (c) 2025 Agisight) and `LICENSE-rf-keyboard-corpora`
(Copyright (c) 2025 Agisight (Ali Kuzhuget)). The Nogai files name their
contributor, Renat Shakhmirzov.

What the Nogai keyboard takes from them:

- `rus-3-rows.yaml`, `rus-longpress.yaml`: a transcription of the Russian
  iOS keyboard (letter rows, number and symbol pages, symbol alternates),
  the baseline the Nogai layout departs from by one key.
- `nog_key_mapping.json`: which Russian key carries each two-character
  Nogai letter on a long press (А: Аь · Н: Нъ · О: Оь · У: Уь).
- `nog_monocorpus_freq.csv`: counts of the 37 letters of the Nogai
  alphabet in 3,783,628 letters of Nogai web text (the Nogai part of
  FineWeb-2, collected 2025-08-03 according to `nog_metadata.json`). The
  evidence for the layout in `docs/LAYOUT.md`. Unlike the Kumyk table of
  the same repository, this file is not a copy of another language's: no
  other frequency file there has its content.

Compared but not adopted:

- `nog_key_default.json`, «Nogai (customized)»: a draft with 35 letter keys
  in rows of 12, 12 and 11 (the Russian desktop rows with Нъ in ъ's place
  and Аь, Оь, Уь added). `docs/LAYOUT.md` says why the iPhone layout
  does not use it.

Not present upstream: a Nogai layout in `ios-system-keyboard` (no
`layout/nog` at this commit).
