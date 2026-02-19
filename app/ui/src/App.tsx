import { createSignal, Show, type Component } from 'solid-js';
import Login from './Login';
import MainLayout from './MainLayout';

const App: Component = () => {
    // Initialize token from localStorage if available
    const [token, setToken] = createSignal<string | null>(localStorage.getItem('folio_token'));

    const handleLoginSuccess = (newToken: string) => {
        localStorage.setItem('folio_token', newToken);
        setToken(newToken);
    };

    const handleLogout = () => {
        localStorage.removeItem('folio_token');
        setToken(null);
    };

    return (
        <Show when={token()} fallback={<Login onLoginSuccess={handleLoginSuccess} />}>
            <MainLayout token={token()!} onLogout={handleLogout} />
        </Show>
    );
};

export default App;
