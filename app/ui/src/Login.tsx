import { createSignal } from "solid-js";
import { TextField, Button } from "@kobalte/core";

interface LoginProps {
  onLoginSuccess: (token: string) => void;
}

export default function Login(props: LoginProps) {
  const [username, setUsername] = createSignal("");
  const [password, setPassword] = createSignal("");

  const handleLogin = async (e: Event) => {
    e.preventDefault();
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: username(), password: password() })
      });
      const data = await response.json();
      if (response.ok) {
        props.onLoginSuccess(data.access_token);
      } else {
        alert("Login Failed: " + data.detail);
      }
    } catch (error) {
      console.error("Login error:", error);
      alert("Network error or server unavailable");
    }
  };

  return (
    <div class="flex items-center justify-center min-h-screen bg-neutral-900 text-white font-sans">
      <form onSubmit={handleLogin} class="w-full max-w-sm p-8 bg-neutral-800 rounded-xl shadow-2xl border border-neutral-700 space-y-6">
        <h2 class="text-2xl font-bold text-center text-neutral-100 mb-6">Folio Login</h2>

        <TextField.Root class="flex flex-col space-y-2" value={username()} onChange={setUsername}>
          <TextField.Label class="text-sm font-medium text-neutral-400">Username</TextField.Label>
          <TextField.Input
            class="w-full px-4 py-2 bg-neutral-900 border border-neutral-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-white placeholder-neutral-500"
            placeholder="Enter username"
          />
        </TextField.Root>

        <TextField.Root class="flex flex-col space-y-2" value={password()} onChange={setPassword}>
          <TextField.Label class="text-sm font-medium text-neutral-400">Password</TextField.Label>
          <TextField.Input
            type="password"
            class="w-full px-4 py-2 bg-neutral-900 border border-neutral-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-white placeholder-neutral-500"
            placeholder="Enter password"
          />
        </TextField.Root>

        <Button.Root type="submit" class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg shadow-lg transition-transform active:scale-95 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-neutral-800">
          Sign In
        </Button.Root>
      </form>
    </div>
  );
}
