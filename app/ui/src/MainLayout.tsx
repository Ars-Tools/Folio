import { createSignal, Switch, Match } from "solid-js";
import Dashboard from "./Dashboard";
import Agents from "./Agents";
import Timeline from "./Timeline";
import Sessions from "./Sessions";
import Settings from "./Settings";
import Approvals from "./Approvals";
import Chats from "./Chats";

type Page = "dashboard" | "timeline" | "sessions" | "agents" | "settings" | "approvals" | "chats";

interface MainLayoutProps {
  token: string;
  onLogout: () => void;
}

export default function MainLayout(props: MainLayoutProps) {
  const [activePage, setActivePage] = createSignal<Page>("dashboard");

  const NavItem = (p: { page: Page; label: string }) => (
    <button
      onClick={() => setActivePage(p.page)}
      class={`w-full text-left px-4 py-2 rounded-lg transition-colors mb-1 ${
        activePage() === p.page
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
              Platform
            </h2>
            <NavItem page="dashboard" label="Dashboard" />
            <NavItem page="timeline" label="Timeline" />
            <NavItem page="sessions" label="Session" />
          </div>

          <div class="mb-6">
            <h2 class="px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
              Communication
            </h2>
            <NavItem page="approvals" label="Pending Approval" />
            <NavItem page="chats" label="Direct Message" />
          </div>

          <div>
            <h2 class="px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
              Management
            </h2>
            <NavItem page="agents" label="Agents" />
            <NavItem page="settings" label="Settings" />
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
      <main class="flex-1 overflow-auto bg-neutral-900/50">
        <div class="w-full p-8 pr-12">
            <Switch>
            <Match when={activePage() === "dashboard"}>
                <Dashboard />
            </Match>
            <Match when={activePage() === "timeline"}>
                <Timeline />
            </Match>
            <Match when={activePage() === "sessions"}>
                <Sessions />
            </Match>
            <Match when={activePage() === "approvals"}>
                <Approvals />
            </Match>
            <Match when={activePage() === "chats"}>
                <Chats />
            </Match>
            <Match when={activePage() === "agents"}>
                <Agents token={props.token} onLogout={props.onLogout} />
            </Match>
            <Match when={activePage() === "settings"}>
                <Settings />
            </Match>
            </Switch>
        </div>
      </main>
    </div>
  );
}
