export default function Dashboard() {
  return (
    <div class="w-full h-full">
      <h1 class="text-3xl font-bold mb-8">Dashboard</h1>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div class="bg-neutral-800 p-6 rounded-xl border border-neutral-700 w-full">
          <h3 class="text-neutral-400 text-sm font-medium mb-2">Total Agents</h3>
          <p class="text-3xl font-bold">4</p>
        </div>
        <div class="bg-neutral-800 p-6 rounded-xl border border-neutral-700 w-full">
          <h3 class="text-neutral-400 text-sm font-medium mb-2">Active Sessions</h3>
          <p class="text-3xl font-bold">12</p>
        </div>
        <div class="bg-neutral-800 p-6 rounded-xl border border-neutral-700 w-full">
          <h3 class="text-neutral-400 text-sm font-medium mb-2">System Status</h3>
          <p class="text-3xl font-bold text-green-500">Operational</p>
        </div>
      </div>
    </div>
  );
}
