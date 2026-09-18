import SwiftUI
import MimoCore

enum NavigationTab: String, CaseIterable, Identifiable {
    case memoria = "Memoria & Paranco"
    case training = "Fine-Tuning Locale"
    case chat = "Chat col Clone"
    case sessioni = "Sessioni Online"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .memoria: return "externaldrive.fill.badge.checkmark"
        case .training: return "waveform.path.badge.plus"
        case .chat: return "bubble.left.and.bubble.right.fill"
        case .sessioni: return "globe.europe.africa.fill"
        }
    }
}

struct ContentView: View {
    @State private var selectedTab: NavigationTab = .memoria
    @EnvironmentObject var memoryStore: MemoryStore
    @EnvironmentObject var ollamaClient: OllamaClient

    var body: some View {
        NavigationSplitView {
            List(NavigationTab.allCases, selection: $selectedTab) { tab in
                NavigationLink(value: tab) {
                    Label(tab.rawValue, systemImage: tab.icon)
                        .padding(.vertical, 4)
                }
            }
            .listStyle(.sidebar)
            .navigationTitle("Mimo")
            .toolbar {
                ToolbarItem(placement: .status) {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(ollamaClient.isConnected ? Color.green : Color.orange)
                            .frame(width: 8, height: 8)
                        Text(ollamaClient.isConnected ? "Ollama attivo" : "Ollama offline")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        } detail: {
            switch selectedTab {
            case .memoria:
                MemoriaView()
            case .training:
                TrainingView()
            case .chat:
                ChatView()
            case .sessioni:
                SessioniView()
            }
        }
        .task {
            await ollamaClient.checkConnection()
        }
    }
}
