import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import { ErrorBox, Heading } from '../components/Common'

export default function Upload({ health }) {
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(null)
  const [sampleBusy, setSampleBusy] = useState(false)
  const navigate = useNavigate()
  async function useSample() {
    setSampleBusy(true)
    setError('')
    try {
      const { data } = await api.get('/demo/sample', { responseType: 'blob' })
      setFile(new File([data], 'synthetic-demo.avi', { type: 'video/x-msvideo' }))
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setSampleBusy(false)
    }
  }
  async function upload(event) {
    event.preventDefault()
    setError('')
    if (!file) return setError('Choose a video first.')
    if (file.size > (health?.max_upload_mb || 200) * 1024 * 1024)
      return setError('This video exceeds the upload limit. Trim it and try again.')
    const body = new FormData()
    body.append('video', file)
    setProgress(0)
    try {
      const { data } = await api.post('/analyses', body, {
        timeout: 0,
        onUploadProgress: (event) =>
          setProgress(Math.round((100 * event.loaded) / (event.total || file.size))),
      })
      navigate(`/analyses/${data.id}`)
    } catch (failure) {
      setError(errorMessage(failure))
      setProgress(null)
    }
  }
  return (
    <>
      <Heading
        title="Bring your game into focus"
        text="Upload a match clip. Find yourself on the pitch. Explore your movement."
      />
      <div className="upload-grid">
        <form className="panel" onSubmit={upload}>
          <ErrorBox message={error} />
          {health?.demo_mode && (
            <div className="sample-choice">
              <h2>Start with the synthetic sample</h2>
              <p>No footage needed. This small generated clip demonstrates upload, selection and reporting.</p>
              <button type="button" disabled={sampleBusy || progress !== null} onClick={useSample}>
                {sampleBusy ? 'Preparing sample…' : 'Use synthetic demo sample'}
              </button>
            </div>
          )}
          <label
            className="upload-target"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault()
              if (progress === null) setFile(event.dataTransfer.files[0])
            }}
          >
            <span className="upload-symbol" aria-hidden="true">
              ↥
            </span>
            <strong>{file ? file.name : 'Choose or drop your match video'}</strong>
            <span>MP4, MOV or AVI · Up to {health?.max_upload_mb || 200} MB</span>
            <input
              type="file"
              aria-label="Match video"
              accept=".mp4,.mov,.avi,video/mp4,video/quicktime,video/x-msvideo"
              disabled={progress !== null}
              onChange={(event) => setFile(event.target.files[0])}
            />
          </label>
          {progress !== null && (
            <div role="status">
              <p>
                Uploading {progress}%{progress === 100 ? ' · Checking video…' : ''}
              </p>
              <progress value={progress} max="100" />
            </div>
          )}
          <button className="primary" disabled={!file || progress !== null}>
            {progress !== null ? 'Uploading…' : 'Upload and find players'}
          </button>
        </form>
        <aside className="upload-guide">
          <h2>A clearer view of your game</h2>
          <ol>
            <li>
              <strong>Use a steady camera</strong>
              <p>Keep the pitch and players visible. Camera movement affects field measurements.</p>
            </li>
            <li>
              <strong>Find your player</strong>
              <p>Select your tracked ID from the detected player gallery.</p>
            </li>
            <li>
              <strong>Add field calibration</strong>
              <p>
                Known corners, a confirmed fixed camera and reliable timestamps may allow physical
                estimates. Their accuracy is unvalidated; otherwise explore image movement.
              </p>
            </li>
          </ol>
          {health?.demo_mode && (
            <p className="notice">
              Demo mode uses sample players and metrics. Your video is validated, but no AI model
              runs.
            </p>
          )}
        </aside>
      </div>
    </>
  )
}
