import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api, { getApiError } from '../../api';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault(); setLoading(true); setError(''); setMessage('');
    if (password.length < 8) { setError('Your password must be at least 8 characters long.'); setLoading(false); return; }
    try { const { data } = await api.post('/auth/password-reset/confirm', { token: params.get('token') || '', password }); setMessage(data.message); }
    catch (err) { setError(getApiError(err, 'This reset link is invalid or expired.')); }
    finally { setLoading(false); }
  }
  return <main className="auth-shell"><section className="auth-panel"><p className="eyebrow">VERVE GATE / ACCOUNT RECOVERY</p><h1>Choose a new password.</h1><form onSubmit={submit} className="stack-form" noValidate><label>New password<input type="password" autoComplete="new-password" minLength="8" required value={password} onChange={event => setPassword(event.target.value)} /></label>{error && <p className="form-error" role="alert">{error}</p>}{message && <p className="success-text" role="status">{message}</p>}<button className="primary-button" disabled={loading || !!message}>{loading ? 'Updating...' : 'Update password'}</button></form><p className="form-foot"><Link to="/login">Return to sign in</Link></p></section></main>;
}
