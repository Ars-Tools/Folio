import { createSignal, createEffect, For, Show, onMount } from "solid-js";

interface ConfigField {
  key: string;
  label: string;
  placeholder: string;
  secret: boolean;
}

interface ProviderInfo {
  id: string;
  name: string;
  kind: string;
  config: Record<string, string>;
  update: string;
}

export default function Providers(props: { token: string; onLogout: () => void }) {
  const [providers, setProviders] = createSignal<ProviderInfo[]>([]);
  const [error, setError] = createSignal("");

  // Kind metadata from server
  const [kinds, setKinds] = createSignal<string[]>([]);
  const [schemas, setSchemas] = createSignal<Record<string, ConfigField[]>>({});

  // Create form
  const [showCreate, setShowCreate] = createSignal(false);
  const [newId, setNewId] = createSignal("");
  const [newName, setNewName] = createSignal("");
  const [newKind, setNewKind] = createSignal("");
  const [newConfig, setNewConfig] = createSignal<Record<string, string>>({});

  // Edit state
  const [editId, setEditId] = createSignal<string | null>(null);
  const [editName, setEditName] = createSignal("");
  const [editKind, setEditKind] = createSignal("");
  const [editConfig, setEditConfig] = createSignal<Record<string, string>>({});

  const headers = () => ({
    Authorization: `Bearer ${props.token}`,
    "Content-Type": "application/json",
  });

  const fetchKinds = async () => {
    try {
      const res = await fetch("/providers/kinds", { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setKinds(data.kinds);
        setSchemas(data.schemas);
        if (data.kinds.length && !newKind()) setNewKind(data.kinds[0]);
      }
    } catch { /* ignore */ }
  };

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

  onMount(() => { fetchKinds(); });
  createEffect(() => { fetchProviders(); });

  // Reset config fields when kind changes in create form
  createEffect(() => {
    const k = newKind();
    const fields = schemas()[k] || [];
    const cfg: Record<string, string> = {};
    for (const f of fields) cfg[f.key] = "";
    setNewConfig(cfg);
  });

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
        config: newConfig(),
      }),
    });
    if (res.ok) {
      setNewId(""); setNewName(""); setNewConfig({});
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
    // Pre-fill with masked values from server
    setEditConfig({ ...p.config });
  };

  const cancelEdit = () => setEditId(null);

  const handleUpdate = async () => {
    const id = editId();
    if (!id) return;
    setError("");
    const res = await fetch(`/provider/${id}`, {
      method: "PUT",
      headers: headers(),
      body: JSON.stringify({
        name: editName(),
        kind: editKind(),
        config: editConfig(),
      }),
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
      "google": "bg-amber-900/60 text-amber-200 border-amber-700",
      "anthropic": "bg-orange-900/60 text-orange-200 border-orange-700",
      "xai": "bg-neutral-800/60 text-neutral-200 border-neutral-500",
    };
    return colors[kind] || "bg-neutral-700 text-neutral-300 border-neutral-600";
  };

  /** Render config fields for a given kind */
  const ConfigFields = (cfgProps: {
    kind: string;
    config: Record<string, string>;
    setConfig: (c: Record<string, string>) => void;
    placeholderOverride?: boolean; // when true, use "leave empty to keep" for secret fields
  }) => {
    const fields = () => schemas()[cfgProps.kind] || [];
    return (
      <div class="space-y-3">
        <For each={fields()}>
          {(f) => (
            <div>
              <label class="block text-xs font-medium text-neutral-400 mb-1.5">{f.label}</label>
              <input
                type={f.secret ? "password" : "text"}
                placeholder={cfgProps.placeholderOverride && f.secret ? "Leave empty to keep current" : f.placeholder}
                value={cfgProps.config[f.key] || ""}
                onInput={(e) => cfgProps.setConfig({ ...cfgProps.config, [f.key]: e.currentTarget.value })}
                onKeyDown={(e) => { if (!e.isComposing && e.key === "Enter") handleCreate(); }}
                class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm"
              />
            </div>
          )}
        </For>
      </div>
    );
  };

  /** Summarise config for list view (show non-secret values) */
  const configSummary = (kind: string, config: Record<string, string>) => {
    const fields = schemas()[kind] || [];
    const parts: string[] = [];
    for (const f of fields) {
      const v = config[f.key];
      if (!v) continue;
      parts.push(f.secret ? `${f.label}: ${v}` : `${f.label}: ${v}`);
    }
    return parts.join("  ·  ") || "—";
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
                onKeyDown={(e) => { if (!e.isComposing && e.key === "Enter") handleCreate(); }}
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
                onKeyDown={(e) => { if (!e.isComposing && e.key === "Enter") handleCreate(); }}
                class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 text-sm"
              />
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-neutral-400 mb-1.5">Type</label>
            <select
              value={newKind()}
              onChange={(e) => setNewKind(e.currentTarget.value)}
              class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-neutral-500 appearance-none"
            >
              <For each={kinds()}>
                {(k) => <option value={k}>{k}</option>}
              </For>
            </select>
          </div>
          <ConfigFields kind={newKind()} config={newConfig()} setConfig={setNewConfig} />
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
                    <div class="text-neutral-500 text-xs font-mono truncate max-w-[400px]">{configSummary(p.kind, p.config)}</div>
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
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">Name</label>
                    <input
                      type="text"
                      value={editName()}
                      onInput={(e) => setEditName(e.currentTarget.value)}
                      placeholder="Name"
                      class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-neutral-500"
                    />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-400 mb-1.5">Type</label>
                    <select
                      value={editKind()}
                      onChange={(e) => {
                        setEditKind(e.currentTarget.value);
                        // Reset config when kind changes during edit
                        const fields = schemas()[e.currentTarget.value] || [];
                        const cfg: Record<string, string> = {};
                        for (const f of fields) cfg[f.key] = "";
                        setEditConfig(cfg);
                      }}
                      class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-neutral-500 appearance-none"
                    >
                      <For each={kinds()}>
                        {(k) => <option value={k}>{k}</option>}
                      </For>
                    </select>
                  </div>
                </div>
                <ConfigFields kind={editKind()} config={editConfig()} setConfig={setEditConfig} placeholderOverride />
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
