import {languageName, useI18n, type Lang} from '../services/i18n';
import {useMutation, useResource} from '../services/useResource';
import {dateTime} from '../services/format';
import {LanguagePicker, LanguageSelect, Messages} from '../components/ui';
import {useEffect, useState} from 'react';
import {api, type Row} from '../services/api';
import {Icon} from '../components/Icon';
import {SOURCES, sourceTitle} from '../services/sources';

/** Any bot text in any language, edited without touching the code; languages switched on and off. */
function Translations({revision}: {revision: number}) {
  const {t} = useI18n();
  const langs = useResource<Row[]>(`admin/translations?r=${revision}`, []);
  const [code, setCode] = useState('');
  const [query, setQuery] = useState('');
  const [edits, setEdits] = useState<Record<string, string>>({});
  const current = code || (langs.data.find(l => l.code !== 'en')?.code ?? 'en');
  const texts = useResource<Row[]>(`admin/translations/${current}?r=${revision}`, []);
  const {busy, error, notice, run} = useMutation(() => { texts.reload(); langs.reload(); setEdits({}); }, t('saved'));
  const shown = texts.data.filter(x => !query || (x.key + ' ' + x.english + ' ' + x.default + ' ' + x.value).toLowerCase().includes(query.toLowerCase()));
  const language = langs.data.find(l => l.code === current);
  return <section className="panel settings youtube-access">
    <div className="panel-title">
      <div><h2>{t('translations')}</h2><p>{t('translationsHint')}</p></div>
    </div>
    <Messages error={langs.error || texts.error || error} notice={notice}/>
    <ul className="proxy-list">{langs.data.map(l => <li key={l.code}>
      <button className={'ghost' + (l.code === current ? ' active' : '')} onClick={() => { setCode(l.code); setEdits({}); }}>{l.name}</button>
      <span className={'badge ' + (l.enabled ? 'active' : 'offline')}>{l.enabled ? t('on') : t('off')}</span>
      {l.edited > 0 && <span className="badge">{t('editedTexts').replace('{count}', String(l.edited))}</span>}
      {!l.fallback && <button disabled={busy} onClick={() => run(() => api(`admin/translations/${l.code}/${l.enabled ? 'disable' : 'enable'}`, 'POST'))}>
        {l.enabled ? t('igDisable') : t('igEnable')}</button>}
    </li>)}</ul>
    <label>{t('search')}<input value={query} onChange={e => setQuery(e.target.value)} placeholder="welcome, premium…"/></label>
    <div className="translation-list" dir={language?.rtl ? 'rtl' : 'ltr'}>{shown.slice(0, 80).map(x => <label key={x.key}>
      <span><code>{x.key}</code>{x.placeholders?.length ? <small> · {x.placeholders.map((p: string) => `{${p}}`).join(' ')}</small> : null}</span>
      <textarea rows={2} value={edits[x.key] ?? x.value} placeholder={x.default || x.english}
        onChange={e => setEdits({...edits, [x.key]: e.target.value})}/>
    </label>)}</div>
    {shown.length > 80 && <p className="hint">{t('narrowSearch').replace('{count}', String(shown.length))}</p>}
    <div className="row-actions">
      <button className="primary" disabled={busy || !Object.keys(edits).length} onClick={() => run(() => api(`admin/translations/${current}`, 'PUT', {texts: edits}))}>{t('save')}</button>
    </div>
  </section>;
}

