import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useLoad } from '../hooks/useLoad'
import { ErrorBox, Heading, Loading, ProfileCard, Shirt } from '../components/Common'
import Report, { Metrics } from '../components/Report'

export default function Scouting() {
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const { data, loading, error, reload } = useLoad(`/players?q=${encodeURIComponent(search)}&offset=${offset}`)
  return <><Heading title="The scouting room" text="Discover saved player profiles and their latest match reports." /><form className="search" onSubmit={event => { event.preventDefault(); setSearch(query); setOffset(0) }}><label className="sr-only" htmlFor="player-search">Search players</label><input id="player-search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Search by name or username" /><button type="submit">Search</button></form><ErrorBox message={error} retry={reload} />{loading ? <Loading /> : data?.length ? <div className="scout-grid">{data.map(player => <article className="player-card" key={player.user.id}><div className="player-card-top"><Shirt small /><div><span className="muted">{player.profile.position}</span><h2>{player.profile.full_name || player.user.username}</h2><p>{player.profile.team || 'Independent player'}</p></div></div>{player.latest_analysis ? <>{player.latest_analysis.result.demo && <span className="status demo">Demo report</span>}<Metrics metrics={player.latest_analysis.result.metrics} /></> : <p className="no-report">No completed analyses yet.</p>}<Link className="button secondary" to={`/players/${player.user.id}`}>View player</Link></article>)}</div> : <div className="empty"><h2>{search ? 'No players match your search' : 'The squad is still taking shape'}</h2><p>{search ? 'Try another name or username.' : 'Registered players will appear here. Their reports are added after analysis.'}</p></div>}<div className="actions pagination"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous</button><button disabled={(data?.length || 0) < 50} onClick={() => setOffset(offset + 50)}>Next</button></div></>
}
export function PlayerDetail() {
  const { id } = useParams()
  const { data, loading, error, reload } = useLoad(`/players/${id}`)
  if (loading) return <Loading />
  if (!data) return <ErrorBox message={error} retry={reload} />
  return <><Heading title="Player detail" action={<Link className="button secondary" to="/dashboard">Back to scouting</Link>} /><ProfileCard {...data} /><h2 className="section-title">Recent match reports</h2>{data.analyses.length ? data.analyses.map((analysis, index) => <details className="saved-report" key={analysis.id} open={index === 0}><summary>Match report · {new Date(analysis.completed_at).toLocaleDateString()}{analysis.result.demo ? ' · Demo' : ''}</summary><Report result={analysis.result} /></details>) : <p className="empty">This player has no completed analysis yet.</p>}</>
}
