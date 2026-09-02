import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api';

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault(); setLoading(true); setError('');
    try {
      const { data } = await api.post('/auth/login', form);
      localStorage.setItem('vg_access_token', data.access_token);
      navigate('/dashboard');
    } catch (err) { setError(err.response?.data?.detail || 'Unable to sign in.'); }
    finally { setLoading(false); }
  }

  return <main className="auth-shell"><section className="auth-panel"><p className="eyebrow">VERVE GATE / CONTROL ROOM</p><h1>Move money with clarity.</h1><p className="muted">Sign in to create sessions, inspect your ledger, and manage settlement routing.</p><form onSubmit={submit} className="stack-form"><label>Email<input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label><label>Password<input type="password" required value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>{error && <p className="form-error">{error}</p>}<button className="primary-button" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button></form><p className="form-foot">New merchant? <Link to="/register">Create an account</Link></p></section></main>;
}
