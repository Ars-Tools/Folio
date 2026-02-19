import { createSignal, createEffect, For, Show } from "solid-js";

export default function Agents(props: { token: string; onLogout: () => void }) {
  const [agents, setAgents] = createSignal<string[]>([]);
  const [error, setError] = createSignal("");

  createEffect(async () => {
    try {
      const response = await fetch("/api/agents", {
        headers: {
          Authorization: `Bearer ${props.token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setAgents(data.agents);
      } else {
        setError("Failed to fetch agents");
        if (response.status === 401) {
            props.onLogout();
        }
      }
    } catch (e) {
      setError("Network error");
    }
  });

  return (
    <div class="w-full h-full">
      <h1 class="text-3xl font-bold mb-8">Agents</h1>
      
      <Show when={error()}>
        <div class="p-4 mb-4 bg-red-900/50 border border-red-700 rounded-lg text-red-200 w-full">
          {error()}
        </div>
      </Show>

      <div class="bg-neutral-800 rounded-xl p-6 border border-neutral-700 w-full">
        <h2 class="text-xl font-semibold mb-4">Available Agents</h2>
        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 w-full">
          <For each={agents()} fallback={<div class="text-neutral-400">Loading agents...</div>}>
            {(agent) => (
              <div class="p-4 bg-neutral-900 rounded-lg border border-neutral-700 hover:border-neutral-500 transition-colors cursor-pointer group">
                <div class="font-medium text-lg mb-2 group-hover:text-blue-400 transition-colors">{agent}</div>
                <div class="text-sm text-neutral-400">Ready to chat</div>
              </div>
            )}
          </For>
        </div>
      </div>
    </div>
  );
}
