import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../api';

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault(); setLoading(true); setError('');
    try { await api.post('/auth/register', form); navigate('/login'); }
    catch (err) { setError(err.response?.data?.detail || 'Unable to create account.'); }
    finally { setLoading(false); }
  }
  return <main className="auth-shell"><section className="auth-panel"><p className="eyebrow">VERVE GATE / NEW MERCHANT</p><h1>Open your payment desk.</h1><p className="muted">Create an account to issue checkout sessions and connect your settlement rails.</p><form onSubmit={submit} className="stack-form"><label>Email<input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label><label>Password<input type="password" minLength="8" required value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>{error && <p className="form-error">{error}</p>}<button className="primary-button" disabled={loading}>{loading ? 'Creating...' : 'Create merchant account'}</button></form><p className="form-foot">Already registered? <Link to="/login">Sign in</Link></p></section></main>;
}
