//
//  NogaiLayoutTests.swift
//  NogaiCoreTests
//
//  NogaiLayout.swift: the three letter rows, the one departure from the
//  Russian iOS layout (checked against the pinned transcription of that
//  layout, Fixtures/agisight/rus-3-rows.yaml), every long-press mapping,
//  the long-press assignment of the pinned Nogai mapping of Agisight
//  (nog_key_mapping.json), the alphabet, and the evidence the design rests
//  on: Agisight's letter counts of Nogai web text and the shipped
//  dictionary.
//

import XCTest
import SQLite3
import UIKit
@testable import NogaiCore
@testable import GeneralKeyboard

final class NogaiLayoutTests: NogaiTestCase {

    private var spec: LayoutStyleSpec { KeyboardDefinition.current.layout.spec(for: .standard) }

    private func characters(_ row: [KeyCap]) -> [String] {
        row.compactMap { if case .character(let c) = $0 { return c } else { return nil } }
    }

    private var letterKeys: [String] { spec.letterRows.flatMap(characters) }

    // MARK: - Minimal readers for the pinned files

    private func file(_ name: String) throws -> String {
        try RepoPaths.text(RepoPaths.upstream.appendingPathComponent(name))
    }

    /// Rows of one layer of `iOS: primary:` as key tokens; `\s{…}`
    /// specials (shift, backspace, spacers) are dropped.
    private func russianLayer(_ name: String) throws -> [[String]] {
        let lines = try file("rus-3-rows.yaml").components(separatedBy: "\n")
        guard let primary = lines.firstIndex(of: "  primary:"),
              let start = lines[primary...].firstIndex(where: {
                  $0.trimmingCharacters(in: .whitespaces) == "\(name): |" }) else {
            XCTFail("layer \(name) not found"); return []
        }
        let indent = lines[start].prefix(while: { $0 == " " }).count
        var rows: [[String]] = []
        for line in lines[(start + 1)...] {
            let lineIndent = line.prefix(while: { $0 == " " }).count
            if line.trimmingCharacters(in: .whitespaces).isEmpty || lineIndent <= indent { break }
            rows.append(line.split(separator: " ").map(String.init).filter { !$0.hasPrefix("\\s{") })
        }
        return rows
    }

    // MARK: - Letter rows

    func testLetterRows() {
        XCTAssertEqual(spec.letterRows.map(characters), [
            ["й", "ц", "у", "к", "е", "н", "г", "ш", "ъ", "з", "х"],
            ["ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"],
            ["я", "ч", "с", "м", "и", "т", "ь", "б", "ю"],
        ])
        XCTAssertEqual(spec.letterRows.count, 3)
        // Shift and backspace frame the third row
        XCTAssertEqual(spec.letterRows[2].first, .shift)
        XCTAssertEqual(spec.letterRows[2].last, .backspace)
        // No letter twice, no row wider than the Russian keyboard's 11 keys
        XCTAssertEqual(Set(letterKeys).count, letterKeys.count)
        XCTAssertEqual(spec.letterRows.map { characters($0).count }, [11, 11, 9])
        // Every key is one lowercase Cyrillic character
        for key in letterKeys {
            XCTAssertEqual(key.unicodeScalars.count, 1, key)
            XCTAssertTrue(Nogai.isPlainCyrillic(key), key)
            XCTAssertEqual(key, key.lowercased(), key)
        }
    }

    /// The layout is the Russian iOS layout with exactly one key changed:
    /// «ъ» where the Russian keyboard has «щ».
    func testOnlyOneKeyDiffersFromTheRussianLayout() throws {
        let russian = try russianLayer("default")
        XCTAssertEqual(russian.map(\.count), [11, 11, 9])
        let nogai = spec.letterRows.map(characters)
        var differences: [(String, String)] = []
        for (r, row) in russian.enumerated() {
            for (i, key) in row.enumerated() where nogai[r][i] != key {
                differences.append((key, nogai[r][i]))
            }
        }
        XCTAssertEqual(differences.count, 1)
        XCTAssertEqual(differences.first?.0, "щ")
        XCTAssertEqual(differences.first?.1, "ъ")
        // «ъ» sits in the top row three keys right of «н», under the same thumb
        XCTAssertEqual(nogai[0].firstIndex(of: "ъ"), 8)
        XCTAssertEqual(nogai[0].firstIndex(of: "н"), 5)
        // «ь» keeps its Russian key: «аь», «оь», «уь» need nothing new
        XCTAssertEqual(nogai[2].firstIndex(of: "ь"), 6)
    }

    /// The shift layer the engine derives equals the Russian shift layer
    /// with the same one change.
    func testShiftLayer() throws {
        let upstream = try russianLayer("shift")
        let shifted = spec.letterRows.map { row in
            characters(row).map { KeyboardLayout.label(for: .character($0), shifted: true, capsLock: false) }
        }
        XCTAssertEqual(shifted, upstream.map { $0.map { $0 == "Щ" ? "Ъ" : $0 } })
    }

