import { createSignal, createEffect, For, Show } from "solid-js";

interface SkillSummary {
  id: string;
  update: string;
}

export default function Skills(props: { token: string; onLogout: () => void }) {
  const [skills, setSkills] = createSignal<SkillSummary[]>([]);
  const [error, setError] = createSignal("");
  const [search, setSearch] = createSignal("");
  const [expanded, setExpanded] = createSignal<string | null>(null);
  const [loadedBody, setLoadedBody] = createSignal<Record<string, string>>({});
  const [editing, setEditing] = createSignal<string | null>(null);
  const [editBody, setEditBody] = createSignal("");
  const [newId, setNewId] = createSignal("");
  const [newBody, setNewBody] = createSignal("");
  const [showCreate, setShowCreate] = createSignal(false);

  const headers = () => ({
    Authorization: `Bearer ${props.token}`,
    "Content-Type": "application/json",
  });

  const fetchSkills = async () => {
    try {
      const q = search().trim();
      const url = q ? `/skills?q=${encodeURIComponent(q)}` : "/skills";
      const res = await fetch(url, { headers: headers() });
      if (res.ok) {
        const data = await res.json();
        setSkills(data.skills);
      } else if (res.status === 401) {
        props.onLogout();
      }
    } catch {
      setError("Failed to fetch skills");
    }
  };

  createEffect(() => { fetchSkills(); });

  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  const onSearchInput = (v: string) => {
    setSearch(v);
    clearTimeout(searchTimer);
    searchTimer = setTimeout(fetchSkills, 300);
  };

  const fetchBody = async (id: string) => {
    if (loadedBody()[id] !== undefined) return loadedBody()[id];
    const res = await fetch(`/skill/${id}`, { headers: headers() });
    if (res.ok) {
      const data = await res.json();
      setLoadedBody((prev) => ({ ...prev, [id]: data.body }));
      return data.body as string;
    }
    return "";
  };

  const toggleExpand = async (id: string) => {
    if (expanded() === id) {
      setExpanded(null);
      setEditing(null);
      return;
    }
    await fetchBody(id);
    setExpanded(id);
    setEditing(null);
  };

  const handleCreate = async () => {
    if (!newId().trim() || !newBody().trim()) return;
    const res = await fetch("/skills", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ id: newId().trim(), body: newBody() }),
    });
    if (res.ok) {
      setNewId("");
      setNewBody("");
      setShowCreate(false);
      fetchSkills();
    } else {
      const d = await res.json();
      setError(d.detail || "Create failed");
    }
  };

  const handleUpdate = async (id: string) => {
    const res = await fetch(`/skill/${id}`, {
      method: "PUT",
      headers: headers(),
      body: JSON.stringify({ body: editBody() }),
    });
    if (res.ok) {
      setEditing(null);
      setLoadedBody((prev) => ({ ...prev, [id]: editBody() }));
      fetchSkills();
    }
  };

  const handleDelete = async (id: string) => {
    const res = await fetch(`/skill/${id}`, {
      method: "DELETE",
      headers: headers(),
    });
    if (res.ok) fetchSkills();
  };

  return (
    <div class="w-full h-full">
      <div class="flex items-center justify-between mb-8">
        <h1 class="text-3xl font-bold">Skills</h1>
        <button
          onClick={() => setShowCreate(!showCreate())}
          class="px-4 py-2 bg-neutral-700 hover:bg-neutral-600 text-neutral-100 rounded-lg transition-colors text-sm border border-neutral-600"
        >
          {showCreate() ? "Cancel" : "+ New Skill"}
        </button>
      </div>

      {/* Search */}
      <div class="mb-6">
        <input
          type="text"
          placeholder="Search skills by name..."
          value={search()}
          onInput={(e) => onSearchInput(e.currentTarget.value)}
          class="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-4 py-2.5 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm"
        />
      </div>

      <Show when={error()}>
        <div class="mb-4 p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-200 text-sm">{error()}</div>
      </Show>

      {/* Create form */}
      <Show when={showCreate()}>
        <div class="mb-6 bg-neutral-800 p-6 rounded-xl border border-neutral-700 space-y-4">
          <div>
            <label class="block text-xs font-medium text-neutral-400 mb-1.5">Skill ID</label>
            <input
              type="text"
              placeholder="e.g. summarize"
              value={newId()}
              onInput={(e) => setNewId(e.currentTarget.value)}
              onKeyDown={(e) => { if (!e.isComposing && e.key === "Enter") handleCreate(); }}
              class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-neutral-400 mb-1.5">Body</label>
            <textarea
              placeholder="Skill body (prompt / instructions)..."
              value={newBody()}
              onInput={(e) => setNewBody(e.currentTarget.value)}
              rows={6}
              class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white placeholder-neutral-500 focus:outline-none focus:border-neutral-500 font-mono text-sm resize-y"
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

      {/* Skill list */}
      <div class="space-y-4 w-full">
        <For each={skills()} fallback={<div class="text-neutral-500">No skills registered.</div>}>
          {(skill) => (
            <div class="bg-neutral-800 rounded-xl border border-neutral-700 overflow-hidden">
              <div
                class="flex items-center justify-between p-5 cursor-pointer hover:bg-neutral-750"
                onClick={() => toggleExpand(skill.id)}
              >
                <div>
                  <div class="font-mono font-medium text-lg">{skill.id}</div>
                  <div class="text-neutral-500 text-xs mt-1">Updated: {new Date(skill.update).toLocaleString()}</div>
                </div>
                <div class="flex items-center space-x-2">
                  <span class="text-neutral-500 text-sm">{expanded() === skill.id ? "▼" : "▶"}</span>
                </div>
              </div>

              {/* Expanded body / Edit */}
              <Show when={expanded() === skill.id}>
                <div class="px-5 pb-5">
                  <div class="flex space-x-2 mb-3">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (editing() === skill.id) {
                          setEditing(null);
                        } else {
                          setEditing(skill.id);
                          setEditBody(loadedBody()[skill.id] || "");
                        }
                      }}
                      class="px-3 py-1.5 text-sm bg-neutral-700 hover:bg-neutral-600 rounded-lg transition-colors"
                    >
                      {editing() === skill.id ? "Cancel" : "Edit"}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(skill.id); }}
                      class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-neutral-800 rounded-lg transition-colors"
                    >
                      Delete
                    </button>
                  </div>

                  <Show when={editing() === skill.id} fallback={
                    <pre class="text-sm text-neutral-400 whitespace-pre-wrap font-mono bg-neutral-900 rounded-lg p-4 max-h-80 overflow-auto">{loadedBody()[skill.id] || ""}</pre>
                  }>
                    <div class="space-y-3">
                      <textarea
                        value={editBody()}
                        onInput={(e) => setEditBody(e.currentTarget.value)}
                        rows={12}
                        class="w-full bg-neutral-900 border border-neutral-600 rounded-lg px-4 py-2 text-white font-mono text-sm resize-y focus:outline-none focus:border-neutral-500"
                      />
                      <button
                        onClick={() => handleUpdate(skill.id)}
                        class="px-4 py-2 bg-neutral-200 hover:bg-white text-neutral-900 rounded-lg transition-colors text-sm font-medium"
                      >
                        Save
                      </button>
                    </div>
                  </Show>
                </div>
              </Show>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
