import { useState } from 'react';
import { Link } from 'react-router-dom';
import api, { getApiError } from '../../api';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault(); setLoading(true); setError(''); setMessage('');
    try { const { data } = await api.post('/auth/password-reset/request', { email }); setMessage(data.message); }
    catch (err) { setError(getApiError(err, 'Unable to request a password reset.')); }
    finally { setLoading(false); }
  }
  return <main className="auth-shell"><section className="auth-panel"><p className="eyebrow">VERVE GATE / ACCOUNT RECOVERY</p><h1>Reset your password.</h1><p className="muted">Enter your email and we will send a secure reset link if the account exists.</p><form onSubmit={submit} className="stack-form" noValidate><label>Email<input type="email" autoComplete="email" required value={email} onChange={event => setEmail(event.target.value)} /></label>{error && <p className="form-error" role="alert">{error}</p>}{message && <p className="success-text" role="status">{message}</p>}<button className="primary-button" disabled={loading}>{loading ? 'Sending...' : 'Send reset link'}</button></form><p className="form-foot"><Link to="/login">Return to sign in</Link></p></section></main>;
}
