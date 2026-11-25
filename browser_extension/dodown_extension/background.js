const PORTS = [14370, 24370, 34370, 44370, 38370];
const EXT_VERSION = "1.0.0";
const PROTOCOL_VERSION = 2;

let ws = null;
let connected = false;
let authenticated = false;
let activePort = 14370;

async function getConfig() {
  const data = await chrome.storage.local.get({
    enabled: true,
    token: "",
    port: 14370,
    minSizeMB: 0,
  });
  return data;
}

function sendJson(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(obj));
    return true;
  }
  return false;
}

async function connectToDodown(preferredPort = null) {
  const cfg = await getConfig();
  const candidates = preferredPort ? [preferredPort, ...PORTS.filter(p => p !== preferredPort)] : [cfg.port, ...PORTS.filter(p => p !== cfg.port)];

  for (const port of candidates) {
    const ok = await new Promise((resolve) => {
      try {
        const socket = new WebSocket(`ws://127.0.0.1:${port}`);
        const timer = setTimeout(() => {
          try { socket.close(); } catch {}
          resolve(false);
        }, 1200);

        socket.onopen = () => {
          clearTimeout(timer);
          ws = socket;
          connected = true;
          activePort = port;
          chrome.storage.local.set({ port });
          sendJson({
            type: "hello",
            protocolVersion: PROTOCOL_VERSION,
            token: cfg.token || "",
            extensionVersion: EXT_VERSION,
            installType: "development",
            clientKind: "Dodown Browser Extension",
          });
          resolve(true);
        };

        socket.onmessage = async (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            if (msg.type === "hello_ack") {
              authenticated = Boolean(msg.authenticated);
            } else if (msg.type === "pair_result") {
              if (msg.ok && msg.token) {
                await chrome.storage.local.set({ token: msg.token });
                authenticated = true;
                sendJson({
                  type: "hello",
                  protocolVersion: PROTOCOL_VERSION,
                  token: msg.token,
                  extensionVersion: EXT_VERSION,
                  installType: "development",
                  clientKind: "Dodown Browser Extension",
                });
              }
              chrome.runtime.sendMessage({ type: "pair_result", ...msg }).catch(() => {});
            }
          } catch {}
        };

        socket.onclose = () => {
          if (ws === socket) {
            ws = null;
            connected = false;
            authenticated = false;
          }
        };

        socket.onerror = () => {
          clearTimeout(timer);
          resolve(false);
        };
      } catch {
        resolve(false);
      }
    });
    if (ok) return true;
  }
  return false;
}

async function sendDownloadToDodown(url, filename = "", referer = "") {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    await connectToDodown();
  }
  if (!ws || ws.readyState !== WebSocket.OPEN) return false;
  return sendJson({
    type: "create_task",
    requestId: `dl-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    source: "download",
    url,
    filename,
    referer,
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: "dodown-download-link",
      title: "Download with Dodown",
      contexts: ["link", "video", "audio", "image"],
    });
  });
  connectToDodown();
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId === "dodown-download-link") {
    const targetUrl = info.linkUrl || info.srcUrl;
    if (targetUrl) {
      await sendDownloadToDodown(targetUrl, "", info.pageUrl || "");
    }
  }
});

chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
  (async () => {
    const cfg = await getConfig();
    if (!cfg.enabled || !item.url || item.url.startsWith("blob:") || item.url.startsWith("data:")) {
      suggest();
      return;
    }
    const sent = await sendDownloadToDodown(item.finalUrl || item.url, item.filename || "", item.referrer || "");
    if (sent) {
      chrome.downloads.cancel(item.id, () => {
        chrome.downloads.erase({ id: item.id });
      });
    } else {
      suggest();
    }
  })();
  return true;
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    if (msg.type === "get_status") {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        await connectToDodown();
      }
      const cfg = await getConfig();
      sendResponse({ connected, authenticated, port: activePort, ...cfg });
    } else if (msg.type === "auto_pair") {
      const ok = await connectToDodown();
      if (!ok) {
        sendResponse({ ok: false, message: "Dodown desktop app is not running." });
        return;
      }
      sendJson({
        type: "pair_request",
        protocolVersion: PROTOCOL_VERSION,
        requestId: `pair-${Date.now()}`,
        extensionVersion: EXT_VERSION,
        clientKind: "Dodown Browser Extension",
      });
      sendResponse({ ok: true, message: "Pairing request sent — approve it in Dodown." });
    } else if (msg.type === "send_url") {
      const ok = await sendDownloadToDodown(msg.url);
      sendResponse({ ok });
    } else if (msg.type === "save_token") {
      await chrome.storage.local.set({ token: msg.token || "" });
      if (ws) try { ws.close(); } catch {}
      await connectToDodown();
      sendResponse({ ok: true, connected, authenticated });
    }
  })();
  return true;
});
