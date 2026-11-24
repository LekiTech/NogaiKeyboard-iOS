# Nogai Keyboard for iOS

A native iOS keyboard for the Nogai language (Ногай тили), developed by
[LekiTech](https://github.com/LekiTech) on the shared
**General Keyboard** engine, next to the Avar, Lezgi, Dargwa, Kumyk,
Tabasaran, Lak, Aghul, Rutul and Tsakhur keyboards.

Nogai is a Kipchak Turkic language. Its alphabet is the Russian one plus
four letters written with two characters each, **аь, нъ, оь, уь**; it has
no palochka and none of the Dagestanian consonant letters.

## The keyboard

- **The LekiTech Nogai layout** (a proposal, designed from letter counts;
  not an Apple layout): the Russian iOS layout with one key changed. The
  hard sign **ъ**, needed for **нъ** (1.25 % of the letters of Nogai
  text), has its own key where Russian has щ.

  ```
  й ц у к е н г ш ъ з х
  ф ы в а п р о л д ж э
  ⇧ я ч с м и т ь б ю ⌫
  ```

- аь, нъ, оь, уь are typed with two plain taps (а ь, н ъ, о ь, у ь), or
  with one long press: а → аь · н → нъ · о → оь · у → уь. Also
  е → ё · ш → щ · ь → ъ. Why this layout, the numbers and the
  alternatives (among them Agisight's draft with a key for each of the
  four letters): [docs/LAYOUT.md](docs/LAYOUT.md).
- Word suggestions from an offline dictionary of 17,145 Nogai words and
  2,317 word pairs, plus the words and word pairs it learns from your own
  typing (after three uses by default), including next-word suggestions.
  The dictionary was rebuilt from its sources: the first build had taken
  5,900 Russian words for Nogai. See
  [docs/DICTIONARY.md](docs/DICTIONARY.md).
- Matches the native iOS keyboard (Apple's measured iPhone grid, key
  previews, callout menus with swipe selection, caps lock,
  auto-capitalization, spacebar cursor control, hold-to-repeat delete),
  light and dark mode, the emoji page, an in-keyboard settings panel.
- Private by design: never asks for Full Access and sends nothing anywhere.
  Learned words live in the keyboard's own storage and can be managed and
  reset from the keyboard's gear key.

Status: **built and checked on a simulator; not yet tested on an iPhone,
not published, not released.** Open questions for Nogai speakers are in
[docs/LAYOUT.md](docs/LAYOUT.md#open-questions) and
[docs/DICTIONARY.md](docs/DICTIONARY.md#open-questions); the keyboard's key
names and settings panel use Russian text until a Nogai translation is
reviewed ([docs/LOCALIZATION.md](docs/LOCALIZATION.md)).

## Building

The keyboard engine is the shared **General Keyboard** Swift Package
([LekiTech/GeneralKeyboard-iOS](https://github.com/LekiTech/GeneralKeyboard-iOS)),
linked as a local package found next to this checkout:

```
<workspace>/
  GeneralKeyboard-iOS/   the engine package (main)
  NogaiKeyboard-iOS/     this repository
```

The Xcode project references the package as `../../GeneralKeyboard-iOS`
(relative to `NogaiKeyboard/NogaiKeyboard.xcodeproj`) and the test
package as `../GeneralKeyboard-iOS`; nothing else is required (no tokens,
no package registry) and nothing of the engine is copied here. Open
**`NogaiKeyboard/NogaiKeyboard.xcodeproj`** in Xcode 27, pick the
**`NogaiKeyboard`** scheme (it builds and embeds the
`NogaiKeyboardExtension` target) and run on a simulator or an iPhone.

```bash
xcodebuild build -project NogaiKeyboard/NogaiKeyboard.xcodeproj -scheme NogaiKeyboard \
  -destination 'platform=iOS Simulator,name=iPhone 18 Pro,OS=27.2' \
  -derivedDataPath build/DerivedData
xcodebuild test -scheme NogaiCoreTests-Package \
  -destination 'platform=iOS Simulator,name=iPhone 18 Pro,OS=27.2' \
  -derivedDataPath build/DerivedData-tests
```

Installing on an iPhone, signing and the test suite:
[docs/BUILDING.md](docs/BUILDING.md).

## Identity

| | Debug (development) | Release (App Store) |
|---|---|---|
| App bundle ID | `org.lekitech.nogaikeyboard.dev` | `org.lekitech.nogaikeyboard` |
| Keyboard extension bundle ID | `org.lekitech.nogaikeyboard.dev.NogaiKeyboardExtension` | `org.lekitech.nogaikeyboard.NogaiKeyboardExtension` |
| App Group (both targets) | `group.org.lekitech.nogaikeyboard.dev` | `group.org.lekitech.nogaikeyboard` |
| Signing | automatic, the developer's own team | manual: the distribution team adds its team and App Store profiles |
| Home Screen name | Nogai · Russian: Ногай тили | same |
| Keyboard name | Nogai · Russian: Ногайский; language code `nog` | same |

Both targets carry the App Groups entitlement; the group's identifier is
the `NOGAI_APP_GROUP_ID` build setting of each configuration. The Release
configuration ships with an empty team and empty profile names on purpose.

## Release and App Store handoff

Debug builds run as they are under the developer's team. The Release
configuration is prepared but deliberately unsigned: it carries the App
Store identifiers, manual signing with `Apple Distribution`, and an empty
team and empty profile names. To archive for the App Store, the
distribution team:

1. Registers the App IDs `org.lekitech.nogaikeyboard` and
   `org.lekitech.nogaikeyboard.NogaiKeyboardExtension`, creates the App
   Group `group.org.lekitech.nogaikeyboard`, and enables the App Groups
   capability with that group on both App IDs.
2. Creates an App Store provisioning profile for each of the two App IDs.
3. In the **Release** configuration of both targets (`NogaiKeyboard` and
   `NogaiKeyboardExtension`) sets `DEVELOPMENT_TEAM` and
   `PROVISIONING_PROFILE_SPECIFIER` (Signing & Capabilities → Release, or
   the build settings). Debug stays as it is.
4. Sets the version in both targets, the same values in each:
   `MARKETING_VERSION` (now 1.0.0) and `CURRENT_PROJECT_VERSION` (now 1).
5. Archives the `NogaiKeyboard` scheme (Product → Archive; it archives the
   Release configuration and embeds the extension) and uploads the archive
   to App Store Connect.

Before signing is set up, this checks that Release compiles:

```bash
xcodebuild build -project NogaiKeyboard/NogaiKeyboard.xcodeproj -scheme NogaiKeyboard \
  -configuration Release -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO \
  -derivedDataPath build/DerivedData-release
```

For the App Store listing: the keyboard does not request Full Access
(`RequestsOpenAccess` is false) and sends nothing anywhere, and
`ITSAppUsesNonExemptEncryption` is NO. The bundle identifiers and the App
Group must not change after the first upload. Before a release, read the
licence note on the Apertium word list in
[docs/DICTIONARY.md](docs/DICTIONARY.md#open-questions).

## Repository

```
NogaiKeyboard/
  NogaiKeyboard.xcodeproj            two targets: the app and the keyboard extension
  NogaiKeyboard/                     containing app (SwiftUI): install steps, layout,
                                     long-press guide, settings info
  NogaiKeyboardExtension/            the keyboard: NogaiDefinition (with the Nogai
                                     normalization profile), NogaiLayout, NogaiStrings,
                                     NogaiIdentity, KeyboardViewController, Info.plist,
                                     nogai_words.sqlite, nogai_bigrams.sqlite
Package.swift, Tests/NogaiCoreTests/ product-layer tests through the real engine
  Fixtures/agisight/                 pinned upstream files (MIT): the Russian baseline,
                                     Agisight's Nogai mapping, letter counts and draft
dictionary-source/
  original-v0/                       the Nogai files of keyboard_data_v0.zip
  upstream/                          the three sources v0 read, pinned by commit
scripts/derive_source_repairs.py     reads the sources again; proves the v0 replay
scripts/data/                        what it found: words, pairs, brackets, removals
scripts/build_dictionary.py          reproducible dictionary build and review files
scripts/analyze_layout.py            letter statistics and the layout comparison
scripts/make_icon.py                 installs the app icon from docs/branding/
docs/                                LAYOUT (+ layout/analysis.json), DICTIONARY
                                     (+ dictionary/review/), LOCALIZATION, BUILDING,
                                     branding/ (the icon artwork as delivered)
```

The engine itself (model, views, storage, normalization pipeline,
settings, emoji) is not in this repository; see `GeneralKeyboard-iOS/docs/`.

## Organization

Developed by [LekiTech](https://github.com/LekiTech), a team building
digital tools for the languages of Dagestan.

## License

All rights reserved, see [LICENSE](LICENSE). Third-party material and its
licenses are listed there: Agisight's layout data (MIT), the Russian–Nogai
dictionary dataset of Renat Shakhmirzov (MIT), the Apertium Nogai lexicon
(GPL v3) and the Intercontinental Dictionary Series (CC BY 4.0).
