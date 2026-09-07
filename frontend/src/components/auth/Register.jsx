import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api, { getApiError } from '../../api';

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault(); setError('');
    if (!form.email.trim() || !form.password) { setError('Enter an email and password to create your account.'); return; }
    if (form.password.length < 8) { setError('Your password must be at least 8 characters long.'); return; }
    setLoading(true);
    try {
      const { data } = await api.post('/auth/register', form);
      localStorage.setItem('vg_access_token', data.access_token);
      localStorage.setItem('vg_role', data.role || 'merchant');
      window.dispatchEvent(new Event('vg-auth-changed'));
      navigate('/dashboard');
    }
    catch (err) { setError(getApiError(err, 'Unable to create account. Please check your details and try again.')); }
    finally { setLoading(false); }
  }
  return <main className="auth-shell"><section className="auth-panel"><p className="eyebrow">VERVE GATE / NEW MERCHANT</p><h1>Open your payment desk.</h1><p className="muted">Create an account to issue checkout sessions and connect your settlement rails.</p><form onSubmit={submit} className="stack-form" noValidate><label>Email<input type="email" autoComplete="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label><label>Password<input type="password" autoComplete="new-password" minLength="8" required value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={loading}>{loading ? 'Creating...' : 'Create merchant account'}</button></form><p className="form-foot">Already registered? <Link to="/login">Sign in</Link></p></section></main>;
}
