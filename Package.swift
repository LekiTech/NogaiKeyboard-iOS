// swift-tools-version: 6.0
//
//  Test-only package for the Nogai keyboard's product layer.
//
//  The keyboard engine lives in the General Keyboard package
//  (../GeneralKeyboard-iOS) and is tested there. This package tests what
//  Nogai adds on top: `NogaiCore` compiles the very same product files
//  that ship inside the NogaiKeyboardExtension target (the definition,
//  layout, strings and identity), via an explicit `sources:` list, and the
//  tests run them through the real engine: the definition, the layout
//  against the pinned Russian baseline and Nogai long-press mapping, the
//  shipped dictionary artifacts,
//  learning and the typing path.
//
//  Run from the repo root (General Keyboard checked out next to this repo):
//    xcodebuild test -scheme NogaiCoreTests-Package \
//      -destination 'platform=iOS Simulator,name=iPhone 18 Pro,OS=27.0'
//
//  iOS-only by design: the layout and the engine use UIKit types.
//
import PackageDescription

let package = Package(
    name: "NogaiCoreTests",
    platforms: [.iOS(.v18)],
    dependencies: [
        .package(path: "../GeneralKeyboard-iOS"),
    ],
    targets: [
        .target(
            name: "NogaiCore",
            dependencies: [.product(name: "GeneralKeyboard", package: "GeneralKeyboard-iOS")],
            path: "NogaiKeyboard/NogaiKeyboardExtension",
            sources: [
                "NogaiDefinition.swift",
                "NogaiLayout.swift",
                "NogaiStrings.swift",
                "NogaiIdentity.swift",
            ]
        ),
        .testTarget(
            name: "NogaiCoreTests",
            dependencies: ["NogaiCore", .product(name: "GeneralKeyboard", package: "GeneralKeyboard-iOS")],
            path: "Tests/NogaiCoreTests",
            // Read through #filePath (like the shipped artifacts), not bundled.
            exclude: ["Fixtures"]
        ),
    ]
)
