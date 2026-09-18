import Foundation

public struct SpeakerSummary: Identifiable, Sendable, Codable {
    public var id: String { name }
    public let name: String
    public let turns: Int
    public let words: Int
    public let jobs: Int
    public let datasetPath: String?
}

public struct ConversationSample: Identifiable, Sendable {
    public let id = UUID()
    public let user: String
    public let assistant: String
}

public final class MemoryStore: ObservableObject, @unchecked Sendable {
    @Published public var speakers: [SpeakerSummary] = []
    @Published public var totalConversations: Int = 0
    @Published public var isExtracting: Bool = false
    @Published public var lastExtractedDate: Date? = nil

    private let dataDir: URL

    public init(baseDir: URL = URL(fileURLWithPath: "/Users/eugenionerelli/dev/mimo")) {
        self.dataDir = baseDir.appendingPathComponent("data")
        reload()
    }

    public func reload() {
        let summaryFile = dataDir.appendingPathComponent("summary.json")
        guard FileManager.default.fileExists(atPath: summaryFile.path),
              let data = try? Data(contentsOf: summaryFile),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }

        let stats = json["stats"] as? [String: Any] ?? [:]
        self.totalConversations = stats["total_conversations"] as? Int ?? 0

        let speakersDict = stats["speakers"] as? [String: [String: Any]] ?? [:]
        let generated = json["generated_datasets"] as? [String: [String: Any]] ?? [:]

        var list: [SpeakerSummary] = []
        for (spk, info) in speakersDict {
            let turns = info["turns"] as? Int ?? 0
            let words = info["words"] as? Int ?? 0
            let jobs = info["jobs"] as? Int ?? 0
            let path = generated[spk]?["file"] as? String
            list.append(SpeakerSummary(name: spk, turns: turns, words: words, jobs: jobs, datasetPath: path))
        }

        // Ordina mettendo Eugenio e Alberto in cima, poi per numero di parole
        self.speakers = list.sorted { a, b in
            if a.name == "Eugenio" { return true }
            if b.name == "Eugenio" { return false }
            if a.name == "Alberto" { return true }
            if b.name == "Alberto" { return false }
            return a.words > b.words
        }
    }

    public func runExtraction() async {
        await MainActor.run { isExtracting = true }
        let script = dataDir.deletingLastPathComponent().appendingPathComponent("engine/extract_turns.py")
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/opt/homebrew/Caskroom/miniforge/base/bin/python3")
        process.arguments = [script.path]

        try? process.run()
        process.waitUntilExit()

        await MainActor.run {
            self.reload()
            self.isExtracting = false
            self.lastExtractedDate = Date()
        }
    }

    public func importWhatsAppChat(url: URL) async {
        await MainActor.run { isExtracting = true }
        let importsDir = dataDir.appendingPathComponent("imports")
        try? FileManager.default.createDirectory(at: importsDir, withIntermediateDirectories: true)
        let targetFile = importsDir.appendingPathComponent(url.lastPathComponent)
        try? FileManager.default.removeItem(at: targetFile)
        try? FileManager.default.copyItem(at: url, to: targetFile)

        await runExtraction()
    }
}
