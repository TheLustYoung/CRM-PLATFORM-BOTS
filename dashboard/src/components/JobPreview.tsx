import {Fragment, useState, type ReactNode} from 'react';
import {useI18n} from '../services/i18n';
import {useResource} from '../services/useResource';
import {bytes, dateTime, number} from '../services/format';
import {Badge} from './ui';
import {DownloadLink, MediaView, Modal} from './FilePreview';
import type {Row} from '../services/api';

const duration = (s: number) => [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60]
  .filter((v, i) => v || i).map((v, i) => (i ? String(v).padStart(2, '0') : String(v))).join(':');

/** "View" window of a download: the link, what was found there, the delivered files (playable) and who asked. */
export function JobPreview({id, onClose, onUser}: {id: string; onClose: () => void; onUser?: (userId: number) => void}) {
  const {t, lang} = useI18n();
  const job = useResource<Row>(`admin/jobs/${encodeURIComponent(id)}`, {});
  const [current, setCurrent] = useState(0);
  const j = job.data, info: Row = j.info ?? {}, files: Row[] = (j.files ?? []).filter((f: Row) => !f.deleted);
  const file = files[Math.min(current, files.length - 1)];
  const rows: [string, ReactNode][] = [
    ['status', j.status && <><Badge status={j.status}/>{j.error && <small> {j.error}</small>}</>],
    ['platform', j.platform], ['jobChannel', info.channel], ['jobDuration', info.duration ? duration(Math.round(info.duration)) : null],
    ['jobViews', info.views != null ? number(info.views, lang) : null], ['jobLikes', info.likes != null ? number(info.likes, lang) : null],
    ['jobItems', info.count], ['jobFormat', j.selected_format], ['created', j.created_at && dateTime(j.created_at, lang)],
    ['jobCompleted', j.completed_at && dateTime(j.completed_at, lang)], ['bot', j.bot_id],
  ];
  return <Modal title={info.title || (j.kind ? t(j.kind) : '…')} subtitle={j.id} onClose={onClose}
                footer={file && <DownloadLink file={file}/>}>
    <div className="modal-scroll">
      {job.error && <p className="pad">{job.error}</p>}
      {file && <div className="modal-body"><MediaView file={file} autoPlay={false}/></div>}
      {files.length > 1 && <div className="thumbs">{files.map((f, i) =>
        <button key={f.id} className={i === current ? 'active' : ''} onClick={() => setCurrent(i)}>{i + 1}</button>)}</div>}
      <dl className="details">
        {j.source_url && <><dt>{t('jobLink')}</dt><dd><a href={j.source_url} target="_blank" rel="noreferrer noopener">{j.source_url}</a></dd></>}
        {rows.filter(([, v]) => v !== null && v !== undefined && v !== '').map(([k, v]) => <Fragment key={k}><dt>{t(k)}</dt><dd>{v}</dd></Fragment>)}
        {j.user && <><dt>{t('user')}</dt><dd>
          {j.user.username ? '@' + j.user.username : j.user.first_name || ''} <small>ID {j.user.id}</small>
          {onUser && <button className="link" onClick={() => onUser(j.user.id)}>👤 {t('userData')}</button>}
        </dd></>}
        {files.map(f => <Fragment key={f.id}><dt>{t('fileLabel')}</dt><dd>{f.name} <small>{bytes(f.size)}</small></dd></Fragment>)}
        {info.description && <><dt>{t('jobDescription')}</dt><dd className="pre" dir="auto">{info.description}</dd></>}
      </dl>
      {job.data.id && files.length === 0 && <p className="pad muted">{t('jobNoFiles')}</p>}
    </div>
  </Modal>;
}

/** "User data" window: the same profile as the Users page, read-only. */
export function UserPreview({id, onClose}: {id: number; onClose: () => void}) {
  const {t, lang} = useI18n();
  const user = useResource<Row>(`admin/users/${id}`, {});
  const d = user.data;
  const rows: [string, ReactNode][] = [
    ['ID', d.id], ['userName', d.first_name], ['language', d.language], ['bots_list', (d.bots ?? []).join(', ')],
    ['tier', d.tier || '—'], ['credits', d.credits ?? 0], ['dailyLimit', d.daily_limit ?? '—'],
    ['status', d.banned ? <Badge status="banned"/> : <Badge status="active"/>],
    ['downloadsCount', d.downloads != null && number(d.downloads, lang)], ['uploadsCount', d.uploads != null && number(d.uploads, lang)],
    ['failedCount', d.failed != null && number(d.failed, lang)], ['filesActive', d.files != null && number(d.files, lang)],
    ['joined', d.created_at && dateTime(d.created_at, lang)], ['lastSeen', d.last_seen && dateTime(d.last_seen, lang)],
  ];
  return <Modal title={d.username ? '@' + d.username : `ID ${id}`} subtitle={d.first_name} onClose={onClose}>
    <div className="modal-scroll">
      {user.error && <p className="pad">{user.error}</p>}
      <dl className="details">
        {rows.filter(([, v]) => v !== null && v !== undefined && v !== '' && v !== false)
          .map(([k, v]) => <Fragment key={k}><dt>{k === 'ID' ? k : t(k)}</dt><dd>{v}</dd></Fragment>)}
      </dl>
      {(d.payments ?? []).length > 0 && <div className="pad table-wrap"><table>
        <thead><tr>{['created', 'paymentSource', 'days', 'stars', 'bot'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{d.payments.map((p: Row, i: number) => <tr key={i}>
          <td data-label={t('created')}>{dateTime(p.created_at, lang)}</td><td data-label={t('paymentSource')}>{p.source}</td>
          <td data-label={t('days')}>{p.days}</td><td data-label={t('stars')}>{p.stars || '—'}</td><td data-label={t('bot')}>{p.bot_id ?? '—'}</td>
        </tr>)}</tbody></table></div>}
    </div>
  </Modal>;
}
