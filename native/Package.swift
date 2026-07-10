// swift-tools-version:6.4
import PackageDescription

let package = Package(
    name: "lantern-native-describe",
    platforms: [.macOS(.v27)],
    targets: [
        .executableTarget(name: "lantern-native-describe")
    ]
)
