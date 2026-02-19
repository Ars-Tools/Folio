export default function Settings() {
  return (
    <div class="w-full h-full">
      <h1 class="text-3xl font-bold mb-4">Settings</h1>
      <div class="bg-neutral-800 p-6 rounded-xl border border-neutral-700 w-full space-y-4">
        <div>
            <h3 class="font-medium mb-1">Theme</h3>
            <p class="text-sm text-neutral-400">Manage your application appearance</p>
        </div>
        <div class="h-px bg-neutral-700"></div>
        <div>
            <h3 class="font-medium mb-1">Account</h3>
            <p class="text-sm text-neutral-400">Update your profile settings</p>
        </div>
      </div>
    </div>
  );
}
