import { useEffect, useState } from 'react'
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { api } from './api/client'
import { useLoad } from './hooks/useLoad'
import { Loading } from './components/Common'
import Auth from './pages/Auth'
import Profile from './pages/Profile'
import Upload from './pages/Upload'
import Analysis from './pages/Analysis'
import Scouting, { PlayerDetail } from './pages/Scouting'

export default function App() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  const [sessionError, setSessionError] = useState('')
  const health = useLoad('/health', 15000)
  useEffect(() => {
    let active = true
    async function restore() {
      try {
        if (sessionStorage.getItem('scout_token')) {
          const { data } = await api.get('/profile/me')
          if (active) setUser(data.user)
        }
      } catch { if (active) setSessionError('Your session could not be restored. Please log in again.') }
      finally { if (active) setReady(true) }
    }
    function expired() { setUser(null); setSessionError('Your session has expired. Please log in again.') }
    window.addEventListener('scout:unauthorized', expired)
    restore()
    return () => { active = false; window.removeEventListener('scout:unauthorized', expired) }
  }, [])
  function logout() { sessionStorage.removeItem('scout_token'); setUser(null); setSessionError('') }
  const home = user?.role === 'player' ? '/profile/view' : '/dashboard'
  if (!ready) return <Loading />
  return <BrowserRouter><a href="#main" className="skip-link">Skip to content</a>{health.data?.demo_mode && <div className="mode-banner">Demo mode <span>Sample analysis for development. No AI inference.</span></div>}{health.error && <div role="alert" className="mode-banner offline">Server unavailable. Start the backend or check your connection.</div>}{user ? <div className="app-shell"><aside className="sidebar"><Link to={home} className="brand">Scout<span>AI</span><i /></Link><p className="workspace-label">{user.role === 'player' ? 'Player workspace' : 'Scout workspace'}</p><nav aria-label="Main navigation">{user.role === 'player' ? <><NavLink to="/profile/view">My profile</NavLink><NavLink to="/upload">Analyze a video</NavLink></> : <NavLink to="/dashboard">Scouting room</NavLink>}</nav><div className="account"><span>@{user.username}</span><button onClick={logout}>Log out</button></div></aside><main id="main" className="workspace">{health.data && !health.data.worker_online && <p className="notice">The analysis worker is offline. Uploads will stay queued until it starts.</p>}<Routes><Route path="/" element={<Navigate to={home} replace />} /><Route path="/profile/view" element={user.role === 'player' ? <Profile /> : <Navigate to={home} replace />} /><Route path="/profile/edit" element={user.role === 'player' ? <Profile edit /> : <Navigate to={home} replace />} /><Route path="/upload" element={user.role === 'player' ? <Upload health={health.data} /> : <Navigate to={home} replace />} /><Route path="/analyses/:id" element={user.role === 'player' ? <Analysis /> : <Navigate to={home} replace />} /><Route path="/dashboard" element={user.role !== 'player' ? <Scouting /> : <Navigate to={home} replace />} /><Route path="/players/:id" element={user.role !== 'player' ? <PlayerDetail /> : <Navigate to={home} replace />} /><Route path="/login" element={<Navigate to={home} replace />} /><Route path="/register" element={<Navigate to={home} replace />} /><Route path="*" element={<div className="empty"><h1>Page not found</h1><Link to={home}>Return to your workspace</Link></div>} /></Routes></main></div> : <main id="main">{sessionError && <p className="notice" role="alert">{sessionError}</p>}<Routes><Route path="/login" element={<Auth onLogin={value => { setUser(value); setSessionError('') }} />} /><Route path="/register" element={<Auth register />} /><Route path="*" element={<Navigate to="/login" replace />} /></Routes></main>}</BrowserRouter>
}
