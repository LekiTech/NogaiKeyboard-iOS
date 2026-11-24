//
//  TypingAndLearningTests.swift
//  NogaiCoreTests
//
//  The keyboard model built exactly as the extension builds it (its own
//  UserDefaults, its own learned store), fed through a mock host: the keys
//  and the long-press options insert Nogai digraphs as Cyrillic sequences
//  in lowercase, title case and uppercase, typed and picked words are
//  learned and come back, settings persist. The bundled artifacts are not
//  in the test bundle, so the model's dictionary tier is empty here; the
//  dictionary itself is covered by DictionaryTests. Every word is a real
//  word of the Nogai dictionary.
//

import XCTest
import UIKit
@testable import NogaiCore
@testable import GeneralKeyboard

final class TypingAndLearningTests: NogaiTestCase {

    private static let persistedKeys = [
        "layoutStyle", "recentEmojis",
        "set_wordSuggestions", "set_nextWordSuggestions", "set_autoSpaceAfterSuggestion",
        "set_doubleSpacePeriod", "set_spaceCursor", "set_spaceLabel",
        "set_learnSpeed", "set_calloutDelay", "set_theme",
    ]

    override func setUp() {
        super.setUp()
        for key in Self.persistedKeys { UserDefaults.standard.removeObject(forKey: key) }
        // Empty the learned store IN PLACE; never delete learned.sqlite
        // while a model may still hold it open.
        LearnedWords()?.reset()
        // These tests follow a word from its first use, so they run with
        // Fast selected, the way a user picks it in the settings panel.
        // The default (Normal, three uses) has its own tests under
        // "Learning speed", which start without a stored choice.
        UserDefaults.standard.set("fast", forKey: "set_learnSpeed")
    }

    @MainActor
    private func type(_ text: String, into model: KeyboardModel, proxy: MockTextDocumentProxy) {
        for ch in text {
            model.handleKey(ch == " " ? .space : .character(String(ch)), proxy: proxy)
            model.updateSuggestions(proxy: proxy)
        }
    }

    /// What the keyboard does when a suggestion is tapped: the typed
    /// prefix is replaced by the word and a space, and the model is told.
    @MainActor
    private func pick(_ word: String, in model: KeyboardModel, proxy: MockTextDocumentProxy) {
        let previous = model.previousWord(proxy: proxy)
        for _ in 0..<model.wordPrefix(proxy: proxy).count { proxy.deleteBackward() }
        proxy.insertText(word + " ")
        model.recordPickedSuggestion(word, previous: previous, insertedSpace: true)
        model.updateSuggestions(proxy: proxy)
    }

    // MARK: - Rows

    @MainActor
    func testKeyboardShowsThreeLetterRowsAndTheBottomRow() {
        let model = KeyboardModel()
        let rows = model.rows(needsGlobe: true)
        XCTAssertEqual(rows.count, 4)
        XCTAssertEqual(rows[0].count, 11)
        XCTAssertEqual(rows[1].count, 11)
        XCTAssertEqual(rows[2].count, 11)   // shift, nine letters, backspace
        XCTAssertEqual(rows[0][8], .character("ъ"))
        XCTAssertEqual(rows[3], [.numbers, .settings, .emoji, .globe, .space, .return])
        XCTAssertEqual(model.rows(needsGlobe: false)[3], [.numbers, .settings, .emoji, .space, .return])
        XCTAssertEqual(model.layoutStyle, .standard)
    }

    // MARK: - Keys and digraphs

    @MainActor
    func testEveryLetterKeyInsertsItsLetter() {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        let letters = "йцукенгшъзхфывапролджэячсмитьбю"
        for ch in letters { model.handleKey(.character(String(ch)), proxy: proxy) }
        XCTAssertEqual(proxy.before, letters)
        XCTAssertFalse(proxy.before.contains(where: Nogai.palochkas.contains))
    }