    // MARK: - Number and symbol pages

    /// The pages of the Russian iOS keyboard, unchanged. The transcription
    /// writes the typographic “ and ’; the keyboard types the plain " and '
    /// like the sibling keyboards and offers the typographic ones on a
    /// long press.
    func testNumberAndSymbolPagesAreTheRussianOnes() throws {
        func plain(_ rows: [[String]]) -> [[String]] {
            rows.map { $0.map { $0 == "“" ? "\"" : $0 == "’" ? "'" : $0 } }
        }
        XCTAssertEqual(spec.numberRows.map(characters), plain(try russianLayer("symbols-1")))
        XCTAssertEqual(spec.symbolRows.map(characters), plain(try russianLayer("symbols-2")))
        XCTAssertEqual(spec.numberRows[2].first, .symbols)
        XCTAssertEqual(spec.symbolRows[2].first, .numbers)
        XCTAssertEqual(spec.numberRows[2].last, .backspace)
    }

    // MARK: - Long press

    func testLongPressMappings() {
        let letters: [String: [String]] = [
            "а": ["аь"],
            "н": ["нъ"],
            "о": ["оь"],
            "у": ["уь"],
            "е": ["ё"],
            "ш": ["щ"],
            "ь": ["ъ"],
        ]
        for (key, alternates) in letters {
            XCTAssertEqual(spec.callouts[key], alternates, key)
        }
        // No other letter key has a long press
        let letterCalloutKeys = spec.callouts.keys.filter { $0.first!.isLetter }
        XCTAssertEqual(Set(letterCalloutKeys), Set(letters.keys))
        // Every long-press base is a key of the layout, and no option
        // repeats its base key or another option
        let allKeys = Set((spec.letterRows + spec.numberRows + spec.symbolRows).flatMap(characters))
        for (key, alternates) in spec.callouts {
            XCTAssertTrue(allKeys.contains(key), "\(key) is not a key")
            XCTAssertFalse(alternates.contains(key), key)
            XCTAssertEqual(Set(alternates).count, alternates.count, key)
        }
    }

    /// Nothing of the sibling keyboards' Dagestanian letters, of the old
    /// Nogai alphabet («гъ», «къ», dropped in 1944) or of Kumyk («гь»,
    /// «нг») is offered, and no palochka anywhere.
    func testNoForeignLettersAreOffered() {
        let options = spec.callouts.values.flatMap { $0 } + Array(spec.callouts.keys) + letterKeys
        for foreign in ["гъ", "къ", "гь", "нг", "хъ", "кь", "\u{04C0}", "\u{04CF}"] {
            XCTAssertFalse(options.contains { $0.contains(foreign) }, foreign)
        }
        XCTAssertNil(spec.callouts["г"])
        XCTAssertNil(spec.callouts["к"])
    }

    /// Each option is exactly two plain Cyrillic characters that start
    /// with its base key: a sequence, never a single code point (not ә, ң,
    /// ө, ү of other Turkic alphabets), a Latin lookalike or a palochka.
    func testDigraphOptionsAreCyrillicSequences() {
        var offered: [String] = []
        for (key, alternates) in NogaiLayout.digraphCallouts {
            for option in alternates {
                XCTAssertEqual(option.unicodeScalars.count, 2, option)
                XCTAssertEqual(option.count, 2, option)
                XCTAssertTrue(option.hasPrefix(key), option)
                XCTAssertTrue(Nogai.isPlainCyrillic(option), option)
                XCTAssertEqual(option, option.precomposedStringWithCanonicalMapping, option)
                offered.append(option)
            }
        }
        XCTAssertEqual(offered.sorted(), Nogai.digraphs.sorted())
        XCTAssertEqual(Array("аь".unicodeScalars).map(\.value), [0x0430, 0x044C])
        XCTAssertEqual(Array("нъ".unicodeScalars).map(\.value), [0x043D, 0x044A])
        XCTAssertEqual(Array("оь".unicodeScalars).map(\.value), [0x043E, 0x044C])
        XCTAssertEqual(Array("уь".unicodeScalars).map(\.value), [0x0443, 0x044C])
    }

    /// The shift layer of an option capitalizes its first letter and Caps
    /// Lock both, as the alphabet writes them (Аь, Нъ, Оь, Уь).
    func testDigraphOptionsInShiftAndCapsLock() {
        for digraph in Nogai.digraphs {
            let first = String(digraph.prefix(1)).uppercased() + digraph.dropFirst()
            XCTAssertEqual(KeyboardLayout.label(for: .character(digraph), shifted: true, capsLock: false), first)
            XCTAssertEqual(KeyboardLayout.label(for: .character(digraph), shifted: true, capsLock: true),
                           digraph.uppercased())
        }
    }

