import { createSignal, createEffect, For, Show, onCleanup } from "solid-js";

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

export default function Chats(props: { token: string; onLogout: () => void }) {
  const [agents, setAgents] = createSignal<AgentInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = createSignal<string | null>(null);
  const [messages, setMessages] = createSignal<ChatMessage[]>([]);
  const [input, setInput] = createSignal("");
  const [isStreaming, setIsStreaming] = createSignal(false);
  const [error, setError] = createSignal("");

  let ws: WebSocket | null = null;
  let msgIdCounter = 0;
  let chatContainerRef: HTMLDivElement | undefined;
  let streamingMsgId: number | null = null;

  // Fetch agents list
  createEffect(async () => {
    try {
      const res = await fetch("/agents", {
        headers: { Authorization: `Bearer ${props.token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAgents(data.agents);
      } else if (res.status === 401) {
        props.onLogout();
      }
    } catch {
      setError("Failed to load agents");
    }
  });

  const scrollToBottom = () => {
    if (chatContainerRef) {
      chatContainerRef.scrollTop = chatContainerRef.scrollHeight;
    }
  };

  const now = () => {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const connectWebSocket = (agentId: string) => {
    if (ws) {
      ws.close();
      ws = null;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/agent/${agentId}/chat?token=${props.token}`;
    ws = new WebSocket(url);

    ws.onopen = () => setError("");

    ws.onmessage = (event) => {
      const chunk = event.data;
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
    ws.onclose = () => {
      setIsStreaming(false);
      streamingMsgId = null;
    };
  };

  const selectAgent = (agentId: string) => {
    if (selectedAgent() === agentId) return;
    setSelectedAgent(agentId);
    setMessages([]);
    setError("");
    streamingMsgId = null;
    connectWebSocket(agentId);
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
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  onCleanup(() => {
    if (ws) ws.close();
  });

  // Gradient colors for fallback initials
  const avatarColors = [
    "from-violet-500 to-purple-600",
    "from-cyan-500 to-blue-600",
    "from-emerald-500 to-teal-600",
    "from-amber-500 to-orange-600",
    "from-rose-500 to-pink-600",
    "from-indigo-500 to-blue-600",
  ];
  const getAvatarColor = (i: number) => avatarColors[i % avatarColors.length];

  /** Render avatar: image if available, gradient initial otherwise */
  const Avatar = (p: { agent: AgentInfo; index: number; size: string; textSize: string }) => (
    <Show
      when={p.agent.hasAvatar}
      fallback={
        <div
          class={`${p.size} rounded-full flex items-center justify-center text-white font-bold ${p.textSize} bg-gradient-to-br ${getAvatarColor(p.index)} shrink-0`}
        >
          {p.agent.initial}
        </div>
      }
    >
      <img
        src={`/agent/${p.agent.id}/avatar`}
        alt={p.agent.name ?? p.agent.id}
        class={`${p.size} rounded-full object-cover shrink-0 bg-neutral-800`}
      />
    </Show>
  );

  return (
    <div class="w-full h-full flex gap-0 -m-8">
      {/* Agent Sidebar */}
      <div class="w-24 min-w-24 bg-neutral-900 border-r border-neutral-800 flex flex-col items-center py-4 gap-1 overflow-y-auto">
        <div class="text-[10px] text-neutral-500 uppercase font-semibold tracking-wider mb-2">
          Agents
        </div>
        <For each={agents()} fallback={<div class="text-neutral-600 text-xs py-4">...</div>}>
          {(agent, index) => (
            <button
              onClick={() => selectAgent(agent.id)}
              class={`relative group flex flex-col items-center gap-1.5 py-2 px-1 rounded-xl transition-all duration-200 cursor-pointer w-full
                ${selectedAgent() === agent.id
                  ? "bg-neutral-800/80"
                  : "hover:bg-neutral-800/40"
                }`}
              title={agent.name ?? agent.id}
            >
              <div
                class={`transition-all duration-200 rounded-full
                  ${selectedAgent() === agent.id
                    ? "ring-2 ring-blue-500 ring-offset-2 ring-offset-neutral-900 scale-105 shadow-lg shadow-blue-500/20"
                    : "opacity-70 group-hover:opacity-100 group-hover:scale-105"
                  }`}
              >
                <Avatar agent={agent} index={index()} size="w-14 h-14" textSize="text-xl" />
              </div>
              <span
                class={`text-[10px] leading-tight text-center truncate w-full px-0.5 transition-colors
                  ${selectedAgent() === agent.id ? "text-white font-medium" : "text-neutral-500 group-hover:text-neutral-300"
                  }`}
              >
                {agent.name ?? agent.id}
              </span>
            </button>
          )}
        </For>
      </div>

      {/* Chat Area */}
      <div class="flex-1 flex flex-col min-w-0">
        <Show
          when={selectedAgent()}
          fallback={
            <div class="flex-1 flex items-center justify-center">
              <div class="text-center">
                <div class="text-6xl mb-4 opacity-20">💬</div>
                <div class="text-neutral-500 text-lg">Select an agent to begin</div>
                <div class="text-neutral-600 text-sm mt-2">Click an avatar on the left to start chatting</div>
              </div>
            </div>
          }
        >
          {/* Chat Header */}
          <div class="px-6 py-4 border-b border-neutral-800 bg-neutral-900/80 backdrop-blur-sm flex items-center gap-3">
            {(() => {
              const agent = agents().find((a) => a.id === selectedAgent());
              const idx = agents().findIndex((a) => a.id === selectedAgent());
              return (
                <>
                  {agent && <Avatar agent={agent} index={idx} size="w-10 h-10" textSize="text-sm" />}
                  <div>
                    <div class="font-semibold text-white">{agent?.name ?? selectedAgent()}</div>
                    <div class="text-xs text-neutral-500">{selectedAgent()}</div>
                  </div>
                </>
              );
            })()}
            <Show when={isStreaming()}>
              <div class="ml-auto flex items-center gap-2 text-xs text-neutral-400">
                <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Streaming...
              </div>
            </Show>
          </div>

          {/* Messages */}
          <div ref={chatContainerRef} class="flex-1 p-6 overflow-y-auto space-y-4">
            <Show when={messages().length === 0}>
              <div class="flex items-center justify-center h-full">
                <div class="text-neutral-600 text-sm">Send a message to start the conversation</div>
              </div>
            </Show>
            <For each={messages()}>
              {(msg) => (
                <div class={`flex flex-col ${msg.sender === "user" ? "items-end" : "items-start"}`}>
                  <div
                    class={`px-4 py-3 rounded-2xl max-w-[70%] ${msg.sender === "user"
                      ? "bg-blue-600/20 text-blue-100 border border-blue-600/30 rounded-br-md"
                      : "bg-neutral-800 border border-neutral-700 rounded-bl-md"
                      }`}
                  >
                    <div class="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
                  </div>
                  <div class="text-[10px] text-neutral-600 mt-1 px-1">{msg.timestamp}</div>
                </div>
              )}
            </For>
          </div>

          {/* Error Banner */}
          <Show when={error()}>
            <div class="mx-6 mb-2 p-3 bg-red-900/30 border border-red-800/50 rounded-lg text-red-300 text-xs">
              {error()}
            </div>
          </Show>

          {/* Input */}
          <div class="px-6 py-4 border-t border-neutral-800 bg-neutral-900/80 backdrop-blur-sm">
            <div class="flex gap-3 items-end">
              <input
                type="text"
                placeholder="Type a message..."
                value={input()}
                onInput={(e) => setInput(e.currentTarget.value)}
                onKeyDown={handleKeyDown}
                class="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500/50 transition-all placeholder:text-neutral-600"
              />
              <button
                onClick={sendMessage}
                disabled={!input().trim() || !selectedAgent()}
                class={`px-5 py-3 rounded-xl font-medium text-sm transition-all
                  ${input().trim() && selectedAgent()
                    ? "bg-neutral-200 hover:bg-white text-neutral-900"
                    : "bg-neutral-800 text-neutral-600 cursor-not-allowed border border-neutral-700"
                  }`}
              >
                Send
              </button>
            </div>
          </div>
        </Show>
      </div>
    </div>
  );
}
