//
//  DictionaryTests.swift
//  NogaiCoreTests
//
//  The SHIPPED artifacts (NogaiKeyboardExtension/nogai_words.sqlite and
//  nogai_bigrams.sqlite, built by scripts/build_dictionary.py) through the
//  engine's readers: metadata, counts, the canonical form of every lookup
//  key, prefix suggestions ranked by frequency, next words from real
//  bigrams, what the repaired reading of the sources removed and
//  restored, and the merges. The figures are those of cleanup version 1
//  (docs/DICTIONARY.md).
//

import XCTest
import SQLite3
@testable import NogaiCore
@testable import GeneralKeyboard

final class DictionaryTests: NogaiTestCase {

    private var words: WordSuggestions!
    private var bigrams: StaticBigrams!

    override func setUpWithError() throws {
        try super.setUpWithError()
        words = try XCTUnwrap(WordSuggestions(databaseURL: RepoPaths.wordsArtifact))
        bigrams = try XCTUnwrap(StaticBigrams(databaseURL: RepoPaths.bigramsArtifact))
    }

    private func meta(_ url: URL) throws -> [String: String] {
        var db: OpaquePointer?
        XCTAssertEqual(sqlite3_open_v2(url.path, &db, SQLITE_OPEN_READONLY, nil), SQLITE_OK)
        defer { sqlite3_close(db) }
        var stmt: OpaquePointer?
        XCTAssertEqual(sqlite3_prepare_v2(db, "SELECT key, value FROM meta", -1, &stmt, nil), SQLITE_OK)
        defer { sqlite3_finalize(stmt) }
        var values: [String: String] = [:]
        while sqlite3_step(stmt) == SQLITE_ROW {
            values[String(cString: sqlite3_column_text(stmt, 0))] = String(cString: sqlite3_column_text(stmt, 1))
        }
        return values
    }

    func testArtifactMetadata() throws {
        let w = try XCTUnwrap(words.metadata)
        XCTAssertEqual(w.artifact, "nogai_words")
        XCTAssertEqual(w.schemaVersion, 1)
        XCTAssertEqual(w.contentVersion, 1)
        XCTAssertEqual(w.normalizationVersion, Normalization.version)
        XCTAssertEqual(w.minReaderSchema, 1)
        XCTAssertEqual(w.rowCount, 17145)
        let b = try XCTUnwrap(bigrams.metadata)
        XCTAssertEqual(b.artifact, "nogai_bigrams")
        XCTAssertEqual(b.rowCount, 2317)
        XCTAssertEqual(b.normalizationVersion, Normalization.version)
        XCTAssertFalse(bigrams.isEmpty)
        // Both artifacts name the profile they are canonical under
        for url in [RepoPaths.wordsArtifact, RepoPaths.bigramsArtifact] {
            let values = try meta(url)
            XCTAssertEqual(values["normalization_profile"], KeyboardDefinition.current.normalization.id)
            XCTAssertEqual(values["language"], "nog")
            XCTAssertEqual(values["cleanup_version"], "1")
        }
    }

