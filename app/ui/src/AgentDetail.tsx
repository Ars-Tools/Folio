import { createSignal, createEffect, For, Show, onCleanup } from "solid-js";
import "katex/dist/katex.min.css";
import { renderMarkdown } from "./renderLatex";

interface AgentConfig {
  id: string;
  name: string;
  provider: string;
  model: string;
  prompt: string;
  avatar: boolean;
  capabilities: string[];
  params: Record<string, number | string>;
  concurrency: number;
}

interface ChatMessage {
  id: number;
  sender: "user" | "agent";
  content: string;
  timestamp: string;
}

export default function AgentDetail(props: {
  token: string;
  agentId: string;
  onLogout: () => void;
  onBack: () => void;
}) {
  // Settings state
  const [config, setConfig] = createSignal<AgentConfig | null>(null);
  const [providers, setProviders] = createSignal<{ id: string; name: string }[]>([]);
  const [models, setModels] = createSignal<string[]>([]);
  const [modelsLoading, setModelsLoading] = createSignal(false);
  const [availableCaps, setAvailableCaps] = createSignal<{ id: string; label: string; description: string; kind: string }[]>([]);
  const [dirty, setDirty] = createSignal(false);
  const [saving, setSaving] = createSignal(false);
  const [saveMsg, setSaveMsg] = createSignal("");

  // Skills & Approvals state
  const [equippedSkills, setEquippedSkills] = createSignal<{ id: string; exists: boolean }[]>([]);
  const [allSkills, setAllSkills] = createSignal<{ id: string }[]>([]);
  const [approvals, setApprovals] = createSignal<{ id: number; request: string; status: string; update: string }[]>([]);

  // Chat state
  const [chatOpen, setChatOpen] = createSignal(false);
  const [messages, setMessages] = createSignal<ChatMessage[]>([]);
  const [input, setInput] = createSignal("");
  const [isStreaming, setIsStreaming] = createSignal(false);
  const [error, setError] = createSignal("");

  let ws: WebSocket | null = null;
  let msgIdCounter = 0;
  let chatContainerRef: HTMLDivElement | undefined;
  let streamingMsgId: number | null = null;

  const headers = () => ({ Authorization: `Bearer ${props.token}` });
  const jsonHeaders = () => ({ Authorization: `Bearer ${props.token}`, "Content-Type": "application/json" });

  // -----------------------------------------------------------------------
  // Fetch agent config
  // -----------------------------------------------------------------------
  const fetchConfig = async () => {
    try {
      const res = await fetch(`/agent/${props.agentId}`, { headers: headers() });
      if (res.ok) {
        const data: AgentConfig = await res.json();
        setConfig(data);
        setDirty(false);
      } else if (res.status === 401) {
        props.onLogout();
      }
    } catch {}
  };

  const fetchProviders = async () => {
    try {
      const res = await fetch("/providers", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setProviders(data.providers || []);
      }
    } catch {}
  };

  const fetchModels = async (providerId: string) => {
    if (!providerId) { setModels([]); return; }
    setModelsLoading(true);
    try {
      const res = await fetch(`/provider/${providerId}/models`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setModels((data.models || []).map((m: { id: string }) => m.id));
      } else {
        setModels([]);
      }
    } catch {
      setModels([]);
    } finally {
      setModelsLoading(false);
    }
  };

  const fetchCapabilities = async () => {
    try {
      const res = await fetch("/capabilities", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setAvailableCaps(data.capabilities || []);
      }
    } catch {}
  };

  const fetchEquippedSkills = async () => {
    try {
      const res = await fetch(`/agent/${props.agentId}/skills`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setEquippedSkills(data.skills || []);
      }
    } catch {}
  };

  const fetchAllSkills = async () => {
    try {
      const res = await fetch("/skills", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setAllSkills((data.skills || []).map((s: { id: string }) => ({ id: s.id })));
      }
    } catch {}
  };

  const fetchApprovals = async () => {
    try {
      const res = await fetch(`/agent/${props.agentId}/approvals`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setApprovals(data.approvals || []);
      }
    } catch {}
  };

  const equipSkill = async (skillId: string) => {
    const res = await fetch(`/agent/${props.agentId}/skills`, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({ skill: skillId }),
    });
    if (res.ok) fetchEquippedSkills();
  };

  const unequipSkill = async (skillId: string) => {
    const res = await fetch(`/agent/${props.agentId}/skill/${skillId}`, {
      method: "DELETE",
      headers: headers(),
    });
    if (res.ok) fetchEquippedSkills();
  };

  const deleteApproval = async (id: number) => {
    const res = await fetch(`/approval/${id}`, {
      method: "DELETE",
      headers: headers(),
    });
    if (res.ok) fetchApprovals();
  };

  createEffect(() => {
    fetchConfig().then(() => {
      const c = config();
      if (c?.provider) fetchModels(c.provider);
    });
    fetchProviders();
    fetchCapabilities();
    fetchAllSkills();
    fetchEquippedSkills();
    fetchApprovals();
  });

  // -----------------------------------------------------------------------
  // Update helpers
  // -----------------------------------------------------------------------
  const update = <K extends keyof AgentConfig>(key: K, value: AgentConfig[K]) => {
    const c = config();
    if (!c) return;
    setConfig({ ...c, [key]: value });
    setDirty(true);
    setSaveMsg("");
  };

  const handleSave = async () => {
    const c = config();
    if (!c || !dirty()) return;
    setSaving(true);
    setSaveMsg("");
    try {
      const res = await fetch(`/agent/${props.agentId}`, {
        method: "PUT",
        headers: jsonHeaders(),
        body: JSON.stringify({
          name: c.name,
          provider: c.provider,
          model: c.model,
          prompt: c.prompt,
          capabilities: c.capabilities,
          params: c.params,
          concurrency: c.concurrency,
        }),
      });
      if (res.ok) {
        setDirty(false);
        setSaveMsg("Saved");
        setTimeout(() => setSaveMsg(""), 2000);
      } else {
        const d = await res.json();
        setSaveMsg(d.detail || "Save failed");
      }
    } catch {
      setSaveMsg("Network error");
    }
    setSaving(false);
  };

  const handleSaveKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "s") {
      e.preventDefault();
      handleSave();
    }
  };

  // -----------------------------------------------------------------------
  // Chat — WebSocket + history
  // -----------------------------------------------------------------------
  createEffect(async () => {
    try {
      const res = await fetch(`/agent/${props.agentId}/history`, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        if (data.messages?.length > 0) {
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

  onCleanup(() => { if (ws) ws.close(); });

  const scrollToBottom = () => {
    if (chatContainerRef) chatContainerRef.scrollTop = chatContainerRef.scrollHeight;
  };

  const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const connectWebSocket = () => {
    if (ws) { ws.close(); ws = null; }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(`${protocol}//${window.location.host}/agent/${props.agentId}/chat?token=${props.token}`);
    ws.onopen = () => setError("");
    ws.onmessage = (event) => {
      const chunk = event.data;
      if (chunk === "\x00") { setIsStreaming(false); streamingMsgId = null; return; }
      if (streamingMsgId !== null) {
        setMessages((prev) => prev.map((m) => m.id === streamingMsgId ? { ...m, content: m.content + chunk } : m));
      } else {
        streamingMsgId = ++msgIdCounter;
        setMessages((prev) => [...prev, { id: streamingMsgId!, sender: "agent", content: chunk, timestamp: now() }]);
      }
      scrollToBottom();
    };
    ws.onerror = () => setError("WebSocket connection error");
    ws.onclose = () => { setIsStreaming(false); streamingMsgId = null; };
  };

  const sendMessage = () => {
    const text = input().trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    setMessages((prev) => [...prev, { id: ++msgIdCounter, sender: "user", content: text, timestamp: now() }]);
    setInput("");
    setIsStreaming(true);
    streamingMsgId = null;
    ws.send(text);
    scrollToBottom();
  };

  const handleChatKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const clearHistory = async () => {
    try { await fetch(`/agent/${props.agentId}/history`, { method: "DELETE", headers: headers() }); } catch {}
    setMessages([]);
    msgIdCounter = 0;
    streamingMsgId = null;
  };

  // -----------------------------------------------------------------------
  // Avatar helpers
  // -----------------------------------------------------------------------
  const avatarColors = [
    "from-violet-500 to-purple-600",
    "from-cyan-500 to-blue-600",
    "from-emerald-500 to-teal-600",
    "from-amber-500 to-orange-600",
    "from-rose-500 to-pink-600",
  ];

  // -----------------------------------------------------------------------
  // Avatar upload
  // -----------------------------------------------------------------------
  let avatarInputRef: HTMLInputElement | undefined;

  const handleAvatarUpload = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`/agent/${props.agentId}/avatar`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${props.token}` },
        body: formData,
      });
      if (res.ok) {
        // Force re-fetch config to update avatar flag
        await fetchConfig();
      } else {
        const d = await res.json();
        setSaveMsg(d.detail || "Upload failed");
      }
    } catch {
      setSaveMsg("Upload failed");
    }
  };

  const handleDeleteAgent = async () => {
    if (!confirm(`Delete agent "${props.agentId}"? This cannot be undone.`)) return;
    try {
      const res = await fetch(`/agent/${props.agentId}`, {
        method: "DELETE",
        headers: headers(),
      });
      if (res.ok) props.onBack();
      else setSaveMsg("Delete failed");
    } catch {
      setSaveMsg("Delete failed");
    }
  };

  const handleAvatarDelete = async () => {
    try {
      const res = await fetch(`/agent/${props.agentId}/avatar`, {
        method: "DELETE",
        headers: headers(),
      });
      if (res.ok) await fetchConfig();
    } catch {}
  };

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div class="w-full h-full flex flex-col min-h-0" onKeyDown={handleSaveKeyDown}>

      {/* ===== Top Bar ===== */}
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

        <Show when={config()}>
          {(c) => (
            <div class="flex items-center gap-3">
              <input
                ref={avatarInputRef}
                type="file"
                accept="image/*"
                class="hidden"
                onChange={(e) => {
                  const f = e.currentTarget.files?.[0];
                  if (f) handleAvatarUpload(f);
                  e.currentTarget.value = "";
                }}
              />
              <div class="relative group cursor-pointer" onClick={() => avatarInputRef?.click()}>
                <Show
                  when={c().avatar}
                  fallback={
                    <div class={`w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-sm bg-gradient-to-br ${avatarColors[0]} shrink-0`}>
                      {c().id[0].toUpperCase()}
                    </div>
                  }
                >
                  <img src={`/agent/${c().id}/avatar?t=${Date.now()}`} alt={c().name} class="w-9 h-9 rounded-full object-cover shrink-0 bg-neutral-800" />
                </Show>
                <div class="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </div>
              </div>
              <Show when={c().avatar}>
                <button
                  onClick={(e) => { e.stopPropagation(); handleAvatarDelete(); }}
                  class="text-[10px] text-neutral-600 hover:text-red-400 transition-colors"
                  title="Remove avatar"
                >
                  ×
                </button>
              </Show>
              <div>
                <div class="font-semibold text-white text-lg leading-tight">{c().name}</div>
                <div class="text-xs text-neutral-500">{c().id}</div>
              </div>
            </div>
          )}
        </Show>

        <div class="ml-auto flex items-center gap-3">
          <Show when={saveMsg()}>
            <span class={`text-xs ${saveMsg() === "Saved" ? "text-neutral-400" : "text-red-400"}`}>{saveMsg()}</span>
          </Show>
          <Show when={dirty()}>
            <span class="text-xs text-amber-400">Unsaved</span>
          </Show>
          <button
            onClick={handleDeleteAgent}
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all text-red-400 hover:bg-red-400/10 border border-neutral-700"
            title="Delete agent"
          >
            Delete
          </button>
          <button
            onClick={handleSave}
            disabled={!dirty() || saving()}
            class={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all
              ${dirty() && !saving()
                ? "bg-neutral-200 hover:bg-white text-neutral-900"
                : "bg-neutral-800 text-neutral-600 cursor-not-allowed border border-neutral-700"
              }`}
          >
            {saving() ? "Saving..." : "Save"}
          </button>
          <Show when={isStreaming()}>
            <div class="flex items-center gap-2 text-xs text-neutral-400">
              <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Streaming
            </div>
          </Show>
        </div>
      </div>

      {/* ===== Main Body ===== */}
      <div class="flex-1 min-h-0 flex flex-col">

        {/* ===== Settings Panel ===== */}
        <div class={`flex-1 min-h-0 overflow-y-auto px-6 py-6 ${chatOpen() ? "max-h-[50%]" : ""}`}>
          <Show when={config()} fallback={<div class="text-neutral-500 text-sm">Loading...</div>}>
            {(c) => (
              <div class="max-w-3xl space-y-6">

                {/* Name + ID row */}
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">Name</label>
                    <input
                      type="text"
                      value={c().name}
                      onInput={(e) => update("name", e.currentTarget.value)}
                      class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neutral-500"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">ID</label>
                    <input
                      type="text"
                      value={c().id}
                      disabled
                      class="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-neutral-500 text-sm cursor-not-allowed font-mono"
                    />
                  </div>
                </div>

                {/* Provider + Model row */}
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">Provider</label>
                    <select
                      value={c().provider}
                      onChange={(e) => {
                        const v = e.currentTarget.value;
                        update("provider", v);
                        fetchModels(v);
                      }}
                      class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 font-mono appearance-none"
                    >
                      <Show when={!providers().find((p) => p.id === c().provider)}>
                        <option value={c().provider}>{c().provider}</option>
                      </Show>
                      <For each={providers()}>
                        {(p) => <option value={p.id}>{p.name} ({p.id})</option>}
                      </For>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">Model</label>
                    <Show when={models().length > 0} fallback={
                      <input
                        type="text"
                        value={c().model}
                        onInput={(e) => update("model", e.currentTarget.value)}
                        placeholder={modelsLoading() ? "Loading…" : ""}
                        class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 font-mono"
                      />
                    }>
                      <select
                        value={c().model}
                        onChange={(e) => update("model", e.currentTarget.value)}
                        class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 font-mono appearance-none"
                      >
                        <Show when={c().model && !models().includes(c().model)}>
                          <option value={c().model}>{c().model}</option>
                        </Show>
                        <For each={models()}>
                          {(m) => <option value={m}>{m}</option>}
                        </For>
                      </select>
                    </Show>
                  </div>
                </div>

                {/* Concurrency + Parameters */}
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">Concurrency <span class="text-neutral-600">(0 = unlimited)</span></label>
                    <input
                      type="number"
                      min="0"
                      value={c().concurrency}
                      onInput={(e) => update("concurrency", parseInt(e.currentTarget.value) || 0)}
                      class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 font-mono"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">Parameters</label>
                    <input
                      type="text"
                      value={JSON.stringify(c().params)}
                      onInput={(e) => {
                        try { update("params", JSON.parse(e.currentTarget.value)); } catch {}
                      }}
                      placeholder="{}"
                      class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 font-mono"
                    />
                  </div>
                </div>

                {/* System Prompt */}
                <div>
                  <label class="block text-xs font-medium text-neutral-400 mb-1.5">System Prompt</label>
                  <textarea
                    value={c().prompt}
                    onInput={(e) => update("prompt", e.currentTarget.value)}
                    rows={12}
                    class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 font-mono leading-relaxed resize-y"
                    spellcheck={false}
                    placeholder="Enter system prompt..."
                  />
                </div>

                {/* Capabilities */}
                <div>
                  <label class="block text-xs font-medium text-neutral-400 mb-1.5">Capabilities</label>
                  {/* Selected tags */}
                  <Show when={c().capabilities.length > 0}>
                    <div class="flex flex-wrap gap-2 mb-2">
                      <For each={c().capabilities}>
                        {(capId) => {
                          const cap = () => availableCaps().find((a) => a.id === capId);
                          return (
                            <span
                              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-700 border border-neutral-500 text-sm font-medium text-white"
                              title={cap()?.description || capId}
                            >
                              {cap()?.label || capId}
                              <button
                                type="button"
                                onClick={() => update("capabilities", c().capabilities.filter((x) => x !== capId))}
                                class="text-neutral-400 hover:text-red-400 transition-colors"
                              >&times;</button>
                            </span>
                          );
                        }}
                      </For>
                    </div>
                  </Show>
                  {/* Add — autocomplete */}
                  {(() => {
                    const [capQuery, setCapQuery] = createSignal("");
                    const [showCapSugg, setShowCapSugg] = createSignal(false);
                    const [capIdx, setCapIdx] = createSignal(-1);
                    const capCandidates = () => {
                      const q = capQuery().toLowerCase();
                      const unselected = availableCaps().filter((a) => !c().capabilities.includes(a.id));
                      if (!q) return unselected;
                      return unselected.filter((a) => a.id.toLowerCase().startsWith(q) || a.label.toLowerCase().startsWith(q));
                    };
                    const addCap = (id: string) => {
                      if (id && !c().capabilities.includes(id)) {
                        update("capabilities", [...c().capabilities, id]);
                      }
                      setCapQuery("");
                      setShowCapSugg(false);
                      setCapIdx(-1);
                    };
                    return (
                      <div class="relative">
                        <input
                          type="text"
                          value={capQuery()}
                          onInput={(e) => { setCapQuery(e.currentTarget.value); setShowCapSugg(true); setCapIdx(-1); }}
                          onFocus={() => { setShowCapSugg(true); setCapIdx(-1); }}
                          onKeyDown={(e) => {
                            const list = capCandidates();
                            if (e.key === "ArrowDown") {
                              e.preventDefault();
                              setCapIdx((i) => (i < list.length - 1 ? i + 1 : 0));
                            } else if (e.key === "ArrowUp") {
                              e.preventDefault();
                              setCapIdx((i) => (i > 0 ? i - 1 : list.length - 1));
                            } else if (e.key === "Enter") {
                              e.preventDefault();
                              if (capIdx() >= 0 && capIdx() < list.length) {
                                addCap(list[capIdx()].id);
                              } else if (list.length === 1) {
                                addCap(list[0].id);
                              }
                            } else if (e.key === "Escape") {
                              setShowCapSugg(false);
                              setCapIdx(-1);
                            }
                          }}
                          placeholder="Add capability…"
                          class="bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-neutral-600 font-mono w-64"
                        />
                        <Show when={showCapSugg() && capCandidates().length > 0}>
                          <div
                            class="absolute z-20 mt-1 w-64 max-h-48 overflow-y-auto bg-neutral-900 border border-neutral-700 rounded-lg shadow-lg"
                            onMouseDown={(e) => e.preventDefault()}
                          >
                            <For each={capCandidates()}>
                              {(cap, i) => (
                                <button
                                  type="button"
                                  class={`w-full text-left px-3 py-2 text-sm transition-colors flex items-center justify-between ${
                                    i() === capIdx() ? "bg-neutral-700 text-white" : "text-neutral-200 hover:bg-neutral-800"
                                  }`}
                                  onClick={() => addCap(cap.id)}
                                >
                                  <span>{cap.label}</span>
                                  <span class="text-neutral-600 text-xs font-mono">{cap.kind}</span>
                                </button>
                              )}
                            </For>
                          </div>
                        </Show>
                      </div>
                    );
                  })()}
                </div>

                {/* Equipped Skills */}
                <div>
                  <label class="block text-xs font-medium text-neutral-400 mb-1.5">Equipped Skills</label>
                  <Show when={equippedSkills().length > 0} fallback={
                    <p class="text-sm text-neutral-600">No skills equipped</p>
                  }>
                    <div class="flex flex-wrap gap-2 mb-2">
                      <For each={equippedSkills()}>
                        {(s) => (
                          <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-800 border border-neutral-700 text-sm text-neutral-200 font-mono">
                            {s.id}
                            <Show when={!s.exists}>
                              <span class="text-red-400 text-xs" title="Skill not found">!</span>
                            </Show>
                            <button
                              type="button"
                              onClick={() => unequipSkill(s.id)}
                              class="text-neutral-500 hover:text-red-400 ml-0.5 transition-colors"
                            >&times;</button>
                          </span>
                        )}
                      </For>
                    </div>
                  </Show>
                  {/* Add skill — autocomplete */}
                  {(() => {
                    const [skillQuery, setSkillQuery] = createSignal("");
                    const [showSuggestions, setShowSuggestions] = createSignal(false);
                    const [skillIdx, setSkillIdx] = createSignal(-1);
                    const candidates = () => {
                      const q = skillQuery().toLowerCase();
                      if (!q) return [];
                      return allSkills()
                        .filter((s) => !equippedSkills().some((e) => e.id === s.id))
                        .filter((s) => s.id.toLowerCase().startsWith(q));
                    };
                    const addSkill = (id: string) => {
                      if (id) equipSkill(id);
                      setSkillQuery("");
                      setShowSuggestions(false);
                      setSkillIdx(-1);
                    };
                    return (
                      <div class="relative">
                        <input
                          type="text"
                          value={skillQuery()}
                          onInput={(e) => { setSkillQuery(e.currentTarget.value); setShowSuggestions(true); setSkillIdx(-1); }}
                          onFocus={() => { if (skillQuery()) { setShowSuggestions(true); setSkillIdx(-1); } }}
                          onKeyDown={(e) => {
                            const list = candidates();
                            if (e.key === "ArrowDown") {
                              e.preventDefault();
                              setSkillIdx((i) => (i < list.length - 1 ? i + 1 : 0));
                            } else if (e.key === "ArrowUp") {
                              e.preventDefault();
                              setSkillIdx((i) => (i > 0 ? i - 1 : list.length - 1));
                            } else if (e.key === "Enter") {
                              e.preventDefault();
                              if (skillIdx() >= 0 && skillIdx() < list.length) {
                                addSkill(list[skillIdx()].id);
                              } else if (list.length === 1) {
                                addSkill(list[0].id);
                              }
                            } else if (e.key === "Escape") {
                              setShowSuggestions(false);
                              setSkillIdx(-1);
                            }
                          }}
                          placeholder="Add skill…"
                          class="bg-neutral-900 border border-neutral-800 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-neutral-600 font-mono w-64"
                        />
                        <Show when={showSuggestions() && candidates().length > 0}>
                          <div
                            class="absolute z-20 mt-1 w-64 max-h-48 overflow-y-auto bg-neutral-900 border border-neutral-700 rounded-lg shadow-lg"
                            onMouseDown={(e) => e.preventDefault()}
                          >
                            <For each={candidates()}>
                              {(s, i) => (
                                <button
                                  type="button"
                                  class={`w-full text-left px-4 py-2 text-sm font-mono transition-colors ${
                                    i() === skillIdx() ? "bg-neutral-700 text-white" : "text-neutral-200 hover:bg-neutral-800"
                                  }`}
                                  onClick={() => addSkill(s.id)}
                                >
                                  {s.id}
                                </button>
                              )}
                            </For>
                          </div>
                        </Show>
                      </div>
                    );
                  })()}
                </div>

                {/* Permissions (approved / denied only) */}
                <div>
                  <label class="block text-xs font-medium text-neutral-400 mb-1.5">Permissions</label>
                  <Show when={approvals().filter((a) => a.status !== "pending").length > 0} fallback={
                    <p class="text-sm text-neutral-600">No resolved permissions</p>
                  }>
                    <div class="space-y-2">
                      <For each={approvals().filter((a) => a.status !== "pending")}>
                        {(a) => (
                          <div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-neutral-800 border border-neutral-700">
                            <span class={`w-2 h-2 rounded-full shrink-0 ${
                              a.status === "approved" ? "bg-green-500" : "bg-red-500"
                            }`} />
                            <span class="text-sm text-neutral-200 font-mono flex-1 truncate">{a.request}</span>
                            <span class="text-xs text-neutral-500 capitalize">{a.status}</span>
                            <button
                              type="button"
                              onClick={() => deleteApproval(a.id)}
                              class="px-2 py-1 text-xs rounded bg-neutral-900 text-neutral-400 border border-neutral-700 hover:text-red-400 hover:border-red-800 transition-colors shrink-0"
                            >Delete</button>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </div>

              </div>
            )}
          </Show>
        </div>

        {/* ===== Chat Panel (collapsible) ===== */}
        <div class={`shrink-0 flex flex-col border-t border-neutral-700 bg-neutral-900/30 transition-all ${chatOpen() ? "h-[50%] min-h-[200px]" : ""}`}>

          {/* Chat Toggle Header */}
          <button
            onClick={() => { setChatOpen(!chatOpen()); setTimeout(scrollToBottom, 100); }}
            class="flex items-center gap-2 px-4 py-2 bg-neutral-900/60 hover:bg-neutral-800/60 transition-colors shrink-0 w-full text-left"
          >
            <svg class={`w-3 h-3 text-neutral-400 transition-transform ${chatOpen() ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
            </svg>
            <span class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Chat</span>
            <Show when={error()}>
              <span class="text-xs text-red-400 ml-1">{error()}</span>
            </Show>
            <Show when={messages().length > 0}>
              <span class="text-[10px] text-neutral-600 ml-1">({messages().length})</span>
            </Show>
            <Show when={messages().length > 0}>
              <span
                onClick={(e) => { e.stopPropagation(); clearHistory(); }}
                class="ml-auto text-[10px] text-neutral-500 hover:text-neutral-300 transition-colors"
              >
                Clear
              </span>
            </Show>
          </button>

          {/* Chat Body — only visible when expanded */}
          <Show when={chatOpen()}>
            <div class="flex-1 min-h-0 flex flex-col">
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
                    onKeyDown={handleChatKeyDown}
                    class="flex-1 bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500/50 transition-all placeholder:text-neutral-600"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!input().trim()}
                    class={`px-4 py-2.5 rounded-xl font-medium text-sm transition-all
                      ${input().trim()
                        ? "bg-neutral-200 hover:bg-white text-neutral-900"
                        : "bg-neutral-800 text-neutral-600 cursor-not-allowed border border-neutral-700"
                      }`}
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </Show>
        </div>

      </div>
    </div>
  );
}
