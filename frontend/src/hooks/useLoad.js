import { useEffect, useState } from 'react'
import { api, errorMessage } from '../api/client'

export function useLoad(path, interval = 0) {
  const [state, setState] = useState({ path: null, data: null, error: '', loading: true })
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let stopped = false
    let timer
    let sequence = 0
    const controller = new AbortController()
    async function load() {
      const requestSequence = ++sequence
      try {
        const { data } = await api.get(path, { signal: controller.signal })
        if (!stopped && requestSequence === sequence) setState({ path, data, error: '', loading: false })
      } catch (error) {
        if (!stopped && requestSequence === sequence)
          setState((previous) => ({
            path,
            data: [401, 403, 404].includes(error.response?.status)
              ? null
              : previous.path === path ? previous.data : null,
            error: errorMessage(error),
            loading: false,
          }))
      } finally {
        if (!stopped && requestSequence === sequence && interval) timer = setTimeout(load, interval)
      }
    }
    load()
    const refreshOnFocus = () => { clearTimeout(timer); load() }
    window.addEventListener('focus', refreshOnFocus)
    return () => {
      stopped = true
      controller.abort()
      clearTimeout(timer)
      window.removeEventListener('focus', refreshOnFocus)
    }
  }, [path, interval, revision])
  return {
    ...(state.path === path ? state : { data: null, error: '', loading: true }),
    reload: () => setRevision((value) => value + 1),
  }
}
