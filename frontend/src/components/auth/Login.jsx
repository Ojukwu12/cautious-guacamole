import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api, { getApiError } from '../../api';

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault(); setError('');
    if (!form.email.trim() || !form.password) { setError('Enter your email and password to continue.'); return; }
    setLoading(true);
    try {
      const { data } = await api.post('/auth/login', form);
      localStorage.setItem('vg_access_token', data.access_token);
      localStorage.setItem('vg_role', data.role || 'merchant');
      window.dispatchEvent(new Event('vg-auth-changed'));
      navigate(data.role === 'admin' ? '/admin' : '/dashboard');
    } catch (err) { setError(getApiError(err, 'Unable to sign in. Check your credentials and try again.')); }
    finally { setLoading(false); }
  }

  return <main className="auth-shell"><section className="auth-panel"><p className="eyebrow">VERVE GATE / CONTROL ROOM</p><h1>Move money with clarity.</h1><p className="muted">Sign in to create sessions, inspect your ledger, and manage settlement routing.</p><form onSubmit={submit} className="stack-form" noValidate><label>Email<input type="email" autoComplete="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label><label>Password<input type="password" autoComplete="current-password" required value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button></form><p className="form-foot"><Link to="/forgot-password">Forgot password?</Link></p><p className="form-foot">New merchant? <Link to="/register">Create an account</Link></p></section></main>;
}
