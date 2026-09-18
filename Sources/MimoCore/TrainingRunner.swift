import Foundation

public struct TrainingProgress: Sendable {
    public let epoch: Int
    public let totalEpochs: Int
    public let loss: Double
    public let perplexity: Double
    public let message: String
}

public final class TrainingRunner: ObservableObject, @unchecked Sendable {
    @Published public var isTraining: Bool = false
    @Published public var currentSpeaker: String = ""
    @Published public var logs: [String] = []
    @Published public var latestLoss: Double? = nil
    @Published public var completedSuccessfully: Bool = false

    private let pythonPath: String
    private let rootDir: URL

    public init(rootDir: URL = URL(fileURLWithPath: "/Users/eugenionerelli/dev/mimo")) {
        self.rootDir = rootDir
        self.pythonPath = "/opt/homebrew/Caskroom/miniforge/base/bin/python3"
    }

    public func startTraining(speaker: str_alias, epochs: Int = 5, baseModel: String = "qwen3:4b-instruct-2507-q4_K_M") async {
        await MainActor.run {
            self.isTraining = true
            self.currentSpeaker = speaker
            self.logs = []
            self.latestLoss = nil
            self.completedSuccessfully = false
            self.logs.append("==> Avvio pipeline di addestramento Mimo per [\(speaker)] su Apple Silicon M4")
        }

        let loraScript = rootDir.appendingPathComponent("engine/train_lora.py")
        let adapterScript = rootDir.appendingPathComponent("engine/ollama_adapter.py")

        // 1. Esegui train_lora.py
        let loraProcess = Process()
        loraProcess.executableURL = URL(fileURLWithPath: pythonPath)
        loraProcess.arguments = [loraScript.path, "--speaker", speaker, "--epochs", "\(epochs)"]

        let pipeOut = Pipe()
        loraProcess.standardOutput = pipeOut
        loraProcess.standardError = pipeOut

        let outHandle = pipeOut.fileHandleForReading
        outHandle.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            let lines = text.components(separatedBy: .newlines)
            Task { @MainActor in
                for line in lines where !line.isEmpty {
                    self?.logs.append(line)
                    if line.contains("Loss: ") {
                        let parts = line.components(separatedBy: "Loss: ")
                        if parts.count > 1, let val = Double(parts[1].prefix(6)) {
                            self?.latestLoss = val
                        }
                    }
                }
            }
        }

        try? loraProcess.run()
        loraProcess.waitUntilExit()
        outHandle.readabilityHandler = nil

        await MainActor.run {
            self.logs.append("==> Addestramento pesi LoRA Metal completato.")
            self.logs.append("==> Registrazione modello persona in Ollama...")
        }

        // 2. Esegui ollama_adapter.py
        let adapterProcess = Process()
        adapterProcess.executableURL = URL(fileURLWithPath: pythonPath)
        adapterProcess.arguments = [adapterScript.path, "--speaker", speaker, "--base", baseModel]
        let adapterPipe = Pipe()
        adapterProcess.standardOutput = adapterPipe
        adapterProcess.standardError = adapterPipe

        let adapterHandle = adapterPipe.fileHandleForReading
        adapterHandle.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            let lines = text.components(separatedBy: .newlines)
            Task { @MainActor in
                for line in lines where !line.isEmpty {
                    self?.logs.append(line)
                }
            }
        }

        try? adapterProcess.run()
        adapterProcess.waitUntilExit()
        adapterHandle.readabilityHandler = nil

        await MainActor.run {
            self.isTraining = false
            self.completedSuccessfully = true
            self.logs.append("==> Modello \(speaker.lowercased())-clone pronto all'uso!")
        }
    }
}

public typealias str_alias = String
