import { createSignal, For } from "solid-js";

export default function Approvals() {
  const [approvals] = createSignal([
    { id: 1, agent: "Nova", task: "Execute Python script", timestamp: "2 mins ago" },
    { id: 2, agent: "DataBroker", task: "Access external API", timestamp: "1 hour ago" }
  ]);

  return (
    <div class="w-full h-full">
      <h1 class="text-3xl font-bold mb-8">Approvals</h1>
      
      <div class="space-y-4 w-full">
        <For each={approvals()} fallback={<div class="text-neutral-500">No pending approvals.</div>}>
          {(item) => (
            <div class="bg-neutral-800 p-6 rounded-xl border border-neutral-700 flex justify-between items-center w-full">
              <div>
                <div class="font-medium text-lg mb-1">{item.agent} requests permission</div>
                <div class="text-neutral-400 text-sm">{item.task} • {item.timestamp}</div>
              </div>
              <div class="flex space-x-3">
                <button class="px-4 py-2 text-red-400 hover:text-red-300 hover:bg-neutral-800 rounded-lg transition-colors">Deny</button>
                <button class="px-4 py-2 bg-green-900/40 hover:bg-green-900/60 text-green-300 rounded-lg transition-colors border border-green-800/50">Approve</button>
              </div>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
