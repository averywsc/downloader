const statusEl = document.getElementById("status");
const enabledEl = document.getElementById("enabled");
const urlInput = document.getElementById("urlInput");
const tokenInput = document.getElementById("tokenInput");
const msgEl = document.getElementById("msg");
const portLabel = document.getElementById("portLabel");

function refreshStatus() {
  chrome.runtime.sendMessage({ type: "get_status" }, (res) => {
    if (!res) return;
    enabledEl.checked = Boolean(res.enabled);
    if (res.token) tokenInput.value = res.token;
    portLabel.textContent = `Port ${res.port || 14370}`;
    if (res.connected && res.authenticated) {
      statusEl.textContent = "Connected";
      statusEl.className = "pill ok";
    } else if (res.connected) {
      statusEl.textContent = "Needs Pair";
      statusEl.className = "pill";
    } else {
      statusEl.textContent = "Offline";
      statusEl.className = "pill";
    }
  });
}

enabledEl.addEventListener("change", () => {
  chrome.storage.local.set({ enabled: enabledEl.checked });
});

document.getElementById("sendBtn").addEventListener("click", () => {
  const url = urlInput.value.trim();
  if (!url) return;
  chrome.runtime.sendMessage({ type: "send_url", url }, (res) => {
    msgEl.textContent = res && res.ok ? "Sent to Dodown!" : "Could not reach Dodown desktop app.";
    if (res && res.ok) urlInput.value = "";
  });
});

document.getElementById("pairBtn").addEventListener("click", () => {
  msgEl.textContent = "Sending pairing request…";
  chrome.runtime.sendMessage({ type: "auto_pair" }, (res) => {
    msgEl.textContent = (res && res.message) || "Pairing request sent.";
  });
});

document.getElementById("saveTokenBtn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "save_token", token: tokenInput.value.trim() }, () => {
    msgEl.textContent = "Token saved.";
    setTimeout(refreshStatus, 300);
  });
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "pair_result") {
    msgEl.textContent = msg.ok ? "Paired with Dodown!" : (msg.message || "Pairing rejected.");
    refreshStatus();
  }
});

refreshStatus();
