export default function Sessions() {
  return (
    <div class="w-full h-full">
      <h1 class="text-3xl font-bold mb-8">Sessions</h1>
      <div class="rounded-xl border border-neutral-700 bg-neutral-800/50 overflow-hidden w-full">
        <table class="w-full text-left">
          <thead class="bg-neutral-800 text-neutral-400 text-sm">
            <tr>
              <th class="px-6 py-4 font-medium">Session ID</th>
              <th class="px-6 py-4 font-medium">Agent</th>
              <th class="px-6 py-4 font-medium">Last Active</th>
              <th class="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-700 text-neutral-300">
             <tr>
                <td class="px-6 py-4 text-neutral-500 italic" colspan="4">No active sessions</td>
             </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