    /// The four two-character letters typed key by key, as Cyrillic sequences.
    @MainActor
    func testDigraphsTypedKeyByKey() {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        type("аь нъ оь уь", into: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "аь нъ оь уь")
        XCTAssertEqual(Array(proxy.before.prefix(5).unicodeScalars).map(\.value),
                       [0x0430, 0x044C, 0x0020, 0x043D, 0x044A])
        XCTAssertTrue(Nogai.isPlainCyrillic(proxy.before.replacingOccurrences(of: " ", with: "")))
    }

    /// A long-press option inserts the complete digraph; the result is the
    /// same string as typing its two keys.
    @MainActor
    func testLongPressOptionsInsertWholeDigraphs() {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        for option in ["аь", "нъ", "оь", "уь", "ё", "щ", "ъ"] {
            model.handleKey(.character(option), proxy: proxy)
        }
        XCTAssertEqual(proxy.before, "аьнъоьуьёщъ")
        XCTAssertEqual(Array(proxy.before.unicodeScalars).count, 11)
        XCTAssertTrue(Nogai.isPlainCyrillic(proxy.before))

        let typed = MockTextDocumentProxy()
        for ch in "аьнъоьуь" { model.handleKey(.character(String(ch)), proxy: typed) }
        XCTAssertEqual(Array(typed.before.unicodeScalars), Array("аьнъоьуь".unicodeScalars))
        XCTAssertTrue(proxy.before.hasPrefix(typed.before))
    }

    /// Shift capitalizes the first letter of a digraph («Нъ», «Оь»), Caps
    /// Lock all of it («НЪ», «ОЬ»), for long-press options and plain keys
    /// alike.
    @MainActor
    func testShiftAndCapsLockOnDigraphs() {
        let model = KeyboardModel()
        let titleCase = ["аь": "Аь", "нъ": "Нъ", "оь": "Оь", "уь": "Уь", "ё": "Ё", "щ": "Щ"]
        let upperCase = ["аь": "АЬ", "нъ": "НЪ", "оь": "ОЬ", "уь": "УЬ", "ё": "Ё", "щ": "Щ"]
        for (option, expected) in titleCase {
            let proxy = MockTextDocumentProxy()
            model.shiftState = .once
            model.handleKey(.character(option), proxy: proxy)
            XCTAssertEqual(proxy.before, expected)
            XCTAssertEqual(model.shiftState, .off)
            // The key label previews exactly what a tap inserts
            XCTAssertEqual(KeyboardLayout.label(for: .character(option), shifted: true, capsLock: false), expected)
        }
        for (option, expected) in upperCase {
            let proxy = MockTextDocumentProxy()
            model.shiftState = .capsLock
            model.handleKey(.character(option), proxy: proxy)
            XCTAssertEqual(proxy.before, expected)
            XCTAssertEqual(model.shiftState, .capsLock)
            XCTAssertEqual(KeyboardLayout.label(for: .character(option), shifted: true, capsLock: true), expected)
        }
        // Key by key: Shift, then с е н и н ъ → «Сенинъ»; Caps Lock → «СЕНИНЪ»
        let proxy = MockTextDocumentProxy()
        model.shiftState = .once
        type("сенинъ", into: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "Сенинъ")
        proxy.before = ""
        model.shiftState = .capsLock
        type("сенинъ", into: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "СЕНИНЪ")
        model.shiftState = .off
    }

    @MainActor
    func testSentenceStartShiftsAndSpaceBehaviour() {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        XCTAssertEqual(model.shiftState, .once)   // new field: auto-capitalized
        type("оьзи", into: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "Оьзи")
        model.handleKey(.space, proxy: proxy)
        XCTAssertEqual(proxy.before, "Оьзи ")
        XCTAssertEqual(model.composedWord, "")
        // A long-press digraph at the start of a sentence is title case
        let fresh = MockTextDocumentProxy()
        let again = KeyboardModel()
        again.handleKey(.character("уь"), proxy: fresh)
        type("йкен", into: again, proxy: fresh)
        XCTAssertEqual(fresh.before, "Уьйкен")
    }

    // MARK: - Learning

