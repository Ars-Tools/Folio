import { createSignal, createEffect, For, Show } from "solid-js";

interface AgentInfo {
  id: string;
  name: string;
  initial: string;
  hasAvatar: boolean;
  status: "active" | "inactive" | "error";
  error: string;
}

export default function Agents(props: {
  token: string;
  onLogout: () => void;
  onSelectAgent: (agentId: string) => void;
}) {
  const [agents, setAgents] = createSignal<AgentInfo[]>([]);
  const [loading, setLoading] = createSignal(true);
  const [error, setError] = createSignal("");
  const [showCreate, setShowCreate] = createSignal(false);
  const [newId, setNewId] = createSignal("");

  const headers = () => ({
    Authorization: `Bearer ${props.token}`,
    "Content-Type": "application/json",
  });

  const fetchAgents = async () => {
    try {
      const res = await fetch("/agents", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setAgents(data.agents);
      } else {
        setError("Failed to fetch agents");
        if (res.status === 401) props.onLogout();
      }
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  };

  createEffect(() => { fetchAgents(); });

  const handleCreate = async () => {
    const id = newId().trim().toLowerCase().replace(/[^a-z0-9_-]/g, "");
    if (!id) return;
    setError("");
    const res = await fetch("/agents", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ id }),
    });
    if (res.ok) {
      setNewId("");
      setShowCreate(false);
      await fetchAgents();
      props.onSelectAgent(id);
    } else {
      const d = await res.json();
      setError(d.detail || "Create failed");
    }
  };

  const avatarColors = [
    "from-violet-500 to-purple-600",
    "from-cyan-500 to-blue-600",
    "from-emerald-500 to-teal-600",
    "from-amber-500 to-orange-600",
    "from-rose-500 to-pink-600",
    "from-indigo-500 to-blue-600",
  ];

  return (
    <div class="w-full h-full">
      <div class="flex items-center justify-between mb-8">
        <h1 class="text-3xl font-bold">Agents</h1>
        <button
          onClick={() => setShowCreate(!showCreate())}
          class="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 text-neutral-100 rounded-lg transition-colors text-sm border border-neutral-600"
        >
          {showCreate() ? "Cancel" : "+ New Agent"}
        </button>
      </div>

      <Show when={error()}>
        <div class="p-3 mb-4 bg-red-900/30 border border-red-800/50 rounded-lg text-red-400 text-sm">
          {error()}
        </div>
      </Show>

      <Show when={showCreate()}>
        <div class="mb-6 bg-neutral-800 p-5 rounded-xl border border-neutral-700 space-y-4">
          <div>
            <label class="block text-xs font-medium text-neutral-400 mb-1.5">Agent ID</label>
            <div class="flex items-center gap-3">
              <input
                type="text"
                placeholder="my-agent"
                value={newId()}
                onInput={(e) => setNewId(e.currentTarget.value)}
                onKeyDown={(e) => { if (!e.isComposing && e.key === "Enter") handleCreate(); }}
                class="flex-1 bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm"
              />
              <button
                onClick={handleCreate}
                class="px-4 py-2 bg-green-900/40 hover:bg-green-900/60 text-green-300 rounded-lg transition-colors text-sm border border-green-800/50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      </Show>

      <Show when={!loading() && agents().length === 0}>
        <p class="text-neutral-500 text-sm">No agents yet. Create one to get started.</p>
      </Show>

      <Show when={loading()}>
        <p class="text-neutral-500 text-sm">Loading agents…</p>
      </Show>

      <div class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        <For each={agents()}>
          {(agent, index) => (
            <button
              onClick={() => props.onSelectAgent(agent.id)}
              class="group flex flex-col items-center gap-3 p-5 rounded-2xl bg-neutral-800/50 border border-neutral-700/50 hover:border-neutral-500 hover:bg-neutral-800 transition-all cursor-pointer"
            >
              <div class="transition-transform group-hover:scale-105 relative">
                <Show
                  when={agent.hasAvatar}
                  fallback={
                    <div
                      class={`w-20 h-20 rounded-full flex items-center justify-center text-white font-bold text-2xl bg-gradient-to-br ${avatarColors[index() % avatarColors.length]} shrink-0 shadow-lg`}
                    >
                      {agent.initial}
                    </div>
                  }
                >
                  <img
                    src={`/agent/${agent.id}/avatar`}
                    alt={agent.name}
                    class="w-20 h-20 rounded-full object-cover shrink-0 bg-neutral-700 shadow-lg"
                  />
                </Show>
                {/* Status indicator */}
                <div
                  class={`absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-neutral-800 ${
                    agent.status === "active"
                      ? "bg-green-500"
                      : agent.status === "error"
                        ? "bg-red-500"
                        : "bg-neutral-500"
                  }`}
                  title={agent.status === "error" ? agent.error : agent.status}
                />
              </div>
              <div class="text-center">
                <div class="font-medium text-white group-hover:text-blue-400 transition-colors text-sm">
                  {agent.name}
                </div>
                <div class="text-xs text-neutral-500 mt-0.5">{agent.id}</div>
                <Show when={agent.status === "error"}>
                  <div class="text-[10px] text-red-400 mt-1 max-w-[120px] truncate" title={agent.error}>{agent.error}</div>
                </Show>
              </div>
            </button>
          )}
        </For>
      </div>
    </div>
  );
}
