import { createSignal, createEffect, For, Show } from "solid-js";

interface AgentInfo {
  id: string;
  name: string;
  initial: string;
  hasAvatar: boolean;
}

export default function Agents(props: {
  token: string;
  onLogout: () => void;
  onSelectAgent: (agentId: string) => void;
}) {
  const [agents, setAgents] = createSignal<AgentInfo[]>([]);
  const [error, setError] = createSignal("");

  createEffect(async () => {
    try {
      const res = await fetch("/agents", {
        headers: { Authorization: `Bearer ${props.token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAgents(data.agents);
      } else {
        setError("Failed to fetch agents");
        if (res.status === 401) props.onLogout();
      }
    } catch {
      setError("Network error");
    }
  });

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
      <h1 class="text-3xl font-bold mb-8">Agents</h1>

      <Show when={error()}>
        <div class="p-4 mb-4 bg-red-900/50 border border-red-700 rounded-lg text-red-200 w-full">
          {error()}
        </div>
      </Show>

      <div class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        <For each={agents()} fallback={<div class="text-neutral-400 col-span-full">Loading agents...</div>}>
          {(agent, index) => (
            <button
              onClick={() => props.onSelectAgent(agent.id)}
              class="group flex flex-col items-center gap-3 p-5 rounded-2xl bg-neutral-800/50 border border-neutral-700/50 hover:border-neutral-500 hover:bg-neutral-800 transition-all cursor-pointer"
            >
              <div class="transition-transform group-hover:scale-105">
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
              </div>
              <div class="text-center">
                <div class="font-medium text-white group-hover:text-blue-400 transition-colors text-sm">
                  {agent.name}
                </div>
                <div class="text-xs text-neutral-500 mt-0.5">{agent.id}</div>
              </div>
            </button>
          )}
        </For>
      </div>
    </div>
  );
}
