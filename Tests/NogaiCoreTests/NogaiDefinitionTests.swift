//
//  NogaiDefinitionTests.swift
//  NogaiCoreTests
//
//  The Nogai KeyboardDefinition: its own identity (never another product's),
//  the persisted contract, a normalization profile without the palochka
//  convention of the sibling keyboards, and the project's two-target,
//  two-identity setup (Debug for the developer's team, Release for
//  distribution).
//

import XCTest
import UIKit
@testable import NogaiCore
@testable import GeneralKeyboard

final class NogaiDefinitionTests: NogaiTestCase {

    private var d: KeyboardDefinition { KeyboardDefinition.current }

    func testIdentityAndArtifacts() {
        XCTAssertEqual(d.validationErrors(), [])
        XCTAssertEqual(d.id, "org.lekitech.nogaikeyboard.NogaiKeyboardExtension")
        XCTAssertEqual(NogaiIdentity.releaseAppGroupID, "group.org.lekitech.nogaikeyboard")
        XCTAssertEqual(NogaiIdentity.debugAppGroupID, "group.org.lekitech.nogaikeyboard.dev")
        // Tests build in Debug
        XCTAssertEqual(d.data.appGroupID, NogaiIdentity.debugAppGroupID)
        XCTAssertEqual(WordSuggestions.artifactName, "nogai_words")
        XCTAssertEqual(StaticBigrams.artifactName, "nogai_bigrams")
        XCTAssertEqual(d.data.diagnosticsSubsystem, "NogaiKeyboardExtension")
    }

    func testNeverReusesAnotherProductsIdentity() {
        let taken = ["lezgi", "avar", "dargwa", "kumyk", "tabasaran", "lakkeyboard", "aghul", "rutul", "tsakhur",
                     "vadivian", "generalkeyboard", "reference"]
        for value in [d.id, d.data.appGroupID, NogaiIdentity.releaseAppGroupID,
                      d.data.wordsArtifact, d.data.bigramsArtifact, d.normalization.id] {
            for other in taken {
                XCTAssertFalse(value.lowercased().contains(other), "\(value) contains \(other)")
            }
        }
    }

    // MARK: - Normalization

    /// Nogai has its own profile: no palochka, so nothing is ever repaired
    /// into one, and «ъ» «ь» are the only digraph tails.
    func testNormalizationProfileIsNogaisOwn() {
        let n = d.normalization
        XCTAssertEqual(n.id, "nogai-cyrillic")
        XCTAssertEqual(n.version, 1)
        XCTAssertNotEqual(n, .dagestanianCyrillicV1)
        XCTAssertNil(n.palochka)
        XCTAssertTrue(n.palochkaLookalikes.isEmpty)
        XCTAssertEqual(n.digraphTails, ["ъ", "ь"])
        XCTAssertTrue(n.rejectsASCIILetters)
        XCTAssertEqual(n.homoglyphs, NormalizationProfile.dagestanianCyrillicV1.homoglyphs)
        XCTAssertNil(d.text.visiblePalochka)
        XCTAssertTrue(d.text.caseNeutral.isEmpty)
        XCTAssertNil(Normalization.palochka)
        XCTAssertEqual(Normalization.version, 1)
    }

    func testCanonicalFormOfNogaiWords() {
        XCTAssertEqual(Normalization.canonical("Ногай"), "ногай")
        XCTAssertEqual(Normalization.canonical("  АЬР\n"), "аьр")
        XCTAssertEqual(Normalization.canonical("УЬЙКЕН"), "уьйкен")
        XCTAssertEqual(Normalization.canonical("СЕНИНЪ"), "сенинъ")
        // NFC: «й» and «ё» typed as a base letter plus a combining mark
        // (the IDS word list stores every «й» that way)
        XCTAssertEqual(Normalization.canonical("и\u{0306}ыл"), "йыл")
        XCTAssertEqual(Normalization.canonical("самоле\u{0308}т"), "самолёт")
        XCTAssertEqual(Array(Normalization.canonical("и\u{0306}ыл").unicodeScalars).count, 3)
        // Latin twins inside a Cyrillic word are repaired (а, о, е here)
        XCTAssertEqual(Normalization.canonical("бaр"), "бар")
        XCTAssertEqual(Normalization.canonical("бoлгaн"), "болган")
        XCTAssertEqual(Normalization.canonical("мeн"), "мен")
        // «аь» and «а», «э» and «е» are different Nogai letters and stay apart
        XCTAssertNotEqual(Normalization.canonical("аьр"), Normalization.canonical("ар"))
        XCTAssertNotEqual(Normalization.canonical("эл"), Normalization.canonical("ел"))
        // The two-character letters stay two characters: nothing is folded
        // into a single code point
        XCTAssertEqual(Array(Normalization.canonical("Аь").unicodeScalars).map(\.value), [0x0430, 0x044C])
        XCTAssertEqual(Array(Normalization.canonical("НЪ").unicodeScalars).map(\.value), [0x043D, 0x044A])
        for word in ["ногай", "сенинъ", "анълав", "оьзи", "уьш", "аьр", "ян-якка"] {
            XCTAssertTrue(Normalization.isCanonical(word), word)
            XCTAssertTrue(Normalization.isValidToken(word), word)
        }
    }

