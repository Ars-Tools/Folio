import { createSignal } from "solid-js";
import { TextField, Button } from "@kobalte/core";

interface LoginProps {
  onLoginSuccess: (token: string) => void;
}

export default function Login(props: LoginProps) {
  const [token, setToken] = createSignal("");
  const [error, setError] = createSignal("");

  const handleLogin = async (e: Event) => {
    e.preventDefault();
    setError("");
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token() })
      });
      const data = await response.json();
      if (response.ok) {
        props.onLoginSuccess(data.access_token);
      } else {
        const detail = data.detail;
        const msg = typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ")
            : "Authentication failed";
        setError(msg);
      }
    } catch {
      setError("Network error or server unavailable");
    }
  };

  return (
    <div class="flex items-center justify-center min-h-screen bg-neutral-900 text-white font-sans">
      <form onSubmit={handleLogin} class="w-full max-w-sm p-8 bg-neutral-800 rounded-xl shadow-2xl border border-neutral-700 space-y-6">
        <h2 class="text-2xl font-bold text-center text-neutral-100 mb-6">FOLIO</h2>

        <TextField.Root class="flex flex-col space-y-2" value={token()} onChange={setToken}>
          <TextField.Label class="text-sm font-medium text-neutral-400">Token</TextField.Label>
          <TextField.Input
            type="password"
            class="w-full px-4 py-2 bg-neutral-900 border border-neutral-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-500 focus:border-transparent transition-all text-white placeholder-neutral-500 font-mono text-sm"
            placeholder="Enter your access token"
          />
        </TextField.Root>

        {error() && (
          <div class="p-3 bg-red-900/50 border border-red-800 rounded-lg text-red-200 text-sm">{error()}</div>
        )}

        <Button.Root type="submit" class="w-full py-2.5 bg-neutral-200 hover:bg-white text-neutral-900 font-semibold rounded-lg shadow-lg transition-transform active:scale-95 focus:outline-none focus:ring-2 focus:ring-neutral-400 focus:ring-offset-2 focus:ring-offset-neutral-800">
          Sign In
        </Button.Root>
      </form>
    </div>
  );
}
