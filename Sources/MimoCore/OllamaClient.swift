import Foundation

public struct OllamaModel: Identifiable, Sendable {
    public var id: String { name }
    public let name: String
    public let size: Int64
    public let modifiedAt: String
}

public struct ChatMessage: Identifiable, Sendable, Codable {
    public let id: UUID
    public let role: String
    public let content: String
    public let timestamp: Date

    public init(id: UUID = UUID(), role: String, content: String, timestamp: Date = Date()) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
    }
}

public final class OllamaClient: ObservableObject, @unchecked Sendable {
    @Published public var availableModels: [OllamaModel] = []
    @Published public var isConnected: Bool = false
    @Published public var isGenerating: Bool = false

    private let endpoint: URL

    public init(endpoint: URL = URL(string: "http://localhost:11434")!) {
        self.endpoint = endpoint
    }

    public func checkConnection() async {
        let tagsUrl = endpoint.appendingPathComponent("api/tags")
        do {
            let (data, response) = try await URLSession.shared.data(from: tagsUrl)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                await MainActor.run { isConnected = false }
                return
            }

            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let modelsArr = json["models"] as? [[String: Any]] {
                let parsed = modelsArr.compactMap { dict -> OllamaModel? in
                    guard let name = dict["name"] as? String else { return nil }
                    let size = dict["size"] as? Int64 ?? 0
                    let mod = dict["modified_at"] as? String ?? ""
                    return OllamaModel(name: name, size: size, modifiedAt: mod)
                }
                await MainActor.run {
                    self.availableModels = parsed
                    self.isConnected = true
                }
            }
        } catch {
            await MainActor.run { isConnected = false }
        }
    }

    public func sendMessage(model: String, messages: [ChatMessage]) async throws -> String {
        await MainActor.run { isGenerating = true }
        defer {
            Task { @MainActor in self.isGenerating = false }
        }

        let chatUrl = endpoint.appendingPathComponent("api/chat")
        var req = URLRequest(url: chatUrl)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let bodyMessages = messages.map { ["role": $0.role, "content": $0.content] }
        let payload: [String: Any] = [
            "model": model,
            "messages": bodyMessages,
            "stream": false
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            let errText = String(data: data, encoding: .utf8) ?? "Errore HTTP"
            throw NSError(domain: "OllamaClient", code: (response as? HTTPURLResponse)?.statusCode ?? 500, userInfo: [NSLocalizedDescriptionKey: errText])
        }

        if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
           let msg = json["message"] as? [String: Any],
           let content = msg["content"] as? String {
            return content.trimmingCharacters(in: .whitespacesAndNewlines)
        }

        throw NSError(domain: "OllamaClient", code: -1, userInfo: [NSLocalizedDescriptionKey: "Formato risposta Ollama non valido"])
    }
}
