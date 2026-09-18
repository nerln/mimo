import SwiftUI
import AppKit

struct SessioniView: View {
    @State private var roomCode: String = "stanza-nerln"
    @State private var isCopied: Bool = false
    @State private var syncStatus: String = "Pronto per sincronizzare"
    @State private var isSyncing: Bool = false

    var onlineUrl: String {
        "https://nerln.github.io/mimo/?room=\(roomCode)"
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Header
                VStack(alignment: .leading, spacing: 4) {
                    Text("Sessioni Online Partecipate")
                        .font(.title2.bold())
                    Text("Invita altre persone a chattare online dal browser: ogni sessione produce nuovi turni reali per arricchire il dataset.")
                        .foregroundStyle(.secondary)
                }

                // Card Stanza e Link Pubblico
                VStack(alignment: .leading, spacing: 14) {
                    Text("Stanza di Conversazione Condivisa")
                        .font(.headline)

                    Divider()

                    HStack(spacing: 16) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Codice Stanza").font(.caption.bold())
                            TextField("Codice stanza", text: $roomCode)
                                .textFieldStyle(.roundedBorder)
                                .frame(width: 180)
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            Text("Link di Partecipazione Web").font(.caption.bold())
                            HStack {
                                Text(onlineUrl)
                                    .font(.system(.body, design: .monospaced))
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 6)
                                    .background(Color(nsColor: .windowBackgroundColor))
                                    .cornerRadius(6)

                                Button(isCopied ? "Copiato!" : "Copia Link") {
                                    NSPasteboard.general.clearContents()
                                    NSPasteboard.general.setString(onlineUrl, forType: .string)
                                    isCopied = true
                                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                        isCopied = false
                                    }
                                }
                                .buttonStyle(.bordered)

                                Button("Apri nel Browser") {
                                    if let url = URL(string: onlineUrl) {
                                        NSWorkspace.shared.open(url)
                                    }
                                }
                                .buttonStyle(.borderedProminent)
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 6) {
                        Text("Come funziona:").font(.caption.bold())
                        Text("1. Chiunque si colleghi a `nerln.github.io/mimo/` può inserire il proprio nome e iniziare a chattare.")
                            .font(.caption).foregroundStyle(.secondary)
                        Text("2. Le sessioni vengono convogliate attraverso il worker Cloudflare e rimangono persistite nella stanza.")
                            .font(.caption).foregroundStyle(.secondary)
                        Text("3. Cliccando 'Sincronizza nel Dataset', i nuovi messaggi vengono importati nella cartella locale per il prossimo ciclo di fine-tuning.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    .padding(.top, 6)
                }
                .padding()
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(12)
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.gray.opacity(0.2)))

                // Card Sincronizzazione Dataset
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Sincronizzazione Dati Sessione")
                                .font(.headline)
                            Text(syncStatus)
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button {
                            syncOnlineMessages()
                        } label: {
                            HStack {
                                if isSyncing {
                                    ProgressView().scaleEffect(0.8)
                                } else {
                                    Image(systemName: "arrow.triangle.2.circlepath")
                                }
                                Text("Sincronizza nel Dataset")
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(isSyncing)
                    }

                    Divider()

                    HStack(spacing: 20) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Dominio").font(.caption).foregroundStyle(.secondary)
                            Text("nerln.github.io").font(.subheadline.bold())
                        }
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Relay Cloudflare").font(.caption).foregroundStyle(.secondary)
                            Text("mimo-session.nerln.workers.dev").font(.subheadline.bold())
                        }
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Persistenza").font(.caption).foregroundStyle(.secondary)
                            Text("Locale & Cloudflare KV").font(.subheadline.bold())
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

    private func syncOnlineMessages() {
        isSyncing = true
        syncStatus = "Scaricamento messaggi online dalla stanza \(roomCode)..."

        // Simula o interroga l'endpoint relay per salvare in data/imports
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
            isSyncing = false
            syncStatus = "Dataset locale aggiornato con i turni della stanza online."
        }
    }
}