    /// Every stored key is already canonical (lowercase, NFC), valid under
    /// the token contract and written with Nogai letters only, and every
    /// bigram word is a row of the words artifact, so a lookup never
    /// misses by representation.
    func testEveryRowIsCanonicalAndValid() throws {
        var db: OpaquePointer?
        XCTAssertEqual(sqlite3_open_v2(RepoPaths.wordsArtifact.path, &db, SQLITE_OPEN_READONLY, nil), SQLITE_OK)
        defer { sqlite3_close(db) }
        var stmt: OpaquePointer?
        XCTAssertEqual(sqlite3_prepare_v2(db, "SELECT word, base_score FROM words", -1, &stmt, nil), SQLITE_OK)
        var all = Set<String>()
        var minScore = Int.max
        while sqlite3_step(stmt) == SQLITE_ROW {
            let word = String(cString: sqlite3_column_text(stmt, 0))
            minScore = min(minScore, Int(sqlite3_column_int64(stmt, 1)))
            XCTAssertTrue(Normalization.isCanonical(word), word)
            XCTAssertTrue(Normalization.isValidToken(word), word)
            XCTAssertTrue(Nogai.isPlainCyrillic(word.replacingOccurrences(of: "-", with: "")), word)
            all.insert(word)
        }
        sqlite3_finalize(stmt)
        XCTAssertEqual(all.count, 17145)
        XCTAssertGreaterThanOrEqual(minScore, 1)

        var bdb: OpaquePointer?
        XCTAssertEqual(sqlite3_open_v2(RepoPaths.bigramsArtifact.path, &bdb, SQLITE_OPEN_READONLY, nil), SQLITE_OK)
        defer { sqlite3_close(bdb) }
        XCTAssertEqual(sqlite3_prepare_v2(bdb, "SELECT prev, word, weight FROM bigrams", -1, &stmt, nil), SQLITE_OK)
        var pairs = 0
        while sqlite3_step(stmt) == SQLITE_ROW {
            let prev = String(cString: sqlite3_column_text(stmt, 0))
            let word = String(cString: sqlite3_column_text(stmt, 1))
            XCTAssertTrue(all.contains(prev), prev)
            XCTAssertTrue(all.contains(word), word)
            XCTAssertGreaterThanOrEqual(sqlite3_column_int64(stmt, 2), 2)
            pairs += 1
        }
        sqlite3_finalize(stmt)
        XCTAssertEqual(pairs, 2317)
    }

    /// Frequency ranks the prefix candidates, for prefixes that end inside
    /// or right after each of the four two-character letters.
    func testPrefixSuggestionsAreRankedByFrequency() {
        XCTAssertEqual(words.suggestions(for: "аь"), ["аьр", "аьдем", "аьл"])
        XCTAssertEqual(words.suggestions(for: "оь"), ["оьз", "оьтуьв", "оьзи"])
        XCTAssertEqual(words.suggestions(for: "уьй"), ["уьйкен", "уьй", "уьйретуьв"])
        XCTAssertEqual(words.suggestions(for: "куь"), ["куьшли", "куьн", "куьш"])
        XCTAssertEqual(words.suggestions(for: "сонъ"), ["сонъ", "сонъы", "сонъгы"])
        XCTAssertEqual(words.suggestions(for: "тенъ"), ["тенъ", "тенъиз", "тенълестируьв"])
        XCTAssertEqual(words.suggestions(for: "соьз"), ["соьз", "соьзсиз", "соьзлер"])
        XCTAssertEqual(words.suggestions(for: "бол"), ["болув", "болмаган", "болып"])
        XCTAssertEqual(words.suggestions(for: "ю"), ["юруьв", "ювык", "юмсак"])
        // «нъ» never begins a Nogai word
        XCTAssertEqual(words.suggestions(for: "нъ"), [])
        XCTAssertEqual(words.suggestions(for: "ъъъ"), [])
    }

    /// A prefix in capitals, with a Latin lookalike or in decomposed
    /// Unicode reaches the same rows.
    func testPrefixLookupNormalizes() {
        let canonical = words.suggestions(for: "уьй")
        XCTAssertEqual(words.suggestions(for: "Уьй"), canonical)
        XCTAssertEqual(words.suggestions(for: "УЬЙ"), canonical)
        XCTAssertEqual(words.suggestions(for: "yьй"), canonical)                    // Latin y
        XCTAssertEqual(words.suggestions(for: "самоле\u{0308}"), words.suggestions(for: "самолё"))
        XCTAssertEqual(words.suggestions(for: "самолё"), ["самолёттинъ"])
        XCTAssertTrue(words.contains("Уьйкен"))
        XCTAssertTrue(words.contains("СЕНИНЪ"))
        XCTAssertTrue(words.contains("аьдем"))
        // «аь» and «а» are different letters: «аьр» every, «ар» honour
        XCTAssertNotEqual(words.suggestions(for: "аьр"), words.suggestions(for: "ар"))
        XCTAssertTrue(words.contains("аьр"))
        XCTAssertTrue(words.contains("ар"))
    }

