# Building, signing, running on a device

## Requirements

- Xcode 27 (the project was created with 27.2); iOS 18.0 deployment target.
- `GeneralKeyboard-iOS` checked out next to this repository (`main`). The
  project references it as a local Swift package (`../../GeneralKeyboard-iOS`
  from the `.xcodeproj`); no tokens or registries. Nothing of the engine is
  copied into this repository, and the engine was not changed for Nogai.

## Targets and identity

Exactly two targets: `NogaiKeyboard` (the app) and
`NogaiKeyboardExtension` (the keyboard).

| | Debug (development) | Release (App Store) |
|---|---|---|
| App bundle ID | `org.lekitech.nogaikeyboard.dev` | `org.lekitech.nogaikeyboard` |
| Extension bundle ID | `org.lekitech.nogaikeyboard.dev.NogaiKeyboardExtension` | `org.lekitech.nogaikeyboard.NogaiKeyboardExtension` |
| App Group (`NOGAI_APP_GROUP_ID`, both entitlements) | `group.org.lekitech.nogaikeyboard.dev` | `group.org.lekitech.nogaikeyboard` |
| Signing | Automatic, team `RC94H8KQYA` | Manual, `Apple Distribution`, team and profiles empty |
| Display name | app: Nogai / Ногай тили · keyboard: Nogai / Ногайский | same |

Debug and Release use different identifiers on purpose: bundle IDs and App
Groups are unique across Apple developer teams, so a Debug build registered
under the developer's team must not take the production identifiers away
from the distribution team. `NogaiIdentity.swift` selects the App Group
with `#if DEBUG` to match. The learned-word store (`learned.sqlite`),
settings (`UserDefaults.standard` of the extension) and recent emojis live
in the extension's own container, keyed by its bundle ID, so Nogai never
shares or touches the data of the sibling keyboards. The App Group only
carries the inert contribution bridge.

The keyboard definition id (`KeyboardDefinition.id`) is the Release
extension bundle ID and never changes.

## Development build on a physical iPhone

