import { useState } from 'react'

export function Metrics({ metrics }) {
  const values = [['Distance', metrics?.total_distance_m, 'm'], ['Top speed', metrics?.top_speed_kmh, 'km/h'], ['Sprints', metrics?.sprint_count, '']]
  return <div className="metrics">{values.map(([label, value, unit]) => <div key={label}><span>{label}</span><strong>{value == null ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 })}<small>{value == null ? '' : unit}</small></strong>{value == null && <small>Calibration required</small>}</div>)}</div>
}
export default function Report({ result }) {
  const [layer, setLayer] = useState('heatmap')
  const peak = Math.max(1, ...result.heatmap.flat())
  const field = result.coordinate_space === 'field' || result.demo
  return <section className="report">
    {result.demo && <p className="notice">Demo report · Sample metrics and synthetic movement. This is not an assessment of the uploaded video.</p>}
    <Metrics metrics={result.metrics} />
    <div className="report-grid"><section className="map-panel"><div className="section-heading"><h2>{field ? 'Movement on the pitch' : 'Movement in the frame'}</h2><div className="segmented"><button aria-pressed={layer === 'heatmap'} onClick={() => setLayer('heatmap')}>Heatmap</button><button aria-pressed={layer === 'path'} onClick={() => setLayer('path')}>Path</button></div></div>
      <svg className="pitch" viewBox="0 0 640 400" role="img" aria-label={`${layer} for player ${result.player_id}`}>
        <rect width="640" height="400" rx="8" fill="#102b39" />
        {Array.from({ length: 8 }, (_, i) => <rect key={i} x={i * 80} width="40" height="400" fill="#143341" />)}
        {layer === 'heatmap' ? result.heatmap.flatMap((row, y) => row.map((value, x) => value > 0 && <rect key={`${x}-${y}`} x={20 + x * 30} y={20 + y * 30} width="30" height="30" rx="7" fill="#62e6eb" opacity={.15 + .75 * value / peak} />)) : <polyline points={result.movement.map(([x, y]) => `${20 + x * 600},${20 + y * 360}`).join(' ')} fill="none" stroke="#62e6eb" strokeWidth="2" />}
        <g fill="none" stroke="#accad1" strokeOpacity=".65" strokeWidth="1.5"><rect x="20" y="20" width="600" height="360" />{field && <><path d="M320 20V380 M20 100H110V300H20 M620 100H530V300H620 M20 155H55V245H20 M620 155H585V245H620" /><circle cx="320" cy="200" r="56" /><circle cx="320" cy="200" r="2" fill="#accad1" /></>}</g>
      </svg><div className="map-caption"><span>{field ? 'Relative field position' : 'Image coordinates · camera perspective'}</span><span className="legend">Low <i /> High</span></div>
    </section><aside className="report-notes"><h2>Analysis details</h2><dl><dt>Tracked player</dt><dd>#{result.player_id}</dd><dt>Video duration</dt><dd>{result.duration_seconds.toFixed(1)} s</dd><dt>Observations</dt><dd>{result.observations}</dd><dt>Processed frames</dt><dd>{result.frames_processed}</dd><dt>Processing</dt><dd>{result.device}</dd><dt>Calibration</dt><dd>{result.calibrated ? 'Manual field corners' : 'Not provided'}</dd><dt>Rejected segments</dt><dd>{result.rejected_segments}</dd></dl></aside></div>
    <div className="report-footnotes">{result.warnings.map(warning => <p key={warning}>{warning}</p>)}</div>
    {result.annotated_preview && <details><summary>View detected players</summary><img className="preview" src={result.annotated_preview} alt="Video frame annotated with tracked player IDs" /></details>}
  </section>
}
