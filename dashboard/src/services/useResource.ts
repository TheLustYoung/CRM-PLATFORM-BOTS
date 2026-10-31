import {useCallback, useEffect, useState} from 'react';
import {api} from './api';

/** Loads `route`, reloads when it changes or when reload() is called. */
export function useResource<T>(route: string | null, initial: T) {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!route) return;
    let active = true;
    setLoading(true); setError('');
    api<T>(route).then(result => { if (active) setData(result); })
      .catch(e => { if (active) setError((e as Error).message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [route, revision]);
  const reload = useCallback(() => setRevision(x => x + 1), []);
  return {data, setData, loading, error, reload};
}

/** Runs a mutation, then calls onDone; exposes busy/error/notice for the UI. */
export function useMutation(onDone: () => void, savedText: string) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  /** Any async change (e.g. a file upload) with the same busy / error / saved feedback. */
  async function run(task: () => Promise<unknown>) {
    setBusy(true); setError(''); setNotice('');
    try { await task(); setNotice(savedText); onDone(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const mutate = (route: string, method: string, body?: unknown) => run(() => api(route, method, body));
  return {busy, error, notice, mutate, run};
}
