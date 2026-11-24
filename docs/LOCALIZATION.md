# Localization and strings for review

## Names

| Where | English and every other language | Russian |
|---|---|---|
| Home Screen (app, `CFBundleDisplayName` and `CFBundleName`) | Nogai | Ногай тили |
| Title on the app's screen | Nogai Keyboard | Ногайская клавиатура |
| Keyboard in Settings → Keyboards and in the 🌐 menu (extension) | Nogai | Ногайский |

English is the development language and the fallback: a phone set to any
language other than Russian shows the English names. The Russian
localization carries the language's own name, as the sibling apps do
(«Къумукъ тил», «Лакку маз»). «Ногай тили» has 10 characters and stays
under the Home Screen limit measured for the family (about 12; iOS first
tightens the spacing, then drops the space, then cuts with «…»). Whether it
shows in full on a 375 pt phone is still to be seen on a device.

Where the names live:

- `NogaiKeyboard/NogaiKeyboard/InfoPlist.xcstrings`: the app's two names,
  en + ru;
- the app target's `INFOPLIST_KEY_CFBundleDisplayName = Nogai`: only the
  unlocalized fallback;
- `NogaiKeyboard/NogaiKeyboardExtension/InfoPlist.xcstrings`: the
  keyboard's name, en + ru. It is separate from the app's Home Screen name
  on purpose;
- `NogaiKeyboardExtension/Info.plist`: `PrimaryLanguage` is **`nog`**, the
  language's real code, not `ru`. If iOS has no display name for `nog`,
  the 🌐 menu shows the keyboard's name without a language line under it;
  that is accepted rather than claim the keyboard is Russian.

## What is Nogai today

| Where | String | Source |
|---|---|---|
| Keyboard name (flashed on the space bar), app header, Russian Home Screen name | Ногай тили | the self-name of the language: the KNAB romanization sheet (Institute of the Estonian Language, 2003: «Ногай тили Nogaj tili»), Omniglot and the English and Russian Wikipedia give this form; the dictionary has «мунда ногай тилин ким биледи?» |
| Space bar corner label | НОГАЙ | the first word of the self-name, as «КЪУМ», «ЛЕЗГ», «АВАР» on the sibling keyboards |

Nothing else is Nogai yet. **No Nogai translation was invented.**

## What is temporary Russian (needs a Nogai translation)

No verified Nogai translation of the key names or of the keyboard's
settings panel exists (Agisight's `ios-system-keyboard` has no Nogai key
names), so `NogaiStrings.swift` uses Russian. Every string below needs a
reviewed Nogai version:

| Field | Russian (current) |
|---|---|
| space | Пробел |
| return key: Go / Send / Done / Next / Continue / Join / Route / Search | Перейти / Отправить / Готово / Далее / Продолжить / Подкл. / Маршрут / Найти |
| emergency call | SOS |
| lettersKey | АБВ |
| deleteWordQuestion | Удалить «…»? |
| no / delete | Нет / Удалить |
| emojiRecents | Недавние |
| back / close | Назад / Клавиатура |
| settingsCaption / settingsTitle | НОГАЙСКАЯ КЛАВИАТУРА / Настройки |
| pageInput / pageTheme / pageDictionary / pageAbout | Ввод / Тема / Словарь / О клавиатуре |
| sectionLayout / sectionSuggestions / sectionKeys / sectionLearning | Раскладка / Подсказки / Клавиши / Обучение |
| sectionLongPress / sectionTheme | Долгое нажатие (нъ, уь, ё…) / Тема |
| wordSuggestions / nextWordSuggestion / autoSpace | Подсказки слов / Подсказка следующего слова / Пробел после подсказки |
| doubleSpacePeriod / spaceCursor / spaceCornerToggle | Два пробела — точка / Курсор пробелом / «ногай» на пробеле |
| learnFast / learnNormal / learnSlow / learnUses | Быстро / Обычно / Медленно / N раз(а) |
| calloutShort / calloutNormal / calloutLong / calloutDuration | Короткая задержка / Обычная задержка / Длинная задержка / 0,3 с |
| themeSystem / themeLight / themeDark | Системная / Светлая / Тёмная |
| learnedWordsCaption / noWordsYet | выученные слова / Пока нет слов |
| deleteAll / deleteAllQuestion | Удалить все выученные слова / Удалить все выученные слова? |
| aboutInitial / aboutTitle / aboutByline | Н / Ногайская клавиатура / Версия … · LekiTech |
| settingsTitle / settingsSubtitle of the layout style | Стандартная / Русская раскладка, ъ на месте щ |
| emojiCategoryTitles | Смайлики и люди, Животные и природа, Еда и напитки, Активность, Путешествия и места, Предметы, Символы, Флаги |

Also the extension's `Localizable.xcstrings` («Show «ногай» on the space
bar», en/ru).

The engine's own labels (for example the explanatory subtitles under the
toggles) follow the system language (en/ru) and are not Nogai's to
translate.

## The containing app

English with Russian translations
(`NogaiKeyboard/NogaiKeyboard/Localizable.xcstrings`, 27 strings), like the
sibling apps: «Nogai Keyboard» / «Ногайская клавиатура», the install
steps, the layout and long-press cards, the settings note. No Nogai text
there except the letters and «Ногай тили». The app shows no contributor
credits; attribution of third-party material is in the repository
(`LICENSE`, `Tests/NogaiCoreTests/Fixtures/agisight/SOURCE.md`,
`dictionary-source/README.md`).

## Icon and colours

The app icon is the owner's artwork (a green winged wolf outlined in gold
on a cyan field, above a white keyboard), delivered as a 1254 × 1254 WebP
and kept as delivered in `docs/branding/NogaiKeyboard_AppIcon_1254.webp`.
`scripts/make_icon.py` scales it to the 1024 × 1024 opaque RGB PNG iOS
takes (`AppIcon.appiconset/AppIcon-1024.png`) and to the 512 px logo of the
app's screen (`AppLogo.imageset/AppLogo.png`), and checks that it is a
full-bleed square without transparency or pre-rounded corners. Nothing is
redrawn. If a 1024 px original is added as
`docs/branding/NogaiKeyboard_AppIcon_1024.png`, the script uses it without
scaling.

`AccentColor` is the emblem's green deepened for white text on it
(#007D00, dark mode #32C850); `BrandTint` is the field's cyan deepened to
be readable as text (#0085B5, dark mode #33C9FF).