/** health checks every 5 minutes and alerts to a Telegram chat. */
function Monitoring({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const state = useResource<Row>(`admin/monitoring?r=${revision}`, {});
  const {busy, error, notice, run} = useMutation(() => state.reload(), t('saved'));
  const [form, setForm] = useState<Row | null>(null);
  const settings = form ?? state.data.settings ?? {};
  const status = state.data.status;
  const set = (patch: Row) => setForm({...settings, ...patch});
  return <section className="panel settings youtube-access">
    <div className="panel-title">
      <div><h2>{t('monitoring')}</h2><p>{t('monitoringHint')}</p></div>
      {status && <span className={'badge ' + (status.problems?.length ? 'failed' : 'active')}>{status.problems?.length ? t('problemsFound').replace('{count}', String(status.problems.length)) : t('allGood')}</span>}
    </div>
    <Messages error={state.error || error} notice={notice}/>
    {status && <>
      <ul className="proxy-list">{(status.problems ?? []).map((p: Row) => <li key={p.kind}><Icon name="alert" size={16}/>{p.text}</li>)}</ul>
      <p className="cookies-status"><Icon name="storage" size={16}/>{t('diskFree').replace('{free}', (status.disk.free / 1e9).toFixed(1)).replace('{total}', (status.disk.total / 1e9).toFixed(1))}
        {' · '}{t('lastCheck').replace('{date}', dateTime(status.checked_at, lang))}</p>
    </>}
    <div className="fields">
      <label>{t('alertChat')}<input value={settings.chat_id ?? ''} placeholder="-1001234567890" onChange={e => set({chat_id: e.target.value.trim()})}/><small>{t('alertChatHint')}</small></label>
      <label>{t('diskMinGb')}<input type="number" min={0} value={settings.disk_min_gb ?? 5} onChange={e => set({disk_min_gb: Number(e.target.value)})}/></label>
      <label>{t('errorRateAlert')}<input type="number" min={1} max={100} value={settings.error_rate ?? 50} onChange={e => set({error_rate: Number(e.target.value)})}/></label>
      <label>{t('queueMinutes')}<input type="number" min={1} value={settings.queue_minutes ?? 15} onChange={e => set({queue_minutes: Number(e.target.value)})}/></label>
      <label>{t('botSilentMinutes')}<input type="number" min={1} value={settings.bot_silent_minutes ?? 5} onChange={e => set({bot_silent_minutes: Number(e.target.value)})}/></label>
      <label>{t('alertEmails')}<input value={settings.email_to ?? ''} placeholder="admin@example.com, ops@example.com" onChange={e => set({email_to: e.target.value})}/></label>
      <label>{t('alertEmailFrom')}<input value={settings.email_from ?? ''} placeholder="alerts@your-domain.com" onChange={e => set({email_from: e.target.value})}/></label>
      <label>{t('alertEmailProvider')}<select value={settings.email_provider ?? ''} onChange={e => set({email_provider: e.target.value})}>
        <option value="">—</option><option value="sendgrid">SendGrid</option><option value="resend">Resend</option></select></label>
      <label>{t('alertEmailKey')}<input type="password" autoComplete="off" value={settings.email_key ?? ''} placeholder={settings.email_key_set ? '••••••••' : ''}
        onChange={e => set({email_key: e.target.value})}/><small>{t('alertEmailHint')}</small></label>
    </div>
    <div className="row-actions">
      <button className="primary" disabled={busy || !form} onClick={() => run(async () => {
        const {email_key_set, ...body} = settings;
        state.setData(await api('admin/monitoring', 'PUT', {...body, email_key: body.email_key ?? ''})); setForm(null);
      })}>{t('save')}</button>
      <button disabled={busy} onClick={() => run(async () => state.setData(await api('admin/monitoring/check', 'POST')))}>{t('checkNow')}</button>
    </div>
  </section>;
}

const PLATFORMS = SOURCES;
const NUMBERS = ['daily_jobs', 'max_download_bytes', 'max_upload_bytes', 'media_retention_days', 'retention_days'];

export function Settings({revision, lang: uiLang, setLang}: {revision: number; lang: Lang; setLang: (l: Lang) => void}) {
  const {t, lang} = useI18n();
  const policy = useResource<Row>(`admin/settings?r=${revision}`, {});
  const audit = useResource<Row[]>(`admin/audit?r=${revision}`, []);
  const {busy, error, notice, mutate} = useMutation(() => { policy.reload(); audit.reload(); }, t('saved'));
  const s = policy.data;
  const set = (patch: Row) => policy.setData({...s, ...patch});
  return <>
    <Messages error={policy.error || error} notice={notice}/>
    <section className="panel settings">
      <label>{t('language')}<LanguageSelect lang={uiLang} onChange={setLang}/></label>
    </section>
    {s.daily_jobs !== undefined && <section className="panel settings">
      <h2>{t('limits')}</h2>
      <form onSubmit={e => { e.preventDefault(); const {languages, ...body} = s; mutate('admin/settings', 'PATCH', body); }}>
        <div className="fields">
          {NUMBERS.map(key => <label key={key}>{t(key)}<input type="number" min="1" required value={s[key]} onChange={e => set({[key]: Number(e.target.value)})}/></label>)}
          <label>{t('default_language')}<LanguagePicker value={s.default_language} label={t('default_language')} onChange={code => set({default_language: code})}
            names={Object.fromEntries(Object.entries(s.languages ?? {}).map(([code, name]) => [code, languageName(code, String(name))]))}/></label>
        </div>
        <fieldset><legend>{t('enabled_platforms')}</legend>{PLATFORMS.map(p => <label className="checkbox" key={p}>
          <input type="checkbox" checked={s.enabled_platforms.includes(p)} onChange={e => set({enabled_platforms: e.target.checked ? [...s.enabled_platforms, p] : s.enabled_platforms.filter((v: string) => v !== p)})}/>{sourceTitle(p)}
        </label>)}</fieldset>
        <button className="primary" disabled={busy}>{t('save')}</button>
      </form>
    </section>}
    <Translations revision={revision}/>
    <Monitoring revision={revision}/>
    <section className="panel audit">
      <div className="panel-title"><h2>{t('audit')}</h2></div>
      <div className="table-wrap"><table>
        <thead><tr>{['created', 'admin', 'action', 'target'].map(k => <th key={k}>{t(k)}</th>)}</tr></thead>
        <tbody>{audit.data.map(a => <tr key={a.id}><td data-label={t('created')}>{dateTime(a.created_at, lang)}</td><td data-label={t('admin')}>{a.admin}</td><td data-label={t('action')}>{a.action}</td><td data-label={t('target')}>{a.target}</td></tr>)}</tbody>
      </table></div>
    </section>
  </>;
}
