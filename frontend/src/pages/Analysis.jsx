import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import { useLoad } from '../hooks/useLoad'
import { ErrorBox, Heading, Loading, Shirt, Status } from '../components/Common'
import Report from '../components/Report'

export default function Analysis() {
  const { id } = useParams()
  const { data: job, error, loading, reload } = useLoad(`/analyses/${id}/status`, 1200)
  if (loading) return <Loading />
  if (!job) return <ErrorBox message={error} retry={reload} />
  return (
    <>
      <Heading
        title={job.status === 'completed' ? 'Your match report' : 'Match analysis'}
        text={job.original_filename}
        action={<Status status={job.status} />}
      />
      <ErrorBox message={error} retry={reload} />
      {job.demo && job.status !== 'completed' && <p className="notice">Demo analysis · Sample data is used for this job.</p>}
      {job.status === 'completed' ? (
        <Completed id={id} />
      ) : job.status === 'failed' ? (
        <section className="panel">
          <h2>Analysis could not finish</h2>
          <ErrorBox message={job.error} />
          <Link className="button primary" to="/upload">
            Upload another video
          </Link>
        </section>
      ) : (
        <>
          <section className="progress-panel" aria-live="polite">
            <div>
              <strong>
                {job.stage === 'awaiting_selection'
                  ? 'Players found. Choose your tracked ID.'
                  : job.status === 'queued'
                    ? 'Queued for processing'
                    : job.stage === 'reporting'
                      ? 'Building your report'
                      : 'Finding and tracking players'}
              </strong>
              <span>{job.demo ? 'DEMO' : 'REAL'}</span>
            </div>
            <p>
              {job.stage === 'awaiting_selection'
                ? 'A tracker ID represents one visible track; it may change after occlusion.'
                : 'CPU processing can take several minutes. You can leave this page and return from your profile; the current stage is saved.'}
            </p>
          </section>
          {job.stage === 'awaiting_selection' && (
            <Selection key={id} id={id} job={job} onRun={reload} />
          )}
        </>
      )}
    </>
  )
}
function Completed({ id }) {
  const { data, error, loading, reload } = useLoad(`/analyses/${id}/result`)
  return loading ? (
    <Loading />
  ) : data ? (
    <Report result={data} />
  ) : (
    <ErrorBox message={error} retry={reload} />
  )
}
function Selection({ id, job, onRun }) {
  const gallery = useLoad(`/analyses/${id}/players`)
  const [selected, setSelected] = useState(job.selected_player_id)
  const [calibrate, setCalibrate] = useState(false)
  const [stationary, setStationary] = useState(false)
  const [points, setPoints] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function run(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      await api.patch(`/analyses/${id}/player`, { player_id: selected })
      const calibration = calibrate
        ? {
            points,
            field_length: Number(form.get('length')),
            field_width: Number(form.get('width')),
            stationary_camera: stationary,
          }
        : null
      await api.post(`/analyses/${id}/run`, { calibration })
      onRun()
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setBusy(false)
    }
  }
  if (gallery.loading) return <Loading />
  if (!gallery.data) return <ErrorBox message={gallery.error} retry={gallery.reload} />
  return (
    <form onSubmit={run} className="selection">
      <h2>Which player are you?</h2>
      {!job.demo && (
        <p>
          The model detects people. Referees, staff and spectators can appear here; choose your
          visible track carefully.
        </p>
      )}
      <div className="player-gallery">
        {gallery.data.players.map((player) => (
          <button
            type="button"
            className={`player-choice ${selected === player.id ? 'selected' : ''}`}
            key={player.id}
            aria-pressed={selected === player.id}
            onClick={() => setSelected(player.id)}
          >
            {player.thumbnail ? (
              <img src={player.thumbnail} alt={`Tracked player ${player.id}`} />
            ) : (
              <Shirt number={player.id} small />
            )}
            <strong>{player.label}</strong>
            <span>{player.observations} observations</span>
          </button>
        ))}
      </div>
      {!job.demo && (
        <details>
          <summary>Field calibration for distance and speed</summary>
          <p>
            Use a static camera. Identify the four corners of a known rectangle on the pitch in
            perimeter order: origin, along its length, opposite corner, along its width. Enter that
            rectangle’s actual dimensions. Panning, zooming and camera shake invalidate one fixed
            projection. Detected camera motion or uncertain camera stability keeps physical metrics
            unavailable.
          </p>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={calibrate}
              onChange={(event) => setCalibrate(event.target.checked)}
            />
            Enable manual calibration
          </label>
          {calibrate && (
            <div className="calibration">
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={stationary}
                  onChange={(event) => setStationary(event.target.checked)}
                />
                I confirm the camera stayed fixed throughout this clip
              </label>
              <div
                className="calibration-image"
                onClick={(event) => {
                  if (points.length >= 4) return
                  const box = event.currentTarget.getBoundingClientRect()
                  setPoints([
                    ...points,
                    [
                      Math.round(((event.clientX - box.left) / box.width) * job.video.width),
                      Math.round(((event.clientY - box.top) / box.height) * job.video.height),
                    ],
                  ])
                }}
              >
                <img
                  src={gallery.data.preview}
                  alt="First video frame. Click four field corners or enter their pixel coordinates below."
                />
                {points.map(([x, y], i) => (
                  <span
                    key={i}
                    style={{
                      left: `${(100 * x) / job.video.width}%`,
                      top: `${(100 * y) / job.video.height}%`,
                    }}
                  >
                    {i + 1}
                  </span>
                ))}
              </div>
              <p>
                {points.length}/4 corners chosen. Frame: {job.video.width} × {job.video.height}{' '}
                pixels.
              </p>
              <button type="button" onClick={() => setPoints([])}>
                Reset corners
              </button>
              <label>
                Corner coordinates (JSON; keyboard alternative)
                <input
                  key={JSON.stringify(points)}
                  defaultValue={JSON.stringify(points)}
                  onBlur={(event) => {
                    try {
                      const value = JSON.parse(event.target.value)
                      if (
                        !Array.isArray(value) ||
                        value.length !== 4 ||
                        value.some(
                          (point) =>
                            !Array.isArray(point) ||
                            point.length !== 2 ||
                            point.some((number) => !Number.isFinite(number)),
                        )
                      ) {
                        throw new Error('Invalid points')
                      }
                      setPoints(value)
                      setError('')
                    } catch {
                      setError(
                        'Enter four coordinate pairs, for example [[10,10],[300,10],[300,180],[10,180]].',
                      )
                    }
                  }}
                />
              </label>
              <div className="form-grid">
                <label>
                  Rectangle length (m)
                  <input
                    name="length"
                    type="number"
                    defaultValue="105"
                    min="5"
                    max="150"
                    required
                  />
                </label>
                <label>
                  Rectangle width (m)
                  <input name="width" type="number" defaultValue="68" min="5" max="100" required />
                </label>
              </div>
            </div>
          )}
        </details>
      )}
      <ErrorBox message={error} />
      <button
        className="primary"
        disabled={!selected || busy || (calibrate && (points.length !== 4 || !stationary))}
      >
        {busy ? 'Starting…' : 'Build my report'}
      </button>
    </form>
  )
}