    /// What v0 read as Nogai and is not: the Russian sense glosses and
    /// translations of the source dictionary, suffix citations, and the
    /// pieces of words its reader cut.
    func testRussianGlossesAndFragmentsAreGone() {
        for word in ["переносном", "значении", "очень", "сделать", "что-л", "начать", "человеке"] {
            XCTAssertFalse(words.contains(word), word)
        }
        // «улдыз» was «йулдыз» cut at a decomposed й; «енинъ», «нга» were
        // endings of pronoun forms in the Apertium lexicon
        for piece in ["улдыз", "енинъ", "нга", "ннан"] {
            XCTAssertFalse(words.contains(piece), piece)
        }
        // Words that Russian also has stay: they are Nogai words here
        for word in ["не", "да", "бас", "ер", "мен"] {
            XCTAssertTrue(words.contains(word), word)
        }
        XCTAssertEqual(bigrams.nextWords(after: "переносном"), [])
    }

    /// Nogai words v0 lost and the repaired reading has.
    func testRestoredWordsArePresent() {
        // Lines v0's Russian filter dropped («(заставить уснуть) уйклатув»)
        XCTAssertTrue(words.contains("куьшинде"))
        XCTAssertTrue(words.contains("биргелей"))
        // One-word fields with a question mark («кайда?»)
        XCTAssertTrue(words.contains("кайда"))
        XCTAssertTrue(words.contains("кашан"))
        // Pronoun forms put together from the Apertium lexicon
        for word in ["мага", "сенинъ", "онынъ", "бизге", "сизди"] {
            XCTAssertTrue(words.contains(word), word)
        }
        // IDS forms with a decomposed й
        XCTAssertTrue(words.contains("кайыр"))
    }

    /// The three spelling rules merged a variant into the attested word
    /// and invented nothing.
    func testMergedVariantsAreGone() {
        // S1: «ъ» typed for «ь» after а, о, у
        XCTAssertFalse(words.contains("соъз"))
        XCTAssertTrue(words.contains("соьз"))
        // S2: «нь» typed for «нъ»
        XCTAssertFalse(words.contains("сизинь"))
        XCTAssertTrue(words.contains("сизинъ"))
        // M1: the IDS transcription «йа», «йу» for the literary «я», «ю»
        XCTAssertFalse(words.contains("йулдыз"))
        XCTAssertTrue(words.contains("юлдыз"))
        XCTAssertFalse(words.contains("йаман"))
        XCTAssertTrue(words.contains("яман"))
        XCTAssertFalse(words.contains("бийуьв"))
        XCTAssertTrue(words.contains("биюв"))
        // Not merged: no literary form in the sources, or not a rule
        XCTAssertTrue(words.contains("вентилйатор"))
        XCTAssertFalse(words.contains("вентилятор"))
        XCTAssertTrue(words.contains("этсуърткиш"))
        XCTAssertTrue(words.contains("къуллыкъ"))
        // A hyphenated word is offered from the part before the hyphen
        XCTAssertEqual(words.suggestions(for: "ян-").first, "ян-якка")
    }

    func testNextWordsComeFromRealBigrams() {
        XCTAssertEqual(bigrams.nextWords(after: "бир"), ["аз", "зат", "ерге"])
        XCTAssertEqual(bigrams.nextWords(after: "йок"), ["этуьв", "болув", "болып"])
        XCTAssertEqual(bigrams.nextWords(after: "тагы"), ["да", "бир"])
        XCTAssertEqual(bigrams.nextWords(after: "куллык").first, "этуьв")
        XCTAssertEqual(bigrams.nextWords(after: "БиР"), ["аз", "зат", "ерге"])
        XCTAssertEqual(bigrams.nextWords(after: "ъъъ"), [])
        // Two words with a comma between them in the source are not a pair:
        // v0 had «кувув кувып» from «кувув, кувып шыгарув»
        XCTAssertFalse(bigrams.nextWords(after: "кувув").contains("кувып"))
        // Static context reorders dictionary candidates among themselves
        let weights = bigrams.weights(after: "бир", candidates: ["кесек", "зат", "ъъъ"])
        XCTAssertEqual(weights, ["зат": 41, "кесек": 12])
    }

    func testRandomIdleWordsComeFromTheDictionary() {
        let idle = words.randomWords(3)
        XCTAssertEqual(idle.count, 3)
        for word in idle { XCTAssertTrue(words.contains(word), word) }
    }
}
