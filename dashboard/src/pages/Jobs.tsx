import {useState} from 'react';
import {useI18n} from '../services/i18n';
import {useResource} from '../services/useResource';
import {dateTime} from '../services/format';
import {Badge, Empty, Messages, Pagination} from '../components/ui';
import type {Row} from '../services/api';
import {useAccess} from '../services/access';
import {JobPreview, UserPreview} from '../components/JobPreview';

export function Jobs({revision, userId, clearUser}: {revision: number; userId: number | null; clearUser: () => void}) {
  const {t, lang} = useI18n();
  const {can} = useAccess();
  const [viewing, setViewing] = useState<string | null>(null), [user, setUser] = useState<number | null>(null);
  const [offset, setOffset] = useState(0), [status, setStatus] = useState(''), [bot, setBot] = useState('');
  const query = `offset=${offset}` + (userId ? `&user_id=${userId}` : '') + (status ? `&status=${status}` : '') + (bot ? `&bot_id=${bot}` : '');
  const jobs = useResource<Row[]>(`admin/jobs?${query}&r=${revision}`, []);
  return <>
    <Messages error={jobs.error}/>
    <section className="panel">
      <div className="filters">
        <select aria-label={t('status')} value={status} onChange={e => { setStatus(e.target.value); setOffset(0); }}>
          <option value="">{t('allStatuses')}</option>
          {['queued', 'processing', 'completed', 'failed'].map(s => <option key={s} value={s}>{t(s)}</option>)}
        </select>
        <select aria-label={t('bots')} value={bot} onChange={e => { setBot(e.target.value); setOffset(0); }}>
          <option value="">{t('allBots')}</option>
          {['video', 'media', 'files'].map(b => <option key={b} value={b}>{b}</option>)}
        </select>
        {userId && <button onClick={clearUser}>{t('user')}: {userId} ✕</button>}
      </div>
      <div className="table-wrap"><table>
        <thead><tr>{['type', 'platform', 'user', 'status', 'created', 'error', 'actions'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{jobs.data.map(j => <tr key={j.id}>
          <td data-label=""><strong>{t(j.kind)}</strong><small title={j.id}>{j.id.slice(0, 8)}</small></td>
          <td data-label={t('platform')}>{j.platform}<small title={j.source_url ?? ''}>{j.source_url ? j.source_url.slice(0, 48) : j.selected_format || '—'}</small></td>
          <td data-label={t('user')}>{j.user_id}<small>{j.bot_id}</small></td>
          <td data-label={t('status')}><Badge status={j.status}/><small>{t('attempts')}: {j.attempts}</small></td>
          <td data-label={t('created')}>{dateTime(j.created_at, lang)}</td>
          <td data-label={t('error')}>{j.error || '—'}</td>
          <td data-label={t('actions')}><div className="row-actions">
            <button onClick={() => setViewing(j.id)}>👁 {t('fileView')}</button>
            {can('users.view') && <button onClick={() => setUser(j.user_id)}>👤 {t('userData')}</button>}
          </div></td>
        </tr>)}</tbody>
      </table></div>
    </section>
    <Empty show={!jobs.loading && jobs.data.length === 0}/>
    <Pagination offset={offset} count={jobs.data.length} onChange={setOffset}/>
    {viewing && <JobPreview id={viewing} onClose={() => setViewing(null)}
                            onUser={can('users.view') ? id => { setViewing(null); setUser(id); } : undefined}/>}
    {user !== null && <UserPreview id={user} onClose={() => setUser(null)}/>}
  </>;
}
