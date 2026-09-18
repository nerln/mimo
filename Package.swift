// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Mimo",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "MimoCore", targets: ["MimoCore"]),
        .executable(name: "MimoApp", targets: ["MimoApp"])
    ],
    dependencies: [],
    targets: [
        .target(
            name: "MimoCore",
            dependencies: [],
            path: "Sources/MimoCore"
        ),
        .executableTarget(
            name: "MimoApp",
            dependencies: ["MimoCore"],
            path: "Sources/MimoApp"
        )
    ]
)