    /// The palochka convention of the Dagestanian keyboards is off: a Latin
    /// I, l or i next to Cyrillic letters is never turned into ӏ, and such
    /// a token is not a valid word.
    func testNoPalochkaRepair() {
        for lookalike in ["I", "l", "i", "1", "|"] {
            let canonical = Normalization.canonical("к" + lookalike + "ала")
            XCTAssertFalse(canonical.contains(where: Nogai.palochkas.contains), canonical)
        }
        XCTAssertEqual(Normalization.canonical("кIала"), "кiала")
        XCTAssertFalse(Normalization.isValidToken(Normalization.canonical("кIала")))
        XCTAssertFalse(Normalization.isValidToken(Normalization.canonical("кlала")))
    }

    /// «аь», «нъ», «оь», «уь» are one letter each for the engine, so a
    /// word needs two letters, not two characters, to be learned.
    func testLetterCountOfDigraphs() {
        for digraph in Nogai.digraphs {
            XCTAssertEqual(Normalization.letterCount(digraph), 1, digraph)
            XCTAssertFalse(Normalization.isValidToken(digraph), digraph)
        }
        // «нг» is not a Nogai letter: н and г, two letters («куьнге»)
        XCTAssertEqual(Normalization.letterCount("нг"), 2)
        XCTAssertEqual(Normalization.letterCount("сенинъ"), 5)   // с е н и нъ
        XCTAssertEqual(Normalization.letterCount("уьйкен"), 5)   // уь й к е н
        XCTAssertEqual(Normalization.letterCount("соьз"), 3)
        XCTAssertTrue(Normalization.isValidToken("уьй"))
        XCTAssertTrue(Normalization.isValidToken("аьр"))
        XCTAssertTrue(Normalization.isValidToken("онъ"))
    }

    // MARK: - Layout capabilities and strings

    func testLayoutCapabilities() {
        XCTAssertEqual(d.layout.styles.map(\.id.rawValue), ["standard"])
        XCTAssertEqual(d.layout.defaultStyle.rawValue, "standard")
        XCTAssertEqual(d.layout.persistenceKey, "layoutStyle")
        XCTAssertFalse(d.layout.showsSelector)
        XCTAssertFalse(d.layout.showsQuickSwitch)
        XCTAssertEqual(d.layout.gridModel, .nativeCells)
        XCTAssertEqual(d.layout.resolve(nil).rawValue, "standard")
        XCTAssertEqual(d.layout.resolve("classic").rawValue, "standard")
        XCTAssertEqual(d.layout.spec(for: .standard).bottomRowAfterSpace, [])
    }

    /// Nothing the user reads or types carries a palochka or a Latin letter
    /// posing as a Nogai one.
    func testUserFacingTextHasNoPalochka() {
        let s = d.strings
        var texts: [String] = [
            s.deleteWordQuestion("ногай"), s.no, s.delete, s.emojiRecents, s.back, s.close,
            s.settingsCaption, s.settingsTitle, s.pageInput, s.pageTheme, s.pageDictionary,
            s.pageAbout, s.sectionLayout, s.sectionSuggestions, s.sectionKeys, s.sectionLearning,
            s.sectionLongPress, s.sectionTheme, s.wordSuggestions, s.nextWordSuggestion,
            s.autoSpace, s.doubleSpacePeriod, s.spaceCursor, s.spaceCornerToggle,
            s.spaceCornerToggleSubtitle, s.learnFast, s.learnNormal, s.learnSlow, s.learnUses(3),
            s.calloutShort, s.calloutNormal, s.calloutLong, s.calloutDuration(0.3), s.themeSystem,
            s.themeLight, s.themeDark, s.learnedWordsCaption, s.noWordsYet, s.deleteAll,
            s.deleteAllQuestion, s.aboutInitial, s.aboutTitle, s.aboutByline("1.0.0"),
            d.keys.space, d.keys.spaceCornerLabel, d.keys.keyboardName, d.keys.lettersKey,
            d.keys.lettersKeyShifted, d.keys.emojiPageLettersKey,
        ]
        texts += d.keys.returnLabels.values
        texts += d.emojiCategoryTitles.values
        let spec = d.layout.spec(for: .standard)
        texts += [spec.settingsTitle, spec.settingsSubtitle]
        for (key, alternates) in spec.callouts { texts += [key] + alternates }
        for text in texts {
            XCTAssertFalse(text.contains(where: Nogai.palochkas.contains), "\(text) contains a palochka")
        }
        XCTAssertEqual(d.keys.keyboardName, "Ногай тили")
        XCTAssertEqual(d.keys.spaceCornerLabel, "НОГАЙ")
        XCTAssertTrue(Nogai.isPlainCyrillic(d.keys.keyboardName.replacingOccurrences(of: " ", with: "")))
    }