    @MainActor
    func testTypedWordIsLearnedAndSuggested() throws {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        type("ногайша ", into: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "ногайша ")
        let store = try XCTUnwrap(LearnedWords())
        XCTAssertTrue(store.isRecognized("ногайша"))
        XCTAssertTrue(store.isRecognized("Ногайша"))
        XCTAssertTrue(store.isRecognized("НОГАЙША"))
        XCTAssertEqual(store.topWords(limit: 5), ["ногайша"])
        // Suggested back while typing its prefix. The bar leads with the
        // typed prefix as a quoted literal (it is not a word of its own),
        // the learned word follows.
        type("ног", into: model, proxy: proxy)
        XCTAssertEqual(model.suggestions, ["ног", "ногайша"])
        XCTAssertTrue(model.isLearnedSuggestion("ногайша"))
        XCTAssertEqual(model.savedWords(), ["ногайша"])
    }

    /// A capitalized prefix capitalizes the suggestion's first letter only:
    /// «Анъ…» is a title-case prefix, not an all-caps one.
    @MainActor
    func testSuggestionFollowsTheCaseOfADigraphPrefix() {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        type("анълатув оьзине ", into: model, proxy: proxy)
        proxy.before = ""
        model.syncComposedWord(proxy: proxy)
        model.shiftState = .once
        type("анъ", into: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "Анъ")
        XCTAssertTrue(model.suggestions.contains("Анълатув"), "\(model.suggestions)")
        proxy.before = ""
        model.syncComposedWord(proxy: proxy)
        model.shiftState = .capsLock
        type("оьз", into: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "ОЬЗ")
        XCTAssertTrue(model.suggestions.contains("ОЬЗИНЕ"), "\(model.suggestions)")
        model.shiftState = .off
    }

    /// Tapping a suggestion replaces the prefix with the whole word, with
    /// its digraphs intact, and adds the space.
    @MainActor
    func testAcceptedSuggestionInsertsTheWholeWord() throws {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        type("анълатув ", into: model, proxy: proxy)
        type("анъ", into: model, proxy: proxy)
        XCTAssertEqual(model.suggestions, ["анъ", "анълатув"])
        pick("анълатув", in: model, proxy: proxy)
        XCTAssertEqual(proxy.before, "анълатув анълатув ")
        XCTAssertEqual(model.composedWord, "")
        // The pick itself counts as a stronger use than typing
        let store = try XCTUnwrap(LearnedWords())
        XCTAssertTrue(store.isRecognized("анълатув"))
        // Sentence punctuation right after a picked word swallows the
        // automatic space
        model.handleKey(.character("."), proxy: proxy)
        XCTAssertEqual(proxy.before, "анълатув анълатув.")
    }

    @MainActor
    func testLearnedWordsSurviveANewModel() {
        do {
            let model = KeyboardModel()
            let proxy = MockTextDocumentProxy()
            model.shiftState = .off
            type("тенъизде оьзине ", into: model, proxy: proxy)
        }
        // A new keyboard controller (new model, same container)
        let again = KeyboardModel()
        let proxy = MockTextDocumentProxy(before: "тенъизде ")
        again.shiftState = .off
        again.syncComposedWord(proxy: proxy)
        XCTAssertEqual(again.savedWords().sorted(), ["оьзине", "тенъизде"])
        type("оьз", into: again, proxy: proxy)
        XCTAssertEqual(again.suggestions, ["оьз", "оьзине"])
    }

    @MainActor
    func testPersonalBigramPredictsTheNextWord() {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        // A pair seen twice is confident enough to predict (minPairUses)
        type("ана тил ", into: model, proxy: proxy)
        type("ана тил ", into: model, proxy: proxy)
        // After the first word and a space, its learned follower leads the bar
        type("ана ", into: model, proxy: proxy)
        XCTAssertEqual(model.suggestions.first, "тил")
    }

    @MainActor
    func testDeletingALearnedWordRemovesIt() throws {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        type("уьйкенлик сонъында ", into: model, proxy: proxy)
        XCTAssertEqual(model.savedWords().sorted(), ["сонъында", "уьйкенлик"])
        model.deleteLearnedWord("уьйкенлик", proxy: proxy)
        XCTAssertEqual(model.savedWords(), ["сонъында"])
        XCTAssertFalse(try XCTUnwrap(LearnedWords()).isRecognized("уьйкенлик"))
        model.resetLearnedWords(proxy: proxy)
        XCTAssertEqual(model.savedWords(), [])
        XCTAssertFalse(try XCTUnwrap(LearnedWords()).isRecognized("сонъында"))
    }

