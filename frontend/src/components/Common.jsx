import { Link } from 'react-router-dom'

export function ErrorBox({ message, retry }) {
  return message ? <div className="error" role="alert">{message} {retry && <button onClick={retry}>Try again</button>}</div> : null
}
export function Loading() { return <p role="status" className="loading">Loading ScoutAI…</p> }
export function Heading({ title, text, action }) {
  return <header className="page-heading"><div><h1>{title}</h1>{text && <p>{text}</p>}</div>{action}</header>
}
export function Shirt({ number = 'S', small = false }) {
  return <div className={`shirt ${small ? 'small' : ''}`} aria-hidden="true"><svg viewBox="0 0 120 120"><path d="M39 12 12 30 25 52 36 45 36 105 84 105 84 45 95 52 108 30 81 12Q60 32 39 12Z" /><text x="60" y="76" textAnchor="middle">{number}</text></svg></div>
}
export function ProfileCard({ profile, user, editable = false }) {
  return <section className="identity"><Shirt /><div><p className="muted">{profile?.position || 'Player'}{profile?.team ? ` / ${profile.team}` : ''}</p><h2>{profile?.full_name || user.username}</h2><p>@{user.username}{profile?.age ? ` · ${profile.age} years` : ''}</p><p>{profile?.bio || 'Add your team, position and a short introduction to your scouting profile.'}</p>{editable && <Link className="button secondary" to="/profile/edit">Edit profile</Link>}</div></section>
}
export function Status({ status }) { return <span className={`status ${status}`}>{status}</span> }
