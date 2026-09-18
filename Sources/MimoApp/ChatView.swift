import SwiftUI
import MimoCore

struct ChatView: View {
    @EnvironmentObject var ollamaClient: OllamaClient
    @State private var selectedModel: String = "eugenio-clone"
    @State private var messages: [ChatMessage] = []
    @State private var inputText: String = ""

    var body: some View {
        VStack(spacing: 0) {
            // Barra superiore con selezione modello
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Interlocutore Clone")
                        .font(.headline)
                    Text(selectedModel.contains("eugenio") ? "Replica di Eugenio Nerelli" : (selectedModel.contains("alberto") ? "Replica di Alberto Robazza" : "Modello locale"))
                        .font(.caption).foregroundStyle(.secondary)
                }

                Spacer()

                Picker("Modello", selection: $selectedModel) {
                    if ollamaClient.availableModels.isEmpty {
                        Text("eugenio-clone").tag("eugenio-clone")
                        Text("alberto-clone").tag("alberto-clone")
                    } else {
                        ForEach(ollamaClient.availableModels) { m in
                            Text(m.name).tag(m.name)
                        }
                    }
                }
                .frame(width: 220)

                Button {
                    messages.removeAll()
                } label: {
                    Image(systemName: "trash")
                }
                .help("Cancella cronologia chat")
                .buttonStyle(.plain)
                .padding(.leading, 8)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 14)
            .background(Color(nsColor: .controlBackgroundColor))
            .overlay(Divider(), alignment: .bottom)

            // Feed messaggi
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        if messages.isEmpty {
                            VStack(spacing: 12) {
                                Image(systemName: "person.crop.circle.badge.checkmark")
                                    .font(.system(size: 44))
                                    .foregroundStyle(.blue)
                                Text("Inizia a conversare con il clone locale")
                                    .font(.headline)
                                Text("Il modello è stato addestrato sui turni di parola della persona selezionata.")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)

                                // Suggerimenti di inizio
                                HStack(spacing: 8) {
                                    SuggestionButton(text: "Cosa ne pensi di WhatsApp?") { send(prompt: $0) }
                                    SuggestionButton(text: "Come va il progetto?") { send(prompt: $0) }
                                    SuggestionButton(text: "Spiegami come funziona Paranco.") { send(prompt: $0) }
                                }
                                .padding(.top, 10)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.top, 80)
                        }

                        ForEach(messages) { msg in
                            ChatBubble(message: msg)
                                .id(msg.id)
                        }

                        if ollamaClient.isGenerating {
                            HStack {
                                ProgressView()
                                    .scaleEffect(0.7)
                                Text("Il clone sta scrivendo...")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Spacer()
                            }
                            .padding(.horizontal, 20)
                        }
                    }
                    .padding(20)
                }
                .onChange(of: messages.count) { _, _ in
                    if let last = messages.last {
                        withAnimation {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }

            // Barra di inserimento
            HStack(spacing: 10) {
                TextField("Scrivi un messaggio...", text: $inputText)
                    .textFieldStyle(.plain)
                    .padding(10)
                    .background(Color(nsColor: .controlBackgroundColor))
                    .cornerRadius(8)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.gray.opacity(0.3)))
                    .onSubmit {
                        submit()
                    }

                Button {
                    submit()
                } label: {
                    Image(systemName: "paperplane.fill")
                        .font(.system(size: 14))
                        .foregroundColor(.white)
                        .padding(8)
                        .background(inputText.trimmingCharacters(in: .whitespaces).isEmpty ? Color.gray : Color.blue)
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .disabled(inputText.trimmingCharacters(in: .whitespaces).isEmpty || ollamaClient.isGenerating)
            }
            .padding(16)
            .background(Color(nsColor: .windowBackgroundColor))
            .overlay(Divider(), alignment: .top)
        }
    }

    private func submit() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        inputText = ""
        send(prompt: text)
    }

    private func send(prompt: String) {
        let userMsg = ChatMessage(role: "user", content: prompt)
        messages.append(userMsg)

        Task {
            do {
                let reply = try await ollamaClient.sendMessage(model: selectedModel, messages: messages)
                await MainActor.run {
                    messages.append(ChatMessage(role: "assistant", content: reply))
                }
            } catch {
                await MainActor.run {
                    messages.append(ChatMessage(role: "assistant", content: "Errore inferenza: \(error.localizedDescription)"))
                }
            }
        }
    }
}

struct SuggestionButton: View {
    let text: String
    let action: (String) -> Void

    var body: some View {
        Button {
            action(text)
        } label: {
            Text(text)
                .font(.caption)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color(nsColor: .controlBackgroundColor))
                .cornerRadius(16)
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.gray.opacity(0.3)))
        }
        .buttonStyle(.plain)
    }
}

struct ChatBubble: View {
    let message: ChatMessage

    var isUser: Bool { message.role == "user" }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 50) }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .font(.body)
                    .foregroundStyle(isUser ? Color.white : Color.primary)
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .background(isUser ? Color.blue : Color(nsColor: .controlBackgroundColor))
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(isUser ? Color.clear : Color.gray.opacity(0.2))
                    )

                Text(message.timestamp.formatted(date: .omitted, time: .shortened))
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 4)
            }

            if !isUser { Spacer(minLength: 50) }
        }
    }
}
