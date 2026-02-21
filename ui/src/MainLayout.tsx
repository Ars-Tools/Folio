import { createSignal, onCleanup, Switch, Match } from "solid-js";
import Dashboard from "./Dashboard";
import Agents from "./Agents";
import AgentDetail from "./AgentDetail";
import Timeline from "./Timeline";
import Sessions from "./Sessions";
import Approvals from "./Approvals";
import Skills from "./Skills";
import Tokens from "./Tokens";
import Providers from "./Providers";

type Page = "dashboard" | "timeline" | "sessions" | "agents" | "approvals" | "skills" | "tokens" | "providers" | "agent-detail";

const validPages: Page[] = ["dashboard", "timeline", "sessions", "agents", "approvals", "skills", "tokens", "providers", "agent-detail"];

/** Parse hash like #agents or #agent-detail/nova */
function parseHash(): { page: Page; agentId: string } {
  const raw = window.location.hash.replace(/^#\/?/, "");
  if (raw.startsWith("agent-detail/")) {
    const agentId = raw.slice("agent-detail/".length);
    return { page: "agent-detail", agentId };
  }
  const page = validPages.includes(raw as Page) ? (raw as Page) : "dashboard";
  return { page, agentId: "" };
}

function setHash(page: Page, agentId?: string) {
  const hash = page === "agent-detail" && agentId ? `agent-detail/${agentId}` : page;
  window.location.hash = hash;
}

interface MainLayoutProps {
  token: string;
  onLogout: () => void;
}

export default function MainLayout(props: MainLayoutProps) {
  const initial = parseHash();
  const [activePage, setActivePage] = createSignal<Page>(initial.page);
  const [selectedAgentId, setSelectedAgentId] = createSignal<string>(initial.agentId);

  // Sync hash → state on popstate / hashchange
  const onHashChange = () => {
    const { page, agentId } = parseHash();
    setActivePage(page);
    if (agentId) setSelectedAgentId(agentId);
  };
  window.addEventListener("hashchange", onHashChange);
  onCleanup(() => window.removeEventListener("hashchange", onHashChange));

  const navigate = (page: Page) => {
    setHash(page);
    setActivePage(page);
  };

  const openAgent = (agentId: string) => {
    setSelectedAgentId(agentId);
    setHash("agent-detail", agentId);
    setActivePage("agent-detail");
  };

  const NavItem = (p: { page: Page; label: string }) => (
    <button
      onClick={() => navigate(p.page)}
      class={`w-full text-left px-4 py-2 rounded-lg transition-colors mb-1 ${activePage() === p.page
        ? "bg-neutral-800 text-white font-medium"
        : "text-neutral-400 hover:bg-neutral-800/50 hover:text-neutral-200"
        }`}
    >
      {p.label}
    </button>
  );

  return (
    <div class="flex h-screen bg-neutral-900 text-white font-sans overflow-hidden">
      {/* Sidebar */}
      <aside class="w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col">
        <div class="p-6 border-b border-neutral-800">
          <h1 class="text-xl font-bold tracking-tight">FOLIO</h1>
        </div>

        <nav class="flex-1 p-4 overflow-y-auto">
          <div class="mb-6">
            <h2 class="px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
              Operator
            </h2>
            <NavItem page="dashboard" label="Dashboard" />
            <NavItem page="approvals" label="Pending" />
          </div>

          <div class="mb-6">
            <h2 class="px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
              Platform
            </h2>
            <NavItem page="timeline" label="Timeline" />
            <NavItem page="sessions" label="Session" />
          </div>

          <div>
            <h2 class="px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
              Management
            </h2>
            <NavItem page="agents" label="Agents" />
            <NavItem page="skills" label="Skills" />
            <NavItem page="providers" label="Providers" />
            <NavItem page="tokens" label="Tokens" />
          </div>
        </nav>

        <div class="p-4 border-t border-neutral-800">
          <div class="flex items-center justify-between px-4 py-2">
            <div class="flex items-center space-x-2">
              <div class="w-2 h-2 rounded-full bg-green-500"></div>
              <span class="text-xs text-neutral-400">Connected</span>
            </div>
            <button
              onClick={props.onLogout}
              class="text-xs text-red-400 hover:text-red-300 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main class="flex-1 overflow-hidden bg-neutral-900/50 flex flex-col">
        <Switch>
          <Match when={activePage() === "agent-detail"}>
            <AgentDetail
              token={props.token}
              agentId={selectedAgentId()}
              onLogout={props.onLogout}
              onBack={() => navigate("agents")}
            />
          </Match>
          <Match when={true}>
            <div class="w-full h-full p-8 overflow-auto">
              <Switch>
                <Match when={activePage() === "dashboard"}>
                  <Dashboard />
                </Match>
                <Match when={activePage() === "timeline"}>
                  <Timeline token={props.token} />
                </Match>
                <Match when={activePage() === "sessions"}>
                  <Sessions />
                </Match>
                <Match when={activePage() === "approvals"}>
                  <Approvals />
                </Match>
                <Match when={activePage() === "agents"}>
                  <Agents token={props.token} onLogout={props.onLogout} onSelectAgent={openAgent} />
                </Match>
                <Match when={activePage() === "skills"}>
                  <Skills token={props.token} onLogout={props.onLogout} />
                </Match>
                <Match when={activePage() === "tokens"}>
                  <Tokens token={props.token} onLogout={props.onLogout} />
                </Match>
                <Match when={activePage() === "providers"}>
                  <Providers token={props.token} onLogout={props.onLogout} />
                </Match>
              </Switch>
            </div>
          </Match>
        </Switch>
      </main>
    </div>
  );
}