1. Open `NogaiKeyboard/NogaiKeyboard.xcodeproj`, scheme `NogaiKeyboard`,
   configuration Debug (the scheme's default).
2. Connect the iPhone, select it as the run destination and press Run.
   Automatic signing with team `RC94H8KQYA` creates the two App IDs, the
   App Group `group.org.lekitech.nogaikeyboard.dev` and the development
   profiles on first use (Xcode asks once; a paid team, so no 7-day
   expiry).
3. On the phone: Settings → General → Keyboard → Keyboards → Add New
   Keyboard → **Nogai** (on a phone set to Russian: **Ногайский**). The
   app's own screen repeats these steps and its button opens Settings.
4. In any text field hold 🌐 and pick the keyboard.
5. Full Access is never requested and must stay off.

Command line, for a connected device (take the id from
`xcrun devicectl list devices`):

```bash
xcodebuild build -project NogaiKeyboard/NogaiKeyboard.xcodeproj -scheme NogaiKeyboard \
  -configuration Debug -destination 'id=<device udid>' -allowProvisioningUpdates \
  -derivedDataPath build/DerivedData-device
```

What to look at on the phone, since none of it can be judged on a
simulator:

- the Home Screen name «Ногай тили» on a Russian phone: does it show in
  full?
- «нъ» with the н and ъ keys: is ъ where the thumb expects it? Then the
  same letter with a long press on н;
- «аь», «оь», «уь» with ь, and with a long press on а, о, у;
- щ and ё on a long press of ш and е;
- suggestions while typing «уьй», «соьз», «бол», and the next word after
  «бир», «йок»;
- a new word typed three times comes back as a suggestion (learning speed
  «Обычно — 3 раза»);
- the globe menu: the keyboard's name and what iOS shows as its language.

## Simulator

```bash
xcodebuild build -project NogaiKeyboard/NogaiKeyboard.xcodeproj -scheme NogaiKeyboard \
  -destination 'platform=iOS Simulator,name=iPhone 18 Pro,OS=27.2' \
  -derivedDataPath build/DerivedData
```

`-derivedDataPath build/DerivedData` keeps the build products inside this
checkout (`build/` is ignored by Git), apart from every other project's.
Install the built `.app`, enable the keyboard in the simulator's Settings
as above, then type in any text field. Older simulator runtimes may lack
the emoji font; the emoji page then shows boxes there.

Checked on 2026-11-24 on an iPhone 17 simulator (iOS 27.2, English), once:
the app opens with its icon, the title «Nogai Keyboard» and «Ногай тили»;
the Home Screen shows the icon with the name «Nogai»; in a web page's text
area the 🌐 key brings up the keyboard with the three rows of
`docs/LAYOUT.md` and «НОГАЙ» in the corner of the space bar; «у», «ь», «й»
type U+0443 U+044C U+0439 and bring up «уьйкен», «уьй», «уьйретуьв» from
the dictionary; tapping «уьйкен» inserts the word with its space and
offers «манели», «зат», «асыгыс» as the next word; long presses on н, а,
о, у insert «нъ», «аь», «оь», «уь» as two characters each (U+043D U+044A,
U+0430 U+044C, U+043E U+044C, U+0443 U+044C); «с», «о», «н», «ъ» key by
key bring up «сонъ», «сонъы», «сонъгы»; the settings panel opens with
«3 раза» selected under learning and «Долгое нажатие (нъ, уь, ё…)»; the
emoji page, dark mode and the 🌐 key back to English work.

Not seen there: the Russian Home Screen name (the simulator was in
English), the globe menu's list with the keyboard's name and language
line, and a word coming back after three uses (covered by
`TypingAndLearningTests`). To add the keyboard without the Settings app,
`defaults write -g AppleKeyboards` needed `AppleKeyboardsExpanded -int 1`
and a restart of the simulator on this runtime. This is a simulator check,
not a test on a phone and not a review by a speaker.

## Tests

```bash
xcodebuild test -scheme NogaiCoreTests-Package \
  -destination 'platform=iOS Simulator,name=iPhone 18 Pro,OS=27.2' \
  -derivedDataPath build/DerivedData-tests
```

`Package.swift` compiles the product files of the extension into
`NogaiCore` and runs them through the real engine:

- `NogaiDefinitionTests` (10): the identity, the normalization profile
  without a palochka, the canonical form of words with аь, нъ, оь, уь,
  letter counts, strings, the project's targets and signing;
- `NogaiLayoutTests` (14): the rows against the pinned Russian baseline,
  every long press, Agisight's mapping, that no Dagestanian, old-alphabet
  or Kumyk letter is offered, the alphabet, Agisight's draft, and the
  letter counts the layout rests on;
- `DictionaryTests` (9): the shipped artifacts, ranked suggestions, the
  Russian glosses and fragments that are gone, the words that came back,
  the merges, the pairs;
- `TypingAndLearningTests` (16): typing, the four letters key by key and
  by long press in every case, accepted suggestions, learning, the
  learned next word, persistence, settings and the default learning speed
  (Normal, three uses).

49 tests. `xcodebuild test` sometimes does not exit after printing the
summary of the last suite; stop it then, the results above the summary
stand.

## The dictionary and the icon

```bash
python3 -I scripts/derive_source_repairs.py
SOURCE_DATE_EPOCH=1795478400 python3 -I scripts/build_dictionary.py
python3 -I scripts/analyze_layout.py
python3 scripts/make_icon.py          # needs Pillow
```

See `docs/DICTIONARY.md` and `docs/LOCALIZATION.md`. None of these runs
as part of the Xcode build; their outputs are committed.

## Release signing (later, by the distribution owner)

The Release configuration carries the App Store identifiers and manual
signing with an empty team and empty profile names. Before the first
archive the distribution team must:

1. register the App IDs `org.lekitech.nogaikeyboard` and
   `org.lekitech.nogaikeyboard.NogaiKeyboardExtension` and the App Group
   `group.org.lekitech.nogaikeyboard` in its developer account, with the
   App Groups capability on both App IDs;
2. create two App Store provisioning profiles and set, in the Release
   configuration of each target, `DEVELOPMENT_TEAM` and
   `PROVISIONING_PROFILE_SPECIFIER`;
3. keep Debug untouched, so development builds stay under the developer's
   own team.

Until then this checks that Release compiles:

```bash
xcodebuild build -project NogaiKeyboard/NogaiKeyboard.xcodeproj -scheme NogaiKeyboard \
  -configuration Release -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO \
  -derivedDataPath build/DerivedData-release
```

Nothing here uses another developer's credentials, and no certificate or
profile is committed.

## Conventions

Exactly two targets. No sticker extension, no messenger integrations, no
advertising, analytics, subscriptions or third-party packages (General
Keyboard `docs/ADDING_A_KEYBOARD.md`). Engine changes go to
`GeneralKeyboard-iOS` first; this repository holds only the Nogai
definition, resources, tests, dictionary sources and documentation. No
engine change was needed for Nogai: its normalization profile
(`nogai-cyrillic`, no palochka, ь and ъ as digraph tails) is a value of
the product, in `NogaiDefinition.swift`.
