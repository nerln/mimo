const WORKER_ENDPOINT = "https://mimo-session.eugenio-nerelli99.workers.dev";

// Parametri stanza dall'URL (es. ?room=stanza-nerln)
const urlParams = new URLSearchParams(window.location.search);
let currentRoom = urlParams.get("room") || "stanza-nerln";
let currentUsername = localStorage.getItem("mimo_username") || "Visitatore";

// Elementi DOM
const roomDisplay = document.getElementById("room-display");
const usernameInput = document.getElementById("username-input");
const roomInput = document.getElementById("room-input");
const btnSwitchRoom = document.getElementById("btn-switch-room");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const btnExport = document.getElementById("btn-export");
const btnAskClone = document.getElementById("btn-ask-clone");

// Stato messaggi
let messages = [];

function init() {
  roomDisplay.textContent = currentRoom;
  roomInput.value = currentRoom;
  usernameInput.value = currentUsername;

  loadRoomMessages();
  setupEventListeners();

  // Polling periodico per nuovi messaggi (ogni 3s)
  setInterval(fetchRemoteMessages, 3000);
}

function setupEventListeners() {
  usernameInput.addEventListener("change", (e) => {
    currentUsername = e.target.value.trim() || "Visitatore";
    localStorage.setItem("mimo_username", currentUsername);
  });

  btnSwitchRoom.addEventListener("click", () => {
    const newRoom = roomInput.value.trim() || "stanza-nerln";
    if (newRoom !== currentRoom) {
      currentRoom = newRoom;
      roomDisplay.textContent = currentRoom;
      const newUrl = `${window.location.pathname}?room=${encodeURIComponent(currentRoom)}`;
      window.history.pushState({ path: newUrl }, "", newUrl);
      loadRoomMessages();
    }
  });

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = messageInput.value.trim();
    if (!text) return;
    messageInput.value = "";
    sendMessage(text, currentUsername, "user");
  });

  btnExport.addEventListener("click", exportDataset);

  btnAskClone.addEventListener("click", () => {
    triggerCloneResponse();
  });
}

function getStorageKey() {
  return `mimo_chat_${currentRoom}`;
}

function loadRoomMessages() {
  chatMessages.innerHTML = "";
  const stored = localStorage.getItem(getStorageKey());
  if (stored) {
    try {
      messages = JSON.parse(stored);
      messages.forEach(renderMessage);
    } catch (e) {
      messages = [];
    }
  } else {
    messages = [];
    addSystemMessage(`Benvenuto nella stanza "${currentRoom}". Inizia la conversazione!`);
  }
}

function saveMessages() {
  localStorage.setItem(getStorageKey(), JSON.stringify(messages));
}

function renderMessage(msg) {
  const div = document.createElement("div");
  const isOwn = msg.author === currentUsername;
  const isClone = msg.type === "clone";

  div.className = `message ${isClone ? "clone" : (isOwn ? "own" : "other")}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.innerHTML = `
    <span class="message-author">${escapeHtml(msg.author)}</span>
    <span class="message-time">${new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
  `;

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = msg.text;

  div.appendChild(meta);
  div.appendChild(body);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addSystemMessage(text) {
  const div = document.createElement("div");
  div.className = "message system-message";
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendMessage(text, author, type = "user") {
  const msg = {
    id: Date.now() + "_" + Math.random().toString(36).substring(2, 7),
    room: currentRoom,
    author: author,
    text: text,
    type: type,
    timestamp: new Date().toISOString()
  };

  messages.push(msg);
  saveMessages();
  renderMessage(msg);

  // Spedisci a Cloudflare Worker se attivo
  postMessageToWorker(msg);
}

async function postMessageToWorker(msg) {
  try {
    await fetch(`${WORKER_ENDPOINT}/api/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg),
      mode: "cors"
    });
  } catch (err) {
    // Silenzioso: fallback su storage locale
  }
}

async function fetchRemoteMessages() {
  try {
    const res = await fetch(`${WORKER_ENDPOINT}/api/messages?room=${encodeURIComponent(currentRoom)}`);
    if (!res.ok) return;
    const remote = await res.json();
    if (Array.isArray(remote) && remote.length > 0) {
      let added = false;
      const existingIds = new Set(messages.map(m => m.id));
      for (const m of remote) {
        if (!existingIds.has(m.id)) {
          messages.push(m);
          renderMessage(m);
          added = true;
        }
      }
      if (added) saveMessages();
    }
  } catch (err) {
    // Nessun server remoto: la chat funziona in locale
  }
}

function triggerCloneResponse() {
  if (messages.length === 0) {
    addSystemMessage("Scrivi prima qualcosa affinché il clone possa intervenire.");
    return;
  }

  // Risposte caratteristiche nello stile di Eugenio addestrato
  const cloneReplies = [
    "Ma guarda che il problema non è il training in sé, è che se usi roba a caso ti ritrovi un modello che ripete sciocchezze. Su Apple Silicon gira in 15 secondi.",
    "Boh, secondo me state complicando la cosa: metti i turni in un jsonl, lancia lo script MPS e guarda scendere la loss.",
    "Piuttosto controlla se Paranco ha liftato la cartella giusta in ~/.scriba/inbox, altrimenti siamo qua a parlare del nulla.",
    "Sì ma chi se ne frega della crittografia se poi l'utente esporta lo zip delle chat a mano e lo dà in pasto a qualsiasi script Python?"
  ];

  const randomReply = cloneReplies[Math.floor(Math.random() * cloneReplies.length)];
  setTimeout(() => {
    sendMessage(randomReply, "Eugenio (Clone)", "clone");
  }, 600);
}

function exportDataset() {
  if (messages.length < 2) {
    alert("Servono almeno 2 messaggi nella stanza per creare un dataset di fine-tuning.");
    return;
  }

  // Converti i messaggi della stanza in formato fine-tuning
  const trainingLines = [];
  for (let i = 1; i < messages.length; i++) {
    const prev = messages[i - 1];
    const curr = messages[i];
    const sample = {
      messages: [
        { role: "system", content: "Sei un interlocutore che partecipa a una conversazione informale in italiano." },
        { role: "user", content: `[${prev.author}]: ${prev.text}` },
        { role: "assistant", content: curr.text }
      ]
    };
    trainingLines.push(JSON.stringify(sample));
  }

  const blob = new Blob([trainingLines.join("\n")], { type: "application/jsonlines" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `dataset_${currentRoom}_${new Date().toISOString().slice(0, 10)}.jsonl`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

window.addEventListener("DOMContentLoaded", init);
