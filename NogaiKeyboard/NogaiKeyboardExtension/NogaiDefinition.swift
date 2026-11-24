//
//  NogaiDefinition.swift
//  NogaiKeyboardExtension
//
//  The Nogai keyboard as a KeyboardDefinition: everything Nogai-specific
//  the General Keyboard engine uses, assembled in one value. The layout
//  lives in NogaiLayout.swift, strings and key names in NogaiStrings.swift.
//

import Foundation
import GeneralKeyboard

enum NogaiDefinition {

    /// Nogai Cyrillic, version 1: the canonical form of the bundled
    /// dictionary (scripts/build_dictionary.py mirrors it) and of learned
    /// words.
    ///
    /// Nogai is written with the 33 Russian letters; its four extra letters
    /// are written with two of those characters each (аь нъ оь уь). It is a
    /// Turkic language and has no palochka, so unlike the Dagestanian
    /// keyboards nothing is ever repaired into one: a Latin «I» or «l» next
    /// to Cyrillic letters stays what it is and makes the token invalid.
    /// The twelve Latin homoglyphs are repaired inside Cyrillic tokens (the
    /// dictionary source has words typed with a Latin «e» or «a»). «ь» and
    /// «ъ» extend the previous letter, so «аь», «нъ», «оь», «уь» count as
    /// one letter each and «уьй» has two letters. What is stored is what is
    /// typed: «аь» is always а + ь, never a single code point, so a word
    /// typed key by key and one picked from a long press are the same
    /// string.
    ///
    /// Identity is (id, version). Changing a rule means a new version, a
    /// dictionary rebuild and a sweep of learned data.
    static let normalization = NormalizationProfile(
        id: "nogai-cyrillic",
        version: 1,
        repairScripts: [0x0400...0x04FF],
        palochka: nil,
        palochkaLookalikes: [],
        homoglyphs: [
            "a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х",
            "y": "у", "k": "к", "m": "м", "t": "т", "b": "ь", "h": "н",
        ],
        rejectsASCIILetters: true,
        digraphTails: ["\u{044C}", "\u{044A}"]   // ь ъ
    )

    static let definition = KeyboardDefinition(
        // Stable identity: the extension's App Store bundle identifier.
        // Never reused for a different definition.
        id: "org.lekitech.nogaikeyboard.NogaiKeyboardExtension",
        data: LanguageData(
            appGroupID: NogaiIdentity.appGroupID,
            // NogaiKeyboardExtension/nogai_words.sqlite and
            // nogai_bigrams.sqlite, built by scripts/build_dictionary.py
            wordsArtifact: "nogai_words",
            bigramsArtifact: "nogai_bigrams",
            diagnosticsSubsystem: "NogaiKeyboardExtension"
        ),
        layout: NogaiLayout.capabilities,
        keys: NogaiStrings.keys,
        text: TextConventions(
            // No palochka: what is stored is what is shown and typed.
            visiblePalochka: nil,
            caseNeutral: []
        ),
        normalization: normalization,
        strings: NogaiStrings.strings,
        emojiCategoryTitles: NogaiStrings.emojiCategoryTitles
    )
}