    func testRussianFallbackFormatting() {
        let s = d.strings
        XCTAssertEqual(s.learnUses(1), "1 раз")
        XCTAssertEqual(s.learnUses(3), "3 раза")
        XCTAssertEqual(s.learnUses(5), "5 раз")
        XCTAssertEqual(s.learnUses(12), "12 раз")
        XCTAssertEqual(s.learnUses(22), "22 раза")
        XCTAssertEqual(s.calloutDuration(0.2), "0,2 с")
        XCTAssertEqual(s.calloutDuration(0.45), "0,45 с")
        XCTAssertEqual(s.aboutByline("1.0.0"), "Версия 1.0.0 · LekiTech")
    }

    // MARK: - Project

    /// Two targets, no sticker or messenger targets; Debug signs with the
    /// developer's team under `.dev` identifiers, Release carries the App
    /// Store identifiers and no team (the distribution team adds its own).
    func testProjectTargetsAndSigning() throws {
        let pbx = try RepoPaths.text(RepoPaths.project)
        XCTAssertEqual(pbx.components(separatedBy: "isa = PBXNativeTarget;").count - 1, 2)
        XCTAssertEqual(pbx.components(separatedBy: "com.apple.product-type.application\"").count - 1, 1)
        XCTAssertEqual(pbx.components(separatedBy: "com.apple.product-type.app-extension\"").count - 1, 1)
        for banned in ["sticker", "Sticker", "messages", "telegram", "whatsapp", "instagram",
                       "Lezgi", "lezgi", "Avar", "avar", "Dargwa", "dargwa", "Kumyk", "kumyk", "vadivian"] {
            XCTAssertFalse(pbx.contains(banned), "project mentions \(banned)")
        }
        let bundleIDs = Set(pbx.matches(of: /PRODUCT_BUNDLE_IDENTIFIER = ([^;]+);/).map { String($0.1) })
        XCTAssertEqual(bundleIDs, [
            "org.lekitech.nogaikeyboard.dev", "org.lekitech.nogaikeyboard.dev.NogaiKeyboardExtension",
            "org.lekitech.nogaikeyboard", "org.lekitech.nogaikeyboard.NogaiKeyboardExtension",
        ])
        let groups = Set(pbx.matches(of: /NOGAI_APP_GROUP_ID = ([^;]+);/).map { String($0.1) })
        XCTAssertEqual(groups, [NogaiIdentity.debugAppGroupID, NogaiIdentity.releaseAppGroupID])
        let teams = pbx.matches(of: /\bDEVELOPMENT_TEAM = ([^;]+);/).map { String($0.1) }
        XCTAssertEqual(teams.sorted(), ["\"\"", "\"\"", "RC94H8KQYA", "RC94H8KQYA"])
        XCTAssertTrue(pbx.contains("relativePath = \"../../GeneralKeyboard-iOS\";"))

        for file in ["NogaiKeyboard/NogaiKeyboard/NogaiKeyboard.entitlements",
                     "NogaiKeyboard/NogaiKeyboardExtension/NogaiKeyboardExtension.entitlements"] {
            let plist = try RepoPaths.text(RepoPaths.root.appendingPathComponent(file))
            XCTAssertTrue(plist.contains("<string>$(NOGAI_APP_GROUP_ID)</string>"), file)
        }
        let info = try RepoPaths.text(RepoPaths.extensionFolder.appendingPathComponent("Info.plist"))
        XCTAssertTrue(info.contains("<key>PrimaryLanguage</key>\n\t\t\t<string>nog</string>"))
        XCTAssertTrue(info.contains("<key>RequestsOpenAccess</key>\n\t\t\t<false/>"))
    }
}
