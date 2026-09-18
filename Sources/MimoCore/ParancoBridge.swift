import Foundation

public struct ParancoRoute: Identifiable, Codable, Sendable {
    public var id: UUID
    public var name: String
    public var sourceID: String
    public var destination: URL
    public var extensions: [String]
    public var enabled: Bool
}

public struct ParancoStatus: Sendable {
    public let routesFileExists: Bool
    public let routesCount: Int
    public let routes: [ParancoRoute]
    public let binaryPath: String?
}

public enum ParancoBridge {
    public static var routesFile: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/paranco/routes.json")
    }

    public static func checkStatus() -> ParancoStatus {
        let exists = FileManager.default.fileExists(atPath: routesFile.path)
        var routes: [ParancoRoute] = []
        if exists {
            if let data = try? Data(contentsOf: routesFile) {
                let decoder = JSONDecoder()
                if let decoded = try? decoder.decode([ParancoRoute].self, from: data) {
                    routes = decoded
                }
            }
        }

        // Cerca il binario paranco
        var binary: String? = nil
        let candidatePaths = [
            "/Users/eugenionerelli/dev/paranco/.build/debug/paranco",
            "/Users/eugenionerelli/dev/paranco/.build/release/paranco",
            "/usr/local/bin/paranco"
        ]
        for p in candidatePaths {
            if FileManager.default.isExecutableFile(atPath: p) {
                binary = p
                break
            }
        }

        return ParancoStatus(
            routesFileExists: exists,
            routesCount: routes.count,
            routes: routes,
            binaryPath: binary
        )
    }

    public static func runParancoLift() async throws -> String {
        guard let binary = checkStatus().binaryPath else {
            return "Binario paranco non trovato. Le rotte sono comunque attive su disco."
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: binary)
        process.arguments = ["lift"]
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        try process.run()
        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        return String(data: data, encoding: .utf8) ?? ""
    }
}