    /// The four letters sit under the same Russian keys as in the Nogai
    /// mapping of Agisight/rf-keyboard-corpora.
    func testDigraphAssignmentMatchesThePinnedNogaiMapping() throws {
        let data = try Data(contentsOf: RepoPaths.upstream.appendingPathComponent("nog_key_mapping.json"))
        let upstream = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: [String]])
        XCTAssertEqual(upstream.count, 4)
        var lowercased: [String: [String]] = [:]
        for (key, values) in upstream { lowercased[key.lowercased()] = values.map { $0.lowercased() } }
        XCTAssertEqual(NogaiLayout.digraphCallouts, lowercased)
    }

    /// What docs/LAYOUT.md says about Agisight's draft layout
    /// (nog_key_default.json): 35 keys in rows of 12, 12 and 11, a key for
    /// each of Нъ, Аь, Оь, Уь. With shift and backspace the third row has
    /// 13 cells; this layout keeps the Russian keyboard's 11.
    func testThePinnedAgisightDraftIsWiderThanAnIPhoneRow() throws {
        struct Draft: Decodable {
            struct Key: Decodable { let label: String; let row: Int; let column: Int }
            let keys: [Key]
        }
        let data = try Data(contentsOf: RepoPaths.upstream.appendingPathComponent("nog_key_default.json"))
        let draft = try JSONDecoder().decode(Draft.self, from: data)
        XCTAssertEqual(draft.keys.count, 35)
        XCTAssertEqual([1, 2, 3].map { row in draft.keys.filter { $0.row == row }.count }, [12, 12, 11])
        XCTAssertEqual(Set(draft.keys.map(\.label).filter { $0.count == 2 }), ["Нъ", "Аь", "Оь", "Уь"])
        XCTAssertEqual(spec.letterRows.map(\.count), [11, 11, 11])
    }

    /// The symbol alternates are those of the Russian iOS keyboard.
    func testSymbolLongPressesAreTheRussianOnes() throws {
        var upstream: [String: [String]] = [:]
        for line in try file("rus-longpress.yaml").components(separatedBy: "\n") {
            guard let colon = line.range(of: ": ") else { continue }
            func unquote(_ s: Substring) -> String {
                let t = s.trimmingCharacters(in: .whitespaces)
                if t.count >= 2, let f = t.first, f == t.last, f == "'" || f == "\"" {
                    return String(t.dropFirst().dropLast())
                }
                return t
            }
            upstream[unquote(line[..<colon.lowerBound])] =
                unquote(line[colon.upperBound...]).split(separator: " ").map(String.init)
        }
        // Letters are Nogai's own (е → ё is shared; ь → ъ is kept too)
        XCTAssertEqual(upstream["е"], spec.callouts["е"])
        XCTAssertEqual(upstream["ь"], spec.callouts["ь"])
        for key in ["0", "₽", "#", ".", "%", "=", "-", "/", "&", "?", "!"] {
            XCTAssertEqual(spec.callouts[key], upstream[key], key)
        }
        // The quote alternates sit on this layout's ' and " keys; the
        // popup never repeats its base key
        XCTAssertEqual(spec.callouts["'"], upstream["’"]?.filter { $0 != "'" })
        XCTAssertEqual(spec.callouts["\""], upstream["“"]?.filter { $0 != "\"" })
    }

    // MARK: - Alphabet

    /// All 37 letters of the Nogai alphabet (the 33 Russian letters and
    /// аь, нъ, оь, уь) can be typed: from the keys, or one long press away.
    func testWholeAlphabetIsTypeable() {
        let alphabet = ["а", "аь", "б", "в", "г", "д", "е", "ё", "ж", "з", "и", "й", "к", "л", "м", "н",
                        "нъ", "о", "оь", "п", "р", "с", "т", "у", "уь", "ф", "х", "ц", "ч", "ш", "щ",
                        "ъ", "ы", "ь", "э", "ю", "я"]
        XCTAssertEqual(alphabet.count, 37)
        let keys = Set(letterKeys)
        let longPress = Set(spec.callouts.filter { keys.contains($0.key) }.flatMap(\.value))
        for letter in alphabet {
            let fromKeys = letter.allSatisfy { keys.contains(String($0)) }
            XCTAssertTrue(fromKeys || longPress.contains(letter), "\(letter) cannot be typed")
        }
        // Each of the four both ways: key by key, and as one long press
        for digraph in Nogai.digraphs {
            XCTAssertTrue(digraph.allSatisfy { keys.contains(String($0)) }, digraph)
            XCTAssertTrue(longPress.contains(digraph), digraph)
        }
        // The only letters without a key of their own
        let russian = Set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя".map(String.init))
        XCTAssertEqual(russian.subtracting(keys), ["ё", "щ"])
        XCTAssertTrue(longPress.isSuperset(of: ["ё", "щ"]))
    }

    // MARK: - The evidence

    /// The layout rests on Agisight's letter counts of Nogai web text
    /// (docs/LAYOUT.md). The claims are checked against the pinned table.
    func testWebTextFrequenciesSupportTheLayout() throws {
        var counts: [String: Double] = [:]
        for line in try file("nog_monocorpus_freq.csv").components(separatedBy: "\n").dropFirst() {
            let cells = line.split(separator: ",")
            if cells.count == 3, let n = Double(cells[1]) { counts[cells[0].lowercased()] = n }
        }
        XCTAssertEqual(counts.count, 37)
        let total = counts.values.reduce(0, +)
        XCTAssertEqual(total, 3_783_628)
        func share(_ letter: String) -> Double { 100 * (counts[letter] ?? 0) / total }

        // «нъ» is a frequent letter, «щ» a very rare one: 50 times apart
        XCTAssertEqual(share("нъ"), 1.249, accuracy: 0.001)
        XCTAssertEqual(share("щ"), 0.024, accuracy: 0.001)
        XCTAssertGreaterThan(share("нъ"), 50 * share("щ"))
        // «ъ» outside «нъ» and «ё» are rarer still
        XCTAssertLessThan(share("ъ"), 0.04)
        XCTAssertLessThan(share("ё"), 0.01)
        // The four letters together, and their order
        XCTAssertEqual(Nogai.digraphs.map(share).reduce(0, +), 3.32, accuracy: 0.01)
        XCTAssertGreaterThan(share("нъ"), share("оь"))
        XCTAssertGreaterThan(share("оь"), share("уь"))
        XCTAssertGreaterThan(share("уь"), share("аь"))
        // Long presses per 100 letters: the Russian layout (every «нъ»,
        // «ъ», «ё») against this one («щ», «ё»)
        XCTAssertEqual(share("нъ") + share("ъ") + share("ё"), 1.288, accuracy: 0.001)
        XCTAssertEqual(share("щ") + share("ё"), 0.029, accuracy: 0.001)
    }

    /// The same claims on the shipped dictionary, so a future dictionary
    /// that no longer supports them fails here.
    func testDictionaryFrequenciesSupportTheLayout() throws {
        var db: OpaquePointer?
        XCTAssertEqual(sqlite3_open_v2(RepoPaths.wordsArtifact.path, &db, SQLITE_OPEN_READONLY, nil), SQLITE_OK)
        defer { sqlite3_close(db) }
        var stmt: OpaquePointer?
        XCTAssertEqual(sqlite3_prepare_v2(db, "SELECT word, base_score FROM words", -1, &stmt, nil), SQLITE_OK)
        var characters: [Character: Int] = [:]
        var pairs: [String: Int] = [:]
        while sqlite3_step(stmt) == SQLITE_ROW {
            let word = Array(String(cString: sqlite3_column_text(stmt, 0)))
            let count = Int(sqlite3_column_int64(stmt, 1)) / 10
            guard count > 0 else { continue }
            for (i, ch) in word.enumerated() where ch != "-" {
                characters[ch, default: 0] += count
                if i > 0 { pairs[String([word[i - 1], ch]), default: 0] += count }
            }
        }
        sqlite3_finalize(stmt)
        let total = Double(characters.values.reduce(0, +))
        func share(_ ch: Character) -> Double { 100 * Double(characters[ch] ?? 0) / total }

        // «ъ» stands after «н» and nowhere else; «щ» is rarer than in web text
        let hard = Double(characters["ъ"]!)
        XCTAssertGreaterThan(Double(pairs["нъ"]!) / hard, 0.99)
        XCTAssertGreaterThan(share("ъ"), 0.5)
        XCTAssertLessThan(share("щ"), 0.01)
        XCTAssertLessThan(share("ё"), 0.01)
        // «ь» belongs to «уь», «оь», «аь» (in that order here: the
        // dictionary's verbal nouns end in «-уьв»)
        let soft = Double(characters["ь"]!)
        XCTAssertGreaterThan(Double(pairs["уь"]! + pairs["оь"]! + pairs["аь"]!) / soft, 0.99)
        XCTAssertGreaterThan(pairs["уь"]!, pairs["оь"]!)
        XCTAssertGreaterThan(pairs["оь"]!, pairs["нъ"]!)
        XCTAssertGreaterThan(pairs["нъ"]!, pairs["аь"]!)
        // The letters of the old alphabet and of Kumyk are not in use
        XCTAssertLessThanOrEqual(pairs["гъ"] ?? 0, 1)
        XCTAssertLessThanOrEqual(pairs["къ"] ?? 0, 1)
        XCTAssertEqual(pairs["гь"] ?? 0, 0)
    }
}
