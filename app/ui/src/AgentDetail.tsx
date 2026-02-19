import { createSignal, createEffect, For, Show, onCleanup } from "solid-js";
import "katex/dist/katex.min.css";
import { renderMarkdown } from "./renderLatex";

interface AgentInfo {
  id: string;
  name: string;
  initial: string;
  hasAvatar: boolean;
}

interface ChatMessage {
  id: number;
  sender: "user" | "agent";
  content: string;
  timestamp: string;
}

type Tab = string; // filename

export default function AgentDetail(props: {
  token: string;
  agentId: string;
  onLogout: () => void;
  onBack: () => void;
}) {
  const [agent, setAgent] = createSignal<AgentInfo | null>(null);
  const [files, setFiles] = createSignal<string[]>([]);
  const [activeTab, setActiveTab] = createSignal<Tab>("");
  const [fileContent, setFileContent] = createSignal("");
  const [fileDirty, setFileDirty] = createSignal(false);
  const [saving, setSaving] = createSignal(false);

  // Chat state
  const [messages, setMessages] = createSignal<ChatMessage[]>([]);
  const [input, setInput] = createSignal("");
  const [isStreaming, setIsStreaming] = createSignal(false);
  const [error, setError] = createSignal("");

  let ws: WebSocket | null = null;
  let msgIdCounter = 0;
  let chatContainerRef: HTMLDivElement | undefined;
  let streamingMsgId: number | null = null;

  const headers = () => ({ Authorization: `Bearer ${props.token}` });

  // Fetch agent info
  createEffect(async () => {
    try {
      const res = await fetch("/agents", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        const found = data.agents.find((a: AgentInfo) => a.id === props.agentId);
        if (found) setAgent(found);
      } else if (res.status === 401) {
        props.onLogout();
      }
    } catch {}
  });

  // Fetch MD files
  createEffect(async () => {
    try {
      const res = await fetch(`/agent/${props.agentId}/files`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files);
        if (data.files.length > 0 && !activeTab()) {
          setActiveTab(data.files[0]);
        }
      }
    } catch {}
  });

  // Load file content when tab changes to a file
  createEffect(async () => {
    const tab = activeTab();
    if (!tab) return;
    setFileContent("");
    setFileDirty(false);
    try {
      const res = await fetch(`/agent/${props.agentId}/file/${tab}`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setFileContent(data.content);
      }
    } catch {}
  });

  // Connect WebSocket and load history on mount
  createEffect(async () => {
    // Load chat history
    try {
      const res = await fetch(`/agent/${props.agentId}/history`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          const loaded: ChatMessage[] = data.messages.map((m: any) => ({
            id: ++msgIdCounter,
            sender: m.sender as "user" | "agent",
            content: m.content,
            timestamp: m.timestamp || "",
          }));
          setMessages(loaded);
          setTimeout(scrollToBottom, 50);
        }
      }
    } catch {}
    connectWebSocket();
  });

  onCleanup(() => {
    if (ws) ws.close();
  });

  const scrollToBottom = () => {
    if (chatContainerRef) chatContainerRef.scrollTop = chatContainerRef.scrollHeight;
  };

  const now = () => {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const connectWebSocket = () => {
    if (ws) { ws.close(); ws = null; }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/agent/${props.agentId}/chat?token=${props.token}`;
    ws = new WebSocket(url);
    ws.onopen = () => setError("");
    ws.onmessage = (event) => {
      const chunk = event.data;
      // End-of-stream signal
      if (chunk === "\x00") {
        setIsStreaming(false);
        streamingMsgId = null;
        return;
      }
      if (streamingMsgId !== null) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === streamingMsgId ? { ...m, content: m.content + chunk } : m
          )
        );
      } else {
        streamingMsgId = ++msgIdCounter;
        setMessages((prev) => [
          ...prev,
          { id: streamingMsgId!, sender: "agent", content: chunk, timestamp: now() },
        ]);
      }
      scrollToBottom();
    };
    ws.onerror = () => setError("WebSocket connection error");
    ws.onclose = () => { setIsStreaming(false); streamingMsgId = null; };
  };

  const sendMessage = () => {
    const text = input().trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    setMessages((prev) => [
      ...prev,
      { id: ++msgIdCounter, sender: "user", content: text, timestamp: now() },
    ]);
    setInput("");
    setIsStreaming(true);
    streamingMsgId = null;
    ws.send(text);
    scrollToBottom();
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const clearHistory = async () => {
    try {
      await fetch(`/agent/${props.agentId}/history`, {
        method: "DELETE",
        headers: headers(),
      });
    } catch {}
    setMessages([]);
    msgIdCounter = 0;
    streamingMsgId = null;
  };

  const saveFile = async () => {
    const tab = activeTab();
    if (!tab) return;
    setSaving(true);
    try {
      await fetch(`/agent/${props.agentId}/file/${tab}`, {
        method: "PUT",
        headers: { ...headers(), "Content-Type": "application/json" },
        body: JSON.stringify({ content: fileContent() }),
      });
      setFileDirty(false);
      // Reload agent configuration after save
      await fetch(`/agent/${props.agentId}/reload`, {
        method: "POST",
        headers: headers(),
      });
    } catch {}
    setSaving(false);
  };

  const handleSaveKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "s") {
      e.preventDefault();
      saveFile();
    }
  };

  // Avatar colors
  const avatarColors = [
    "from-violet-500 to-purple-600",
    "from-cyan-500 to-blue-600",
    "from-emerald-500 to-teal-600",
    "from-amber-500 to-orange-600",
    "from-rose-500 to-pink-600",
  ];

  return (
    <div class="w-full h-full flex flex-col min-h-0">
      {/* Top Bar */}
      <div class="flex items-center gap-4 px-6 py-3 border-b border-neutral-800 bg-neutral-900 shrink-0">
        <button
          onClick={props.onBack}
          class="text-neutral-400 hover:text-white transition-colors text-sm flex items-center gap-1"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          Agents
        </button>

        <div class="flex items-center gap-3">
          <Show when={agent()}>
            {(a) => (
              <>
                <Show
                  when={a().hasAvatar}
                  fallback={
                    <div class={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm bg-gradient-to-br ${avatarColors[0]} shrink-0`}>
                      {a().initial}
                    </div>
                  }
                >
                  <img
                    src={`/agent/${a().id}/avatar`}
                    alt={a().name}
                    class="w-10 h-10 rounded-full object-cover shrink-0 bg-neutral-800"
                  />
                </Show>
                <div>
                  <div class="font-semibold text-white text-lg leading-tight">{a().name}</div>
                  <div class="text-xs text-neutral-500">{a().id}</div>
                </div>
              </>
            )}
          </Show>
        </div>

        <Show when={isStreaming()}>
          <div class="ml-auto flex items-center gap-2 text-xs text-neutral-400">
            <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Streaming...
          </div>
        </Show>
      </div>

      {/* Split: Upper = Editor, Lower = Chat */}
      <div class="flex-1 min-h-0 flex flex-col">

        {/* ===== Upper Panel: Settings Editor ===== */}
        <div class="h-1/2 flex flex-col border-b border-neutral-700 min-h-0">
          {/* File Tabs */}
          <div class="flex border-b border-neutral-800 bg-neutral-900/80 shrink-0 px-4">
            <For each={files()} fallback={<div class="px-4 py-2.5 text-sm text-neutral-600">No files</div>}>
              {(file) => (
                <button
                  onClick={() => setActiveTab(file)}
                  class={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors
                    ${activeTab() === file
                      ? "border-blue-500 text-blue-400"
                      : "border-transparent text-neutral-500 hover:text-neutral-300"
                    }`}
                >
                  {file}
                </button>
              )}
            </For>
          </div>

          {/* Editor Content */}
          <Show when={activeTab()}>
            <div class="flex-1 flex flex-col min-h-0">
              {/* Toolbar */}
              <div class="flex items-center gap-3 px-4 py-2 border-b border-neutral-800 bg-neutral-900/50 shrink-0">
                <span class="text-xs text-neutral-500 font-mono">{activeTab()}</span>
                <div class="ml-auto flex items-center gap-2">
                  <Show when={fileDirty()}>
                    <span class="text-xs text-amber-400">Unsaved</span>
                  </Show>
                  <button
                    onClick={saveFile}
                    disabled={!fileDirty() || saving()}
                    class={`px-3 py-1 rounded-lg text-xs font-medium transition-all
                      ${fileDirty() && !saving()
                        ? "bg-blue-600 hover:bg-blue-500 text-white"
                        : "bg-neutral-800 text-neutral-600 cursor-not-allowed border border-neutral-700"
                      }`}
                  >
                    {saving() ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>

              {/* Editor */}
              <textarea
                value={fileContent()}
                onInput={(e) => { setFileContent(e.currentTarget.value); setFileDirty(true); }}
                onKeyDown={handleSaveKeyDown}
                class="flex-1 w-full bg-neutral-950 text-neutral-200 font-mono text-sm p-4 resize-none focus:outline-none leading-relaxed min-h-0"
                spellcheck={false}
              />
            </div>
          </Show>
        </div>

        {/* ===== Lower Panel: Chat (always visible) ===== */}
        <div class="h-1/2 flex flex-col min-h-0 bg-neutral-900/30">
          {/* Chat Header */}
          <div class="flex items-center gap-2 px-4 py-2 border-b border-neutral-800 bg-neutral-900/60 shrink-0">
            <span class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Chat</span>
            <Show when={error()}>
              <span class="text-xs text-red-400 ml-2">{error()}</span>
            </Show>
            <Show when={messages().length > 0}>
              <button
                onClick={clearHistory}
                class="ml-auto text-[10px] text-neutral-500 hover:text-neutral-300 transition-colors"
                title="Clear chat history"
              >
                Clear
              </button>
            </Show>
          </div>

          {/* Messages */}
          <div ref={chatContainerRef} class="flex-1 px-4 py-3 overflow-y-auto space-y-3 min-h-0">
            <Show when={messages().length === 0}>
              <div class="flex items-center justify-center h-full">
                <div class="text-neutral-600 text-xs">Send a message to start the conversation</div>
              </div>
            </Show>
            <For each={messages()}>
              {(msg) => (
                <div class={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                  <div
                    class={`px-3 py-2 rounded-2xl max-w-[75%] ${
                      msg.sender === "user"
                        ? "bg-blue-600/20 text-blue-100 border border-blue-600/30 rounded-br-md"
                        : "bg-neutral-800 border border-neutral-700 rounded-bl-md"
                    }`}
                  >
                    <Show when={msg.sender === "agent"}>
                      <div class="text-sm leading-relaxed prose-chat latex-content" innerHTML={renderMarkdown(msg.content)} />
                    </Show>
                    <Show when={msg.sender === "user"}>
                      <div class="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                    </Show>
                  </div>
                  <div class="text-[10px] text-neutral-600 mt-0.5 px-1">{msg.timestamp}</div>
                </div>
              )}
            </For>
          </div>

          {/* Input */}
          <div class="px-4 py-3 border-t border-neutral-800 bg-neutral-900/80 shrink-0">
            <div class="flex gap-2 items-end">
              <input
                type="text"
                placeholder="Type a message..."
                value={input()}
                onInput={(e) => setInput(e.currentTarget.value)}
                onKeyDown={handleKeyDown}
                class="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500/50 transition-all placeholder:text-neutral-600"
              />
              <button
                onClick={sendMessage}
                disabled={!input().trim()}
                class={`px-4 py-2.5 rounded-xl font-medium text-sm transition-all
                  ${input().trim()
                    ? "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20"
                    : "bg-neutral-800 text-neutral-600 cursor-not-allowed border border-neutral-700"
                  }`}
              >
                Send
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
