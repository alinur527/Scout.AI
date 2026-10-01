import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { useLoad } from '../hooks/useLoad'
import { ErrorBox, Heading, Loading, ProfileCard, Status } from '../components/Common'

export default function Profile({ edit = false }) {
  const profile = useLoad('/profile/me')
  const jobs = useLoad('/analyses')
  if (profile.loading) return <Loading />
  if (!profile.data) return <ErrorBox message={profile.error} retry={profile.reload} />
  if (edit) return <ProfileForm initial={profile.data.profile} />
  return <><Heading title="Your player profile" text="Your game, your footage, your progress." action={<Link className="button primary" to="/upload">Analyze a video</Link>} /><ProfileCard {...profile.data} editable /><section className="section"><div className="section-heading"><h2>Match analyses</h2><span className="muted">{jobs.data?.length || 0} saved</span></div><ErrorBox message={jobs.error} retry={jobs.reload} />{jobs.loading ? <Loading /> : jobs.data?.length ? <div className="analysis-list">{jobs.data.map(job => <Link to={`/analyses/${job.id}`} key={job.id}><div><strong>{job.original_filename}</strong><span>{new Date(job.created_at).toLocaleDateString()}{job.demo ? ' · Demo' : ''}</span></div><Status status={job.status} /></Link>)}</div> : <div className="empty"><h3>Your first match starts here</h3><p>Upload footage to track players and build a movement report.</p><Link className="button secondary" to="/upload">Upload a video</Link></div>}</section></>
}
function ProfileForm({ initial }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  async function save(event) {
    event.preventDefault(); setBusy(true)
    const data = Object.fromEntries(new FormData(event.currentTarget))
    data.age = data.age ? Number(data.age) : null
    try { await api.put('/profile/me', data); navigate('/profile/view') } catch (failure) { setError(errorMessage(failure)) } finally { setBusy(false) }
  }
  return <><Heading title="Make it your profile" text="Help scouts understand the player behind the numbers." /><form className="panel profile-form" onSubmit={save}><ErrorBox message={error} /><div className="form-grid"><label>Full name<input name="full_name" defaultValue={initial.full_name} required maxLength="100" /></label><label>Position<select name="position" defaultValue={initial.position}>{['Goalkeeper', 'Defender', 'Midfielder', 'Forward'].map(position => <option key={position}>{position}</option>)}</select></label><label>Age<input name="age" type="number" min="5" max="100" defaultValue={initial.age || ''} /></label><label>Team<input name="team" maxLength="100" defaultValue={initial.team} /></label></div><label>About you<textarea name="bio" rows="4" maxLength="1000" defaultValue={initial.bio} /></label><div className="actions"><button className="primary" disabled={busy}>{busy ? 'Saving…' : 'Save profile'}</button><Link className="button secondary" to="/profile/view">Cancel</Link></div></form></>
}
