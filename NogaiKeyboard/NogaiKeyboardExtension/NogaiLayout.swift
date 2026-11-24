//
//  NogaiLayout.swift
//  NogaiKeyboardExtension
//
//  The LekiTech Nogai layout (proposed; not an Apple or otherwise official
//  layout). It is the Russian iOS keyboard with one key changed: the hard
//  sign «ъ» takes the place of «щ», and «щ» moves under a long press on «ш».
//
//  Why: the Nogai alphabet is the Russian one plus four letters written
//  with two characters, «аь», «нъ», «оь», «уь». Three of them end in «ь»,
//  which has a key on the Russian keyboard; «нъ» ends in «ъ», which has
//  none. «нъ» is 1.25 % of the letters of Nogai web text (Agisight's count
//  of 3.78 million letters), while «щ» is 0.02 % and stands in Russian
//  loans only. On the Russian layout every «нъ» needs a long press (1.29
//  long presses per 100 letters); here all four letters are two plain taps
//  and a long press is left for «щ» and «ё» only (0.03 per 100 letters).
//  The numbers, the alternatives that were compared (among them Agisight's
//  draft with a key for each of the four letters) and the trade-offs are in
//  docs/LAYOUT.md, computed by scripts/analyze_layout.py.
//
//  The four letters are also offered as long-press options that insert both
//  characters at once, under the key Agisight's mapping gives them (а, н,
//  о, у). Rows are written once, in lowercase; the engine derives the shift
//  layer (first letter: «нъ» → «Нъ») and Caps Lock (all letters: «НЪ»).
//
//  Nogai is a Turkic language and has no palochka: none of the palochka
//  keys or options of the Dagestanian keyboards is here.
//
//  Product data: the engine reads it only through
//  `KeyboardDefinition.current.layout` (see NogaiDefinition.swift).
//

import Foundation
import GeneralKeyboard

extension LayoutStyle {
    /// The one Nogai layout. Persisted raw value; never rename.
    static let standard = LayoutStyle(rawValue: "standard")
}

enum NogaiLayout {

    static let capabilities = LayoutCapabilities(
        styles: [standard],
        defaultStyle: .standard,
        // One style: the engine hides the selector and the quick menu.
        showsStyleSelector: false,
        persistenceKey: "layoutStyle",
        quickSwitchOnSettingsLongPress: false,
        // iPhone portrait on Apple's native keyboard grid (pixel-snapped
        // cells, native bottom-row proportions, native panel height), as
        // approved for the sibling keyboards
        gridModel: .nativeCells
    )

    static let standard = LayoutStyleSpec(
        id: .standard,
        letterRows: letterRows,
        numberRows: numberRows,
        symbolRows: symbolRows,
        callouts: callouts,
        metrics: metrics,
        settingsTitle: "Стандартная",
        settingsSubtitle: "Русская раскладка, ъ на месте щ"
    )

    /// Three letter rows and the geometry the sibling keyboards ship with.
    static let metrics = KeyboardLayout.Metrics(totalHeight: 250, keyHeight: 43, rowSpacing: 11,
                                                emojiRows: 5, emojiCellHeight: 33)

    // MARK: - Letter rows

    static let letterRows: [[KeyCap]] = [
        ["й","ц","у","к","е","н","г","ш","ъ","з","х"].map { .character($0) },   // 11 keys, ъ on щ's key
        ["ф","ы","в","а","п","р","о","л","д","ж","э"].map { .character($0) },   // 11 keys, as Russian
        [.shift]
            + ["я","ч","с","м","и","т","ь","б","ю"].map { KeyCap.character($0) } // 9 keys, as Russian
            + [.backspace],
    ]

    // MARK: - Number page (the standard Russian iOS set)

    static let numberRows: [[KeyCap]] = [
        ["1","2","3","4","5","6","7","8","9","0"].map { .character($0) },
        ["-","/",":",";","(",")","₽","&","@","\""].map { .character($0) },
        [.symbols] + [".",",","?","!","'"].map { KeyCap.character($0) } + [.backspace],
    ]

    // MARK: - Symbol page (the standard Russian iOS set)

    static let symbolRows: [[KeyCap]] = [
        ["[","]","{","}","#","%","^","*","+","="].map { .character($0) },
        ["_","\\","|","~","<",">","$","€","¥","•"].map { .character($0) },
        [.numbers] + [".",",","?","!","'"].map { KeyCap.character($0) } + [.backspace],
    ]

    // MARK: - Long-press callouts
    // Keys are lowercase; the popup puts the base key first and the shift
    // state is applied to every option. An option is inserted as a whole
    // string («нъ» = н + ъ, two Cyrillic characters).

    /// The four two-character letters of the Nogai alphabet under their
    /// first character: the assignment of the Nogai long-press mapping of
    /// Agisight/rf-keyboard-corpora (nog_key_mapping.json: А → Аь, Н → Нъ,
    /// О → Оь, У → Уь). Each key has one option, so there is no order to
    /// choose. «гъ», «къ» (out of the alphabet since 1944), «гь» and «нг»
    /// are not Nogai letters and are not offered.
    static let digraphCallouts: [String: [String]] = [
        "а": ["аь"],
        "н": ["нъ"],
        "о": ["оь"],
        "у": ["уь"],
    ]

    /// Letters without a key, and the Russian keyboard's ь → ъ so that a
    /// habit from that keyboard keeps working.
    static let letterCallouts: [String: [String]] = [
        "е": ["ё"],
        "ш": ["щ"],
        "ь": ["ъ"],
    ]

    /// The symbol alternates of the Russian iOS keyboard (as the sibling
    /// keyboards; the quote alternates sit on this layout's ' and " keys).
    static let symbolCallouts: [String: [String]] = [
        "0": ["°"],
        "₽": ["$", "€", "£", "¥", "￦"],
        "#": ["№"],
        ".": ["…"],
        "%": ["‰", "∞"],
        "=": ["≠", "≈"],
        "-": ["•", "–", "—"],
        "/": ["\\"],
        "&": ["§"],
        "?": ["¿"],
        "!": ["¡"],
        "'": ["’", "‘", "`"],
        "\"": ["”", "“", "„", "»", "«"],
    ]

    static let callouts: [String: [String]] = digraphCallouts
        .merging(letterCallouts) { first, _ in first }
        .merging(symbolCallouts) { first, _ in first }
}
