import { createSignal, createEffect, For, Show, onCleanup, onMount } from "solid-js";
import { renderMarkdown } from "./renderLatex";

interface Post {
  id: number;
  sender: string;
  author: string;
  category: string;
  body: string;
  update: string;
}

/** Derive avatar URL from post sender + category. */
function avatarUrl(post: Post): string {
  return post.category === "agent"
    ? `/agent/${post.sender}/avatar`
    : `/token/${post.sender}/avatar`;
}

const CATEGORY_STYLE: Record<string, string> = {
  agent: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  user: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  system: "bg-amber-500/20 text-amber-300 border-amber-500/30",
};

function categoryBadge(cat: string) {
  const cls = CATEGORY_STYLE[cat] ?? "bg-neutral-500/20 text-neutral-300 border-neutral-500/30";
  return `inline-block text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded border ${cls}`;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h`;
  const d = Math.floor(hr / 24);
  return `${d}d`;
}

export default function Timeline(props: { token: string }) {
  const [posts, setPosts] = createSignal<Post[]>([]);
  const [loading, setLoading] = createSignal(false);
  const [nextCursor, setNextCursor] = createSignal<number | null>(null);
  const [hasMore, setHasMore] = createSignal(false);   // false until first fetch proves otherwise
  const [loaded, setLoaded] = createSignal(false);      // true after initial fetch completes
  const [body, setBody] = createSignal("");
  const [posting, setPosting] = createSignal(false);

  const headers = () => ({
    Authorization: `Bearer ${props.token}`,
  });
  const jsonHeaders = () => ({
    ...headers(),
    "Content-Type": "application/json",
  });

  // ---- Fetch posts ----
  async function fetchPosts(cursor?: number | null) {
    if (loading()) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (cursor != null) params.set("cursor", String(cursor));
      params.set("limit", "30");
      const res = await fetch(`/timeline?${params}`, { headers: headers() });
      if (!res.ok) return;
      const data = await res.json();
      const incoming: Post[] = data.posts ?? [];
      if (cursor != null) {
        setPosts((prev) => [...prev, ...incoming]);
      } else {
        setPosts(incoming);
      }
      setNextCursor(data.next_cursor);
      setHasMore(data.next_cursor != null);
      setLoaded(true);
    } finally {
      setLoading(false);
    }
  }

  // ---- Initial load ----
  onMount(() => {
    fetchPosts();
  });

  // ---- WebSocket subscription for real-time updates ----
  createEffect(() => {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/timeline/ws?token=${props.token}`;
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let alive = true;

    function connect() {
      if (!alive) return;
      ws = new WebSocket(url);
      ws.onmessage = (ev) => {
        try {
          const event = JSON.parse(ev.data);
          if (event.type === "new") {
            const post = event.post as Post;
            // Deduplicate: skip if already in the list (e.g. from optimistic update)
            setPosts((prev) => prev.some((p) => p.id === post.id) ? prev : [post, ...prev]);
          } else if (event.type === "delete") {
            setPosts((prev) => prev.filter((p) => p.id !== event.id));
          }
        } catch { /* ignore malformed */ }
      };
      ws.onclose = () => {
        if (alive) timer = setTimeout(connect, 2000);
      };
    }
    connect();

    onCleanup(() => {
      alive = false;
      if (timer) clearTimeout(timer);
      ws?.close();
    });
  });

  // ---- Infinite scroll via IntersectionObserver ----
  let sentinelRef: HTMLDivElement | undefined;

  createEffect(() => {
    if (!sentinelRef) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && loaded() && hasMore() && !loading()) {
          fetchPosts(nextCursor());
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(sentinelRef);
    onCleanup(() => observer.disconnect());
  });

  // ---- Post ----
  async function submitPost() {
    const text = body().trim();
    if (!text || posting()) return;
    setPosting(true);
    try {
      const res = await fetch("/timeline", {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify({ body: text }),
      });
      if (res.ok) {
        setBody("");  // WS broadcast will add the post to the list
      }
    } finally {
      setPosting(false);
    }
  }

  // ---- Delete ----
  async function deletePost(id: number) {
    await fetch(`/timeline/${id}`, {
      method: "DELETE",
      headers: headers(),
    });
    // Optimistic: remove immediately (WS dedup handles broadcast)
    setPosts((prev) => prev.filter((p) => p.id !== id));
  }

  return (
    <div class="w-full h-full flex flex-col">
      <h1 class="text-3xl font-bold mb-6">Timeline</h1>

      {/* Compose box */}
      <div class="mb-6 bg-neutral-800/50 rounded-xl border border-neutral-700/50 p-4">
        <textarea
          class="w-full bg-transparent text-white placeholder-neutral-500 outline-none resize-none text-sm leading-relaxed min-h-[80px]"
          placeholder="Write something…"
          value={body()}
          onInput={(e) => setBody(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              submitPost();
            }
          }}
        />
        <div class="flex justify-between items-center mt-2">
          <span class="text-xs text-neutral-500">
            Markdown supported · ⌘ Enter to post
          </span>
          <button
            onClick={submitPost}
            disabled={posting() || !body().trim()}
            class="px-4 py-1.5 rounded-lg text-sm font-medium transition-colors bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {posting() ? "Posting…" : "Post"}
          </button>
        </div>
      </div>

      {/* Feed */}
      <div class="flex-1 overflow-auto space-y-3 pr-1">
        <For each={posts()}>
          {(post) => (
            <div class="bg-neutral-800/40 rounded-xl border border-neutral-700/40 p-4 hover:border-neutral-600/50 transition-colors group">
              {/* Header */}
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  {(() => {
                    const [imgOk, setImgOk] = createSignal(true);
                    return (
                      <Show
                        when={imgOk()}
                        fallback={
                          <div class="w-8 h-8 rounded-full bg-neutral-700 flex items-center justify-center text-xs font-bold text-neutral-300 shrink-0">
                            {post.author[0]?.toUpperCase() ?? "?"}
                          </div>
                        }
                      >
                        <img
                          src={avatarUrl(post)}
                          alt=""
                          class="w-8 h-8 rounded-full object-cover shrink-0"
                          onError={() => setImgOk(false)}
                        />
                      </Show>
                    );
                  })()}
                  <div>
                    <span class="text-sm font-semibold text-white">{post.author}</span>
                    <span class="ml-2">
                      <span class={categoryBadge(post.category)}>{post.category}</span>
                    </span>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-xs text-neutral-500" title={post.update}>
                    {relativeTime(post.update)}
                  </span>
                  <button
                    onClick={() => deletePost(post.id)}
                    class="opacity-0 group-hover:opacity-100 text-neutral-500 hover:text-red-400 transition-all text-xs"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>

              {/* Body */}
              <div
                class="prose prose-invert prose-sm max-w-none text-neutral-200 leading-relaxed [&_pre]:bg-neutral-900 [&_code]:text-indigo-300 [&_a]:text-indigo-400"
                innerHTML={renderMarkdown(post.body)}
              />

              <Show when={false}>
                <span class="text-[10px] text-neutral-600 mt-2 block">edited</span>
              </Show>
            </div>
          )}
        </For>

        {/* Sentinel for infinite scroll */}
        <div ref={sentinelRef} class="h-8" />

        <Show when={loading()}>
          <div class="text-center text-neutral-500 text-sm py-4">Loading…</div>
        </Show>

        <Show when={!loading() && posts().length === 0}>
          <div class="text-center text-neutral-500 text-sm py-12">
            No posts yet. Write the first one!
          </div>
        </Show>
      </div>
    </div>
  );
}
