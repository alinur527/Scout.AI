import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import { ErrorBox } from '../components/Common'

export default function Auth({ register = false, onLogin, demo }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    const form = Object.fromEntries(new FormData(event.currentTarget))
    try {
      if (register) {
        await api.post('/auth/register', form)
        navigate('/login', { state: { registered: true } })
      } else {
        const { data } = await api.post('/auth/login', form)
        sessionStorage.setItem('scout_token', data.access_token)
        onLogin(data.user)
        navigate(data.user.role === 'player' ? '/profile/view' : '/dashboard')
      }
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="auth-layout">
      <section className="auth-story">
        <span className="brand">
          Scout<span>AI</span>
          <i />
        </span>
        <h1>
          Your footage.
          <br />
          A clearer match report.
        </h1>
        <p>
          Upload a football clip, choose an anonymous track and explore its path, heatmap and saved
          report. Share with scouts only when you choose.
        </p>
        <div className="first-run-guide">
          <h2>{demo ? 'Try the complete demo' : 'Analyze with local computer vision'}</h2>
          <p>{demo
            ? 'Create a player account, then use the synthetic sample on the upload page. DEMO shows the full workflow with sample results; it does not assess football performance.'
            : 'Use a short, steady clip with visible players. REAL runs local detection and tracking; identities can split and officials may be detected.'}</p>
          <p>Physical accuracy is not validated. Moving cameras or missing calibration keep distance, speed and sprints unavailable in REAL mode.</p>
        </div>
        <div className="tactical-art" aria-hidden="true">
          <div className="centre-circle" />
          <div className="centre-line" />
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <i key={i} className={`marker marker-${i}`}>
              {i * 2 + 1}
            </i>
          ))}
        </div>
        <span className="story-note">A football video workspace. Private by default.</span>
      </section>
      <section className="auth-panel">
        <div>
          <p className="muted">{demo ? 'DEMO workspace · Synthetic results' : 'REAL workspace · Local inference'}</p>
          <h2>{register ? 'Join the squad' : 'Welcome back'}</h2>
          <p>
            {register ? 'Create a player or scout account.' : 'Log in to your ScoutAI workspace.'}
          </p>
          <ErrorBox message={error} />
          {!register && location.state?.registered && <p role="status" className="notice">Account created. Log in to start your private workspace.</p>}
          <form onSubmit={submit}>
            <label>
              Username
              <input
                name="username"
                required
                minLength="3"
                maxLength="40"
                pattern="[A-Za-z0-9_]+"
                autoComplete="username"
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                required
                minLength="8"
                maxLength="128"
                autoComplete={register ? 'new-password' : 'current-password'}
              />
            </label>
            {register && (
              <label>
                Account type
                <select name="role" defaultValue="player">
                  <option value="player">Player</option>
                  <option value="scout">Scout</option>
                </select>
              </label>
            )}
            <button className="primary" disabled={busy}>
              {busy ? 'Please wait…' : register ? 'Create account' : 'Log in'}
            </button>
          </form>
          <p className="auth-switch">
            {register ? 'Already part of the team?' : 'New to ScoutAI?'}{' '}
            <Link to={register ? '/login' : '/register'}>
              {register ? 'Log in' : 'Create account'}
            </Link>
          </p>
        </div>
      </section>
    </div>
  )
}
