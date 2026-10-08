// Frontend elements
const apiBaseUrl = "";
const form = document.getElementById("chat-form");
const input = document.getElementById("input");
const output = document.getElementById("output");
const sendButton = document.getElementById("send");
const clearButton = document.getElementById("clear");
const suggestions = document.getElementById("suggestions");

// Genres are used to randomize the "Give me a game idea" button
const genres = [
  "horror", "puzzle", "simulation", "adventure", "cozy", "stealth", "strategy",
  "platformer", "survival", "roguelite", "narrative", "management", "rhythm",
  "mystery", "farming", "shooter", "deckbuilder", "arcade", "racing", "action",
  "fighting", "builder", "sports", "educational", "tower defense", "sandbox",
  "metroidvania", "roguelike", "party", "visual novel", "looter",
  "trading card", "looter-shooter", "multiplayer", "moba",
];

// Message sent to the server instead of the visible text
let hiddenMessage = null;
const sessionId = (() => {
  const existing = localStorage.getItem("game-chat-session-id");
  if (existing) return existing;

  const generated = typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

  localStorage.setItem("game-chat-session-id", generated);
  return generated;
})();

// Function to request the server to close the session
function requestShutdown() {
  const payload = JSON.stringify({ session_id: sessionId });
  if (navigator.sendBeacon) {
    const blob = new Blob([payload], { type: "application/json" });
    navigator.sendBeacon(`${apiBaseUrl}/api/close`, blob);
    return;
  }

  fetch(`${apiBaseUrl}/api/close`, {
    headers: { "Content-Type": "application/json" },
    method: "POST",
    body: payload,
    keepalive: true,
  }).catch(() => {});
}

// Add click event listeners to suggestion buttons
for (const button of suggestions.querySelectorAll(".suggestion")) {
  button.addEventListener("click", () => {
    const genre = genres[Math.floor(Math.random() * genres.length)];
    input.value = button.textContent;
    hiddenMessage = `Give me a ${genre} game idea`;
    form.requestSubmit();
  });
}

// Elements for displaying the game idea
const ideaElements = {
  genre: document.getElementById("idea-genre"),
  setting: document.getElementById("idea-setting"),
  theme: document.getElementById("idea-theme"),
  coreMechanics: document.getElementById("idea-mechanics"),
};

// Function to update the idea boxes with the game idea
function setIdeaBoxes(idea) {
  if (!idea) {
    ideaElements.genre.textContent = "";
    ideaElements.setting.textContent = "";
    ideaElements.theme.textContent = "";
    ideaElements.coreMechanics.innerHTML = "";
    return;
  }

  const mechanics = Array.isArray(idea.core_mechanics)
    ? idea.core_mechanics
    : Array.isArray(idea.coreMechanics)
      ? idea.coreMechanics
      : [];

  ideaElements.genre.textContent = idea.genre || "";
  ideaElements.setting.textContent = idea.setting || "";
  ideaElements.theme.textContent = idea.theme || "";
  ideaElements.coreMechanics.innerHTML = "";

  for (const mechanic of mechanics) {
    const listItem = document.createElement("li");
    listItem.textContent = `• ${mechanic}`;
    ideaElements.coreMechanics.appendChild(listItem);
  }
}

// Function to add a message to the chat output
function addMessage(text, role) {
  suggestions.classList.add("hidden");
  const div = document.createElement("div");
  const color = role === "user" ? "bg-blue-100 self-end" : "bg-gray-200 self-start";
  div.className = `my-1.5 max-w-[80%] whitespace-pre-wrap rounded-md px-3 py-2 ${color}`;
  div.textContent = text;
  output.appendChild(div);
  output.scrollTop = output.scrollHeight;
  return div;
}

// Handle form submission
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  const toSend = hiddenMessage || text;
  hiddenMessage = null;

  addMessage(text, "user");
  input.value = "";
  sendButton.disabled = true;
  clearButton.disabled = true;
  const pending = addMessage("Thinking...", "bot");

  // Send the message to the server and handle the response
  try {
    const response = await fetch(`${apiBaseUrl}/api/chat`, {
      headers: { "Content-Type": "application/json" },
      method: "POST",
      body: JSON.stringify({ inputs: toSend, session_id: sessionId }),
    });
    if (!response.ok) throw new Error(`Server error (${response.status})`);

    const reply = await response.json();
    const idea = reply.game_idea || reply.gameIdea;
    if (!idea) throw new Error("No game idea returned from the model");

    const messageText = reply.message || "Here is your game idea.";
    pending.textContent = messageText;
    setIdeaBoxes(idea);
  } catch (error) {
    pending.textContent = `Error: ${error.message}`;
  } finally {
    sendButton.disabled = false;
    clearButton.disabled = false;
    input.focus();
  }
});

// Handle clear button click
clearButton.addEventListener("click", async () => {
  output.innerHTML = "";
  suggestions.classList.remove("hidden");
  setIdeaBoxes(null);
  try {
    await fetch(`${apiBaseUrl}/api/chat/reset`, {
      headers: { "Content-Type": "application/json" },
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  } catch (error) {
    console.error("Reset failed", error);
  }
});

// Events to request server shutdown when the page is hidden or unloaded
window.addEventListener("pagehide", requestShutdown);
window.addEventListener("beforeunload", requestShutdown);
