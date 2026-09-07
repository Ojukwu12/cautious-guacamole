import { ArrowRight, Compass } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function NotFound({ isAuthenticated, role }) {
  const navigate = useNavigate();
  const destination = isAuthenticated ? (role === 'admin' ? '/admin' : '/dashboard') : '/login';

  return (
    <main className="not-found-shell">
      <section className="not-found-panel">
        <Compass size={32} />
        <p className="eyebrow">VERVE GATE / 404</p>
        <h1>That route does not exist.</h1>
        <p className="muted">The page may have moved, expired, or never belonged to this payment desk.</p>
        <button className="primary-button" onClick={() => navigate(destination)}>
          {isAuthenticated ? 'Return to dashboard' : 'Go to sign in'} <ArrowRight size={16} />
        </button>
      </section>
    </main>
  );
}