    /// A lone digraph or a lone letter is not a word; the store refuses it.
    @MainActor
    func testSingleLettersAndLoneDigraphsAreNotLearned() throws {
        let model = KeyboardModel()
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        type("аь нъ оь а ", into: model, proxy: proxy)
        XCTAssertEqual(model.savedWords(), [])
        let store = try XCTUnwrap(LearnedWords())
        XCTAssertFalse(store.isRecognized("нъ"))
    }

    // MARK: - Settings

    @MainActor
    func testSettingsPersistAcrossModels() {
        UserDefaults.standard.removeObject(forKey: "set_learnSpeed")   // a fresh install
        let model = KeyboardModel()
        XCTAssertEqual(model.settings.learnSpeed, .normal)
        XCTAssertEqual(model.settings.theme, .system)
        model.updateSettings {
            $0.theme = .dark
            $0.learnSpeed = .conservative
            $0.calloutDelay = .long
            $0.nextWordSuggestions = false
        }
        let again = KeyboardModel()
        XCTAssertEqual(again.settings.theme, .dark)
        XCTAssertEqual(again.settings.learnSpeed, .conservative)
        XCTAssertEqual(again.settings.calloutDelay, .long)
        XCTAssertFalse(again.settings.nextWordSuggestions)
        XCTAssertEqual(UserDefaults.standard.string(forKey: "set_theme"), "dark")
        XCTAssertEqual(model.layoutStyle, .standard)
    }

    // MARK: - Learning speed

    /// A fresh install has no stored learning speed and follows General
    /// Keyboard's default, Normal: a word is suggested after three uses.
    @MainActor
    func testFreshInstallLearnsAWordAfterThreeUses() {
        UserDefaults.standard.removeObject(forKey: "set_learnSpeed")
        let model = KeyboardModel()
        XCTAssertEqual(model.settings.learnSpeed, .normal)
        XCTAssertEqual(model.settings.learnSpeed.minUses, 3)
        let proxy = MockTextDocumentProxy()
        model.shiftState = .off
        type("ногайша ", into: model, proxy: proxy)
        XCTAssertEqual(model.savedWords(), [], "1 of 3 uses")
        type("ногайша ", into: model, proxy: proxy)
        XCTAssertEqual(model.savedWords(), [], "2 of 3 uses")
        type("ногайша ", into: model, proxy: proxy)
        XCTAssertEqual(model.savedWords(), ["ногайша"])
        type("ног", into: model, proxy: proxy)
        XCTAssertEqual(model.suggestions, ["ног", "ногайша"])
        // Following the default stores nothing
        XCTAssertNil(UserDefaults.standard.object(forKey: "set_learnSpeed"))
    }

    /// A learning speed the user saved is kept: Fast stays Fast and Slow
    /// stays Slow, and words learned earlier are neither deleted nor reset.
    @MainActor
    func testSavedLearningSpeedAndLearnedWordsAreKept() throws {
        for (raw, speed) in [("fast", KeyboardSettings.LearnSpeed.fast), ("conservative", .conservative)] {
            UserDefaults.standard.set(raw, forKey: "set_learnSpeed")
            XCTAssertEqual(KeyboardModel().settings.learnSpeed, speed, raw)
            XCTAssertEqual(UserDefaults.standard.string(forKey: "set_learnSpeed"), raw)
        }
        // A word used once before the default was Normal, no stored choice
        UserDefaults.standard.removeObject(forKey: "set_learnSpeed")
        try XCTUnwrap(LearnedWords()).learn("ногайша", previous: nil, picked: false)
        let model = KeyboardModel()
        XCTAssertEqual(model.savedWords(), [])
        XCTAssertTrue(try XCTUnwrap(LearnedWords()).isRecognized("ногайша"), "the row and its count are still stored")
        model.updateSettings { $0.learnSpeed = .fast }
        XCTAssertEqual(model.savedWords(), ["ногайша"])
    }
}
