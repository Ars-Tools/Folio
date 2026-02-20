import { createSignal, createEffect, For, Show } from "solid-js";

interface ProviderInfo {
  id: string;
  name: string;
  kind: string;
  endpoint: string;
  apikey_masked: string;
  update: string;
}

const PROVIDER_KINDS = ["openai-responses", "openai-chat", "anthropic", "google", "custom"] as const;

export default function Providers(props: { token: string; onLogout: () => void }) {
  const [providers, setProviders] = createSignal<ProviderInfo[]>([]);
  const [error, setError] = createSignal("");

  // Create form
  const [showCreate, setShowCreate] = createSignal(false);
  const [newId, setNewId] = createSignal("");
  const [newName, setNewName] = createSignal("");
  const [newKind, setNewKind] = createSignal("openai-responses");
  const [newEndpoint, setNewEndpoint] = createSignal("");
  const [newApikey, setNewApikey] = createSignal("");

  // Edit state
  const [editId, setEditId] = createSignal<string | null>(null);
  const [editName, setEditName] = createSignal("");
  const [editKind, setEditKind] = createSignal("");
  const [editEndpoint, setEditEndpoint] = createSignal("");
  const [editApikey, setEditApikey] = createSignal("");

  const headers = () => ({
    Authorization: `Bearer ${props.token}`,
    "Content-Type": "application/json",
  });

  const fetchProviders = async () => {
    try {
      const res = await fetch("/providers", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setProviders(data.providers);
      } else if (res.status === 401) {
        props.onLogout();
      }
    } catch {
      setError("Failed to fetch providers");
    }
  };

  createEffect(() => { fetchProviders(); });

  const handleCreate = async () => {
    if (!newId().trim()) return;
    setError("");
    const res = await fetch("/providers", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        id: newId().trim(),
        name: newName().trim() || newId().trim(),
        kind: newKind(),
        endpoint: newEndpoint().trim(),
        apikey: newApikey(),
      }),
    });
    if (res.ok) {
      setNewId(""); setNewName(""); setNewKind("openai-responses"); setNewEndpoint(""); setNewApikey("");
      setShowCreate(false);
      fetchProviders();
    } else {
      const d = await res.json();
      setError(d.detail || "Create failed");
    }
  };

  const startEdit = (p: ProviderInfo) => {
    setEditId(p.id);
    setEditName(p.name);
    setEditKind(p.kind);
    setEditEndpoint(p.endpoint);
    setEditApikey("");
  };

  const cancelEdit = () => setEditId(null);

  const handleUpdate = async () => {
    const id = editId();
    if (!id) return;
    setError("");
    const body: Record<string, string> = {
      name: editName(),
      kind: editKind(),
      endpoint: editEndpoint(),
    };
    if (editApikey()) body.apikey = editApikey();
    const res = await fetch(`/provider/${id}`, {
      method: "PUT",
      headers: headers(),
      body: JSON.stringify(body),
    });
    if (res.ok) {
      setEditId(null);
      fetchProviders();
    } else {
      const d = await res.json();
      setError(d.detail || "Update failed");
    }
  };

  const handleDelete = async (id: string) => {
    setError("");
    const res = await fetch(`/provider/${id}`, {
      method: "DELETE",
      headers: headers(),
    });
    if (res.ok) {
      fetchProviders();
    } else {
      const d = await res.json();
      setError(d.detail || "Delete failed");
    }
  };

  const kindBadge = (kind: string) => {
    const colors: Record<string, string> = {
      "openai-responses": "bg-emerald-900/60 text-emerald-200 border-emerald-700",
      "openai-chat": "bg-blue-900/60 text-blue-200 border-blue-700",
      "anthropic": "bg-amber-900/60 text-amber-200 border-amber-700",
      "google": "bg-cyan-900/60 text-cyan-200 border-cyan-700",
      "custom": "bg-neutral-700 text-neutral-300 border-neutral-600",
    };
    return colors[kind] || "bg-neutral-700 text-neutral-300 border-neutral-600";
  };

  return (
    <div class="w-full h-full">
      <div class="flex items-center justify-between mb-8">
        <h1 class="text-3xl font-bold">Providers</h1>
        <button
          onClick={() => setShowCreate(!showCreate())}
          class="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 text-neutral-100 rounded-lg transition-colors text-sm border border-neutral-600"
        >
          {showCreate() ? "Cancel" : "+ New Provider"}
        </button>
      </div>

      <Show when={error()}>
        <div class="mb-4 p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-200 text-sm">
          {error()}
          <button onClick={() => setError("")} class="ml-3 text-red-400 hover:text-red-200 text-xs">Dismiss</button>
        </div>
      </Show>

      {/* Create form */}
      <Show when={showCreate()}>
        <div class="mb-6 bg-neutral-800 p-6 rounded-xl border border-neutral-700 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-neutral-400 mb-1.5">Provider ID</label>
              <input
                type="text"
                placeholder="e.g. openai"
                value={newId()}
                onInput={(e) => setNewId(e.currentTarget.value)}
                class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm"
              />
            </div>
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
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-neutral-400 mb-1.5">Type</label>
              <select
                value={newKind()}
                onChange={(e) => setNewKind(e.currentTarget.value)}
                class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 appearance-none"
              >
                <For each={[...PROVIDER_KINDS]}>
                  {(k) => <option value={k}>{k}</option>}
                </For>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-400 mb-1.5">Endpoint</label>
              <input
                type="text"
                placeholder="https://api.openai.com/v1"
                value={newEndpoint()}
                onInput={(e) => setNewEndpoint(e.currentTarget.value)}
                class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm"
              />
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-neutral-400 mb-1.5">API Key</label>
            <input
              type="password"
              placeholder="sk-..."
              value={newApikey()}
              onInput={(e) => setNewApikey(e.currentTarget.value)}
              class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm"
            />
          </div>
          <button
            onClick={handleCreate}
            class="px-4 py-2 bg-green-900/40 hover:bg-green-900/60 text-green-300 rounded-lg transition-colors text-sm border border-green-800/50"
          >
            Create
          </button>
        </div>
      </Show>

      {/* Provider list */}
      <div class="space-y-3 w-full">
        <For each={providers()} fallback={<div class="text-neutral-500">No providers registered.</div>}>
          {(p) => (
            <Show
              when={editId() === p.id}
              fallback={
                <div class="bg-neutral-800 p-5 rounded-xl border border-neutral-700 flex items-center justify-between">
                  <div class="flex items-center space-x-4 min-w-0">
                    <span class={`px-2.5 py-1 text-xs font-medium rounded-md border shrink-0 ${kindBadge(p.kind)}`}>{p.kind}</span>
                    <div class="min-w-0">
                      <div class="font-medium truncate">{p.name}</div>
                      <div class="text-neutral-500 text-xs font-mono mt-0.5">{p.id}</div>
                    </div>
                    <div class="text-neutral-500 text-xs font-mono truncate max-w-[300px]">{p.endpoint || "—"}</div>
                    <div class="text-neutral-600 text-xs font-mono">{p.apikey_masked}</div>
                  </div>
                  <div class="flex items-center space-x-3 flex-shrink-0">
                    <span class="text-neutral-500 text-xs">{new Date(p.update).toLocaleString()}</span>
                    <button
                      onClick={() => startEdit(p)}
                      class="px-3 py-1.5 text-sm text-neutral-400 hover:text-neutral-200 hover:bg-neutral-700 rounded-lg transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(p.id)}
                      class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-neutral-800 rounded-lg transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              }
            >
              {/* Edit inline */}
              <div class="bg-neutral-800 p-5 rounded-xl border border-neutral-600 space-y-4">
                <div class="flex items-center gap-2 mb-2">
                  <span class="text-xs text-neutral-400 font-mono">{p.id}</span>
                  <span class="text-xs text-neutral-500">— editing</span>
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <input
                    type="text"
                    value={editName()}
                    onInput={(e) => setEditName(e.currentTarget.value)}
                    placeholder="Name"
                    class="bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-neutral-500"
                  />
                  <select
                    value={editKind()}
                    onChange={(e) => setEditKind(e.currentTarget.value)}
                    class="bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-neutral-500 appearance-none"
                  >
                    <For each={[...PROVIDER_KINDS]}>
                      {(k) => <option value={k}>{k}</option>}
                    </For>
                  </select>
                </div>
                <input
                  type="text"
                  value={editEndpoint()}
                  onInput={(e) => setEditEndpoint(e.currentTarget.value)}
                  placeholder="Endpoint URL"
                  class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white font-mono text-sm focus:outline-none focus:border-neutral-500"
                />
                <input
                  type="password"
                  value={editApikey()}
                  onInput={(e) => setEditApikey(e.currentTarget.value)}
                  placeholder="New API Key (leave empty to keep current)"
                  class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white font-mono text-sm focus:outline-none focus:border-neutral-500"
                />
                <div class="flex items-center gap-3">
                  <button
                    onClick={handleUpdate}
                    class="px-4 py-2 bg-neutral-200 hover:bg-white text-neutral-900 rounded-lg transition-colors text-sm font-medium"
                  >
                    Save
                  </button>
                  <button
                    onClick={cancelEdit}
                    class="px-4 py-2 text-neutral-400 hover:text-neutral-200 text-sm transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </Show>
          )}
        </For>
      </div>
    </div>
  );
}
