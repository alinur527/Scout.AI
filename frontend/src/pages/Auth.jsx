import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import { ErrorBox } from '../components/Common'

export default function Auth({ register = false, onLogin }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
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
          Every movement
          <br />
          tells a story.
        </h1>
        <p>
          Bring your match footage into focus. Build your player profile and explore the movement
          behind your game.
        </p>
        <div className="tactical-art" aria-hidden="true">
          <div className="centre-circle" />
          <div className="centre-line" />
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <i key={i} className={`marker marker-${i}`}>
              {i * 2 + 1}
            </i>
          ))}
        </div>
        <span className="story-note">Football intelligence. Built from your footage.</span>
      </section>
      <section className="auth-panel">
        <div>
          <p className="muted">Your next chapter starts here</p>
          <h2>{register ? 'Join the squad' : 'Welcome back'}</h2>
          <p>
            {register ? 'Create a player or scout account.' : 'Log in to your ScoutAI workspace.'}
          </p>
          <ErrorBox message={error} />
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
