import SwiftUI
import MimoCore

struct MemoriaView: View {
    @EnvironmentObject var memoryStore: MemoryStore
    @State private var parancoStatus = ParancoBridge.checkStatus()
    @State private var parancoOutput: String = ""
    @State private var isRunningLift: Bool = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header
                VStack(alignment: .leading, spacing: 6) {
                    Text("Memoria di Sistema & Rotte Paranco")
                        .font(.title2.bold())
                    Text("Paranco detiene l'accesso al disco protetto per convogliare le registrazioni vocali e le chat verso la pipeline locale.")
                        .foregroundStyle(.secondary)
                }

                // Card Stato Paranco
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Image(systemName: "lock.shield.fill")
                            .foregroundStyle(.blue)
                            .font(.title3)
                        Text("Stato Rotte Paranco")
                            .font(.headline)
                        Spacer()
                        if isRunningLift {
                            ProgressView()
                                .scaleEffect(0.7)
                        } else {
                            Button("Esegui Lift Adesso") {
                                Task {
                                    isRunningLift = true
                                    parancoOutput = (try? await ParancoBridge.runParancoLift()) ?? "Errore esecuzione"
                                    isRunningLift = false
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.small)
                        }
                    }

                    Divider()

                    HStack(spacing: 30) {
                        VStack(alignment: .leading) {
                            Text("Rotte configurate")
                                .font(.caption).foregroundStyle(.secondary)
                            Text("\(parancoStatus.routesCount)")
                                .font(.title3.bold())
                        }
                        VStack(alignment: .leading) {
                            Text("Rotte file")
                                .font(.caption).foregroundStyle(.secondary)
                            Text(parancoStatus.routesFileExists ? "routes.json presente" : "Non trovato")
                                .font(.subheadline)
                        }
                        VStack(alignment: .leading) {
                            Text("Binario paranco")
                                .font(.caption).foregroundStyle(.secondary)
                            Text(parancoStatus.binaryPath != nil ? "Disponibile" : "In attesa")
                                .font(.subheadline)
                        }
                    }

                    if !parancoStatus.routes.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Rotte attive:").font(.caption.bold())
                            ForEach(parancoStatus.routes) { r in
                                HStack {
                                    Circle().fill(r.enabled ? Color.green : Color.gray).frame(width: 6, height: 6)
                                    Text(r.name).font(.subheadline.bold())
                                    Text("[\(r.sourceID)] → \(r.destination.lastPathComponent)").font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                        .padding(.top, 4)
                    }

                    if !parancoOutput.isEmpty {
                        Text(parancoOutput)
                            .font(.system(.caption, design: .monospaced))
                            .padding(8)
                            .background(Color.black.opacity(0.1))
                            .cornerRadius(6)
                    }
                }
                .padding()
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(12)
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gray.opacity(0.2)))

                // Card Parlanti e Trascrizioni
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Identità Rilevate nella Memoria Locale")
                                .font(.headline)
                            Text("\(memoryStore.totalConversations) conversazioni analizzate da Scriba e inbox")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button {
                            Task {
                                await memoryStore.runExtraction()
                            }
                        } label: {
                            Label(memoryStore.isExtracting ? "Scansione..." : "Riscansiona Memoria", systemImage: "arrow.clockwise")
                        }
                        .disabled(memoryStore.isExtracting)
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }

                    Divider()

                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                        ForEach(memoryStore.speakers) { spk in
                            HStack(spacing: 12) {
                                ZStack {
                                    Circle()
                                        .fill(spk.name == "Eugenio" ? Color.blue.opacity(0.15) : (spk.name == "Alberto" ? Color.orange.opacity(0.15) : Color.gray.opacity(0.15)))
                                        .frame(width: 44, height: 44)
                                    Text(String(spk.name.prefix(1)))
                                        .font(.headline.bold())
                                        .foregroundStyle(spk.name == "Eugenio" ? Color.blue : (spk.name == "Alberto" ? Color.orange : Color.primary))
                                }

                                VStack(alignment: .leading, spacing: 2) {
                                    HStack {
                                        Text(spk.name)
                                            .font(.subheadline.bold())
                                        if spk.name == "Eugenio" {
                                            Text("TU")
                                                .font(.system(size: 9, weight: .bold))
                                                .padding(.horizontal, 4)
                                                .padding(.vertical, 1)
                                                .background(Color.blue)
                                                .foregroundColor(.white)
                                                .cornerRadius(4)
                                        }
                                    }
                                    Text("\(spk.words) parole • \(spk.turns) turni")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                            }
                            .padding(10)
                            .background(Color(nsColor: .windowBackgroundColor))
                            .cornerRadius(8)
                        }
                    }
                }
                .padding()
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(12)
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gray.opacity(0.2)))
            }
            .padding(24)
        }
    }
}
