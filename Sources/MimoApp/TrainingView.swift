import SwiftUI
import MimoCore

struct TrainingView: View {
    @EnvironmentObject var memoryStore: MemoryStore
    @EnvironmentObject var ollamaClient: OllamaClient
    @EnvironmentObject var runner: TrainingRunner

    @State private var selectedSpeaker: String = "Eugenio"
    @State private var selectedBaseModel: String = "qwen3:4b-instruct-2507-q4_K_M"
    @State private var epochs: Int = 5

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header
                VStack(alignment: .leading, spacing: 4) {
                    Text("Fine-Tuning Locale su Apple Silicon")
                        .font(.title2.bold())
                    Text("Allena un modello LLM sui turni di parola reali per riprodurre lo stile, il tono e il lessico della persona scelta.")
                        .foregroundStyle(.secondary)
                }

                // Configurazione Parametri
                VStack(alignment: .leading, spacing: 14) {
                    Text("Configurazione Addestramento")
                        .font(.headline)

                    Divider()

                    HStack(spacing: 24) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Parlante da Clonare").font(.caption.bold())
                            Picker("Parlante", selection: $selectedSpeaker) {
                                ForEach(memoryStore.speakers) { spk in
                                    Text(spk.name).tag(spk.name)
                                }
                            }
                            .labelsHidden()
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            Text("Modello Base (Ollama)").font(.caption.bold())
                            Picker("Base", selection: $selectedBaseModel) {
                                Text("Qwen3 4B Instruct (q4_K_M)").tag("qwen3:4b-instruct-2507-q4_K_M")
                                Text("Qwen3 8B").tag("qwen3:8b")
                                Text("Olivera Q4").tag("olivera:q4")
                            }
                            .labelsHidden()
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            Text("Epoche").font(.caption.bold())
                            Stepper("\(epochs)", value: $epochs, in: 1...20)
                        }

                        Spacer()

                        Button {
                            Task {
                                await runner.startTraining(speaker: selectedSpeaker, epochs: epochs, baseModel: selectedBaseModel)
                                await ollamaClient.checkConnection()
                            }
                        } label: {
                            HStack {
                                if runner.isTraining {
                                    ProgressView().scaleEffect(0.8)
                                    Text("Addestramento in corso...")
                                } else {
                                    Image(systemName: "bolt.fill")
                                    Text("Avvia Fine-Tuning")
                                }
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(runner.isTraining)
                    }
                }
                .padding()
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(12)
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gray.opacity(0.2)))

                // Stato e Metriche
                if runner.latestLoss != nil || runner.isTraining || !runner.logs.isEmpty {
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text("Avanzamento & Metriche di Convergenza")
                                .font(.headline)
                            Spacer()
                            if let loss = runner.latestLoss {
                                HStack(spacing: 8) {
                                    Text("Loss:")
                                        .font(.caption).foregroundStyle(.secondary)
                                    Text(String(format: "%.4f", loss))
                                        .font(.subheadline.bold())
                                        .foregroundStyle(.green)
                                }
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(Color.green.opacity(0.1))
                                .cornerRadius(6)
                            }
                        }

                        Divider()

                        // Terminale di log
                        ScrollViewReader { proxy in
                            ScrollView {
                                VStack(alignment: .leading, spacing: 4) {
                                    ForEach(Array(runner.logs.enumerated()), id: \.offset) { idx, line in
                                        Text(line)
                                            .font(.system(size: 11, design: .monospaced))
                                            .foregroundStyle(line.contains("Loss") ? .green : (line.contains("==>") ? .blue : .primary))
                                            .id(idx)
                                    }
                                }
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(10)
                            }
                            .frame(height: 220)
                            .background(Color.black.opacity(0.85))
                            .cornerRadius(8)
                            .onChange(of: runner.logs.count) { _, newCount in
                                proxy.scrollTo(newCount - 1, anchor: .bottom)
                            }
                        }
                    }
                    .padding()
                    .background(Color(nsColor: .controlBackgroundColor))
                    .cornerRadius(12)
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gray.opacity(0.2)))
                }
            }
            .padding(24)
        }
    }
}
