import SwiftUI
import MimoCore

@main
struct MimoApp: App {
    @StateObject private var memoryStore = MemoryStore()
    @StateObject private var ollamaClient = OllamaClient()
    @StateObject private var trainingRunner = TrainingRunner()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(memoryStore)
                .environmentObject(ollamaClient)
                .environmentObject(trainingRunner)
                .frame(minWidth: 880, minHeight: 620)
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
    }
}
