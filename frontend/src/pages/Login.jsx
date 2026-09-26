import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowUpRight, ArrowLeft, ShieldCheck, Eye, EyeOff } from 'lucide-react';
import { Brand } from './Landing';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch {
      setError('Unable to sign in. Check your credentials and try again.');
    } finally {
      setLoading(false);
    }
  };
  return <div className="login-page">
    <section className="login-story grid-paper"><Brand /><div><span className="eyebrow">WELCOME TO YOUR COMMAND CENTER</span><h1>MORE SIGNAL.<br />LESS <span>NOISE.</span></h1><p>Bring your cameras, detections, and evidence into focus. One workspace. The whole picture.</p></div><span className="login-story-footer"><ShieldCheck size={17} /> Intelligence with human judgment at its core.</span></section>
    <main className="login-panel"><Link to="/" className="back-link"><ArrowLeft size={16} /> Back to NEXUS</Link><div className="login-form-wrap"><span className="eyebrow">YOUR WORKSPACE IS WAITING</span><h2>BACK IN FOCUS.</h2><p>Sign in to the NEXUS command center.</p><form onSubmit={handleSubmit}>
      <label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="username" required placeholder="operator@security.local" value={email} onChange={event => setEmail(event.target.value)} disabled={loading} />
      <label htmlFor="password">Password</label><div className="password-field"><input id="password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required placeholder="Enter your password" value={password} onChange={event => setPassword(event.target.value)} disabled={loading} /><button type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
      {error && <p className="login-error" role="alert">{error}</p>}
      <button className="display-button" type="submit" disabled={loading}>{loading ? 'SIGNING IN...' : 'ENTER COMMAND CENTER'}<ArrowUpRight size={21} /></button>
    </form><div className="login-note"><ShieldCheck size={18} /><p>For authorized personnel. Need an account?<br />Contact your system administrator.</p></div></div><span className="login-panel-footer">NEXUS / INTELLIGENCE, CONNECTED.</span></main>
  </div>;
}
