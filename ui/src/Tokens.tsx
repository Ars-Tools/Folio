import { createSignal, createEffect, For, Show } from "solid-js";

interface TokenInfo {
  id: string;
  full_id: string;
  name: string;
  kind: string;
  update: string;
}

const TOKEN_KINDS = ["user", "node", "service"] as const;

export default function Tokens(props: { token: string; onLogout: () => void }) {
  const [tokens, setTokens] = createSignal<TokenInfo[]>([]);
  const [error, setError] = createSignal("");
  const [showCreate, setShowCreate] = createSignal(false);
  const [createdToken, setCreatedToken] = createSignal("");
  const [copied, setCopied] = createSignal(false);
  const [newName, setNewName] = createSignal("");
  const [newKind, setNewKind] = createSignal<string>("node");

  const headers = () => ({
    Authorization: `Bearer ${props.token}`,
    "Content-Type": "application/json",
  });

  const fetchTokens = async () => {
    try {
      const res = await fetch("/tokens", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setTokens(data.tokens);
      } else if (res.status === 401) {
        props.onLogout();
      }
    } catch {
      setError("Failed to fetch tokens");
    }
  };

  createEffect(() => { fetchTokens(); });

  const handleCreate = async () => {
    if (!newName().trim()) return;
    const res = await fetch("/tokens", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ name: newName().trim(), kind: newKind() }),
    });
    if (res.ok) {
      const d = await res.json();
      setCreatedToken(d.id);
      setNewName("");
      setNewKind("node");
      fetchTokens();
    } else {
      const d = await res.json();
      setError(d.detail || "Create failed");
    }
  };

  const handleDelete = async (fullId: string) => {
    const res = await fetch(`/token/${fullId}`, {
      method: "DELETE",
      headers: headers(),
    });
    if (res.ok) fetchTokens();
  };

  const kindBadge = (kind: string) => {
    const colors: Record<string, string> = {
      user: "bg-blue-900/60 text-blue-200 border-blue-700",
      node: "bg-amber-900/60 text-amber-200 border-amber-700",
      service: "bg-purple-900/60 text-purple-200 border-purple-700",
    };
    return colors[kind] || "bg-neutral-700 text-neutral-300 border-neutral-600";
  };

  return (
    <div class="w-full h-full">
      <div class="flex items-center justify-between mb-8">
        <h1 class="text-3xl font-bold">Tokens</h1>
        <button
          onClick={() => setShowCreate(!showCreate())}
          class="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 text-neutral-100 rounded-lg transition-colors text-sm border border-neutral-600"
        >
          {showCreate() ? "Cancel" : "+ New Token"}
        </button>
      </div>

      <Show when={error()}>
        <div class="mb-4 p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-200 text-sm">{error()}</div>
      </Show>

      {/* Created token display */}
      <Show when={createdToken()}>
        <div class="mb-4 p-4 bg-neutral-800 border border-neutral-700 rounded-xl space-y-3">
          <div class="text-sm text-neutral-300 font-medium">Token created — copy it now, it won't be shown again:</div>
          <div class="flex items-center space-x-2">
            <code class="flex-1 bg-neutral-900 rounded-lg px-4 py-2 text-sm font-mono text-white select-all break-all">{createdToken()}</code>
            <button
              onClick={() => {
                navigator.clipboard.writeText(createdToken());
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
              }}
              class={`flex-shrink-0 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                copied()
                  ? "bg-neutral-200 text-neutral-900"
                  : "bg-neutral-700 hover:bg-neutral-600 text-neutral-200"
              }`}
            >
              {copied() ? "Copied!" : "Copy"}
            </button>
          </div>
          <button onClick={() => { setCreatedToken(""); setCopied(false); }} class="text-xs text-neutral-400 hover:text-neutral-200 transition-colors">Dismiss</button>
        </div>
      </Show>

      {/* Create form */}
      <Show when={showCreate()}>
        <div class="mb-6 bg-neutral-800 p-6 rounded-xl border border-neutral-700 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-neutral-400 mb-1.5">Name</label>
              <input
                type="text"
                placeholder="Display name"
                value={newName()}
                onInput={(e) => setNewName(e.currentTarget.value)}
                class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 text-sm"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-400 mb-1.5">Type</label>
              <select
                value={newKind()}
                onChange={(e) => setNewKind(e.currentTarget.value)}
                class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-neutral-500"
              >
                <For each={[...TOKEN_KINDS]}>
                  {(k) => <option value={k}>{k}</option>}
                </For>
              </select>
            </div>
          </div>
          <button
            onClick={handleCreate}
            class="px-4 py-2 bg-green-900/40 hover:bg-green-900/60 text-green-300 rounded-lg transition-colors text-sm border border-green-800/50"
          >
            Create
          </button>
        </div>
      </Show>

      {/* Token list */}
      <div class="space-y-3 w-full">
        <For each={tokens()} fallback={<div class="text-neutral-500">No tokens registered.</div>}>
          {(tk) => (
            <div class="bg-neutral-800 p-5 rounded-xl border border-neutral-700 flex items-center justify-between">
              <div class="flex items-center space-x-4 min-w-0">
                <span class={`px-2.5 py-1 text-xs font-medium rounded-md border ${kindBadge(tk.kind)}`}>{tk.kind}</span>
                <div class="min-w-0">
                  <div class="font-medium truncate">{tk.name}</div>
                  <div class="text-neutral-500 text-xs font-mono mt-0.5">{tk.id}</div>
                </div>
              </div>
              <div class="flex items-center space-x-4 flex-shrink-0">
                <span class="text-neutral-500 text-xs">{new Date(tk.update).toLocaleString()}</span>
                <button
                  onClick={() => handleDelete(tk.full_id)}
                  class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-neutral-800 rounded-lg transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
