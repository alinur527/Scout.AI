import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'

export function useLoad(path, interval = 0) {
  const [state, setState] = useState({ data: null, error: '', loading: true })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let stopped = false
    let timer
    const controller = new AbortController()
    async function load() {
      try {
        const { data } = await api.get(path, { signal: controller.signal })
        if (!stopped) setState({ data, error: '', loading: false })
      } catch (error) {
        if (!stopped) setState(previous => ({ ...previous, error: errorMessage(error), loading: false }))
      } finally {
        if (!stopped && interval) timer = setTimeout(load, interval)
      }
    }
    load()
    return () => { stopped = true; controller.abort(); clearTimeout(timer) }
  }, [path, interval, revision])
  return { ...state, reload: () => setRevision(value => value + 1) }
}
