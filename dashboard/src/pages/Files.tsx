import {useState} from 'react';
import {useI18n} from '../services/i18n';
import {useMutation, useResource} from '../services/useResource';
import {useAccess} from '../services/access';
import {bytes, dateTime} from '../services/format';
import {Badge, Empty, Messages, Pagination} from '../components/ui';
import type {Row} from '../services/api';
import {FilePreview} from '../components/FilePreview';
import {UserPreview} from '../components/JobPreview';

export function Files({revision, userId, clearUser}: {revision: number; userId: number | null; clearUser: () => void}) {
  const {t, lang} = useI18n();
  const {can} = useAccess();
  const [offset, setOffset] = useState(0);
  const [viewing, setViewing] = useState<Row | null>(null), [user, setUser] = useState<number | null>(null);
  const files = useResource<Row[]>(`admin/files?offset=${offset}${userId ? `&user_id=${userId}` : ''}&r=${revision}`, []);
  const {busy, error, notice, mutate} = useMutation(files.reload, t('saved'));
  return <>
    <Messages error={files.error || error} notice={notice}/>
    <section className="panel">
      {userId && <div className="filters"><button onClick={clearUser}>{t('user')}: {userId} ✕</button></div>}
      <div className="table-wrap"><table>
        <thead><tr>{['name', 'size', 'created', 'expires', 'status', 'actions'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{files.data.map(f => <tr key={f.id}>
          <td data-label=""><strong dir="auto">{f.name}</strong><small>{f.user_id} · {f.bot_id ?? '—'} · {f.mime}</small></td>
          <td data-label={t('size')}>{bytes(f.size)}<small>{t('downloadsShort')}: {f.downloads ?? 0}</small></td>
          <td data-label={t('created')}>{dateTime(f.created_at, lang)}</td>
          <td data-label={t('expires')}>{new Date(f.expires_at).getFullYear() >= 2099 ? '∞ ' + t('permanent') : dateTime(f.expires_at, lang)}</td>
          <td data-label={t('status')}><Badge status={f.deleted ? 'deleted' : f.url ? 'active' : 'revoked'}/></td>
          <td data-label={t('actions')}><div className="row-actions">
            {!f.deleted && <button onClick={() => setViewing(f)}>👁 {t('fileView')}</button>}
            {can('users.view') && <button onClick={() => setUser(f.user_id)}>👤 {t('userData')}</button>}
            {f.url && !f.deleted && <>
              <a href={f.url} target="_blank" rel="noreferrer">{t('open')} ↗</a>
              {can('files.manage') && <button disabled={busy} onClick={() => mutate('admin/files/' + f.id + '/revoke', 'POST')}>{t('revoke')}</button>}
              {can('files.manage') && new Date(f.expires_at).getFullYear() < 2099 &&
                <button disabled={busy} onClick={() => mutate('admin/files/' + f.id + '/keep', 'POST', {days: 0})}>∞ {t('makePermanent')}</button>}
            </>}
            {!f.deleted && can('files.manage') && <button className="danger" disabled={busy} onClick={() => { if (confirm(t('confirmDelete'))) mutate('admin/files/' + f.id, 'DELETE'); }}>{t('remove')}</button>}
          </div></td>
        </tr>)}</tbody>
      </table></div>
    </section>
    <Empty show={!files.loading && files.data.length === 0}/>
    <Pagination offset={offset} count={files.data.length} onChange={setOffset}/>
    {viewing && <FilePreview file={viewing} onClose={() => setViewing(null)}/>}
    {user !== null && <UserPreview id={user} onClose={() => setUser(null)}/>}
  </>;
}
