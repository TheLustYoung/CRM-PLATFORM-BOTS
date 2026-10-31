import {useState} from 'react';
import {useI18n} from '../services/i18n';
import {BotAppearance} from '../components/BotAppearance';
import {Icon} from '../components/Icon';
import {useMutation, useResource} from '../services/useResource';
import {number} from '../services/format';
import {Badge, Empty, LimitForm, Messages} from '../components/ui';
import type {Row} from '../services/api';
import {useAccess} from '../services/access';

import {BOT_ICONS, SOURCES, sourceTitle} from '../services/sources';

const LIBRARIES = SOURCES.filter(s => s !== 'direct');  // the Video bot serves the free-licence libraries only

export function Bots({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const {can} = useAccess();
  const bots = useResource<Row[]>(`admin/bots?r=${revision}`, []);
  const [editing, setEditing] = useState<Row | null>(null);
  const {busy, error, notice, mutate} = useMutation(bots.reload, t('saved'));
  const save = (bot: Row, patch: Row) => mutate('admin/bots/' + bot.id, 'PATCH',
    {enabled: bot.enabled, daily_limit: bot.daily_limit, welcome_text: bot.welcome_text, ...patch});
  return <>
    <Messages error={bots.error || error} notice={notice}/>
    {editing && <BotAppearance key={editing.id} bot={editing} onClose={() => { setEditing(null); bots.reload(); }}/>}
    <div className="bot-grid">{bots.data.map(bot => <article className="bot-card" key={bot.id}>
      <div className="bot-card-head">
        <span className="bot-icon"><Icon name={BOT_ICONS[bot.id] ?? 'folder'} size={22}/></span>
        <div><h2>{bot.id}</h2><p>{bot.username ? '@' + bot.username : '—'}</p></div>
      </div>
      <div className="badges"><Badge status={bot.enabled ? 'enabled' : 'disabled'}/><Badge status={!bot.configured ? 'unconfigured' : bot.online ? 'online' : 'offline'}/></div>
      <dl className="mini-stats">
        <div><dt>{t('botUsers')}</dt><dd>{number(bot.users, lang)}</dd></div>
        <div><dt>{t('jobsToday')}</dt><dd>{number(bot.jobs_today, lang)}</dd></div>
        <div><dt>{t('errorsToday')}</dt><dd>{number(bot.errors_today, lang)}</dd></div>
      </dl>
      <label>{t('dailyLimit')}<LimitForm value={bot.daily_limit} label={t('dailyLimit')} busy={busy} onSave={v => save(bot, {daily_limit: v})}/></label>
      {bot.id !== 'files' && <fieldset><legend>{t('botPlatforms')}</legend>
        {(bot.id === 'video' ? LIBRARIES : SOURCES).map(p => {
          const on = !bot.platforms?.length || bot.platforms.includes(p);
          const all = bot.id === 'video' ? LIBRARIES : SOURCES;
          return <label className="checkbox" key={p}><input type="checkbox" checked={on} disabled={busy || !can('bots.manage')} onChange={e => {
            const current = bot.platforms?.length ? bot.platforms : all;
            const next = e.target.checked ? [...current, p] : current.filter((x: string) => x !== p);
            save(bot, {platforms: next.length === all.length ? [] : next});
          }}/>{sourceTitle(p)}</label>;
        })}</fieldset>}
      {can('bots.manage') && <form className="welcome" onSubmit={e => {
        e.preventDefault();
        const token = String(new FormData(e.currentTarget).get('token') || '').trim();
        if (token) { e.currentTarget.reset(); mutate(`admin/bots/${bot.id}/token`, 'PUT', {token}); }
      }}>
        <label>{t('botToken')}<input name="token" type="password" autoComplete="off" spellCheck={false} placeholder="123456789:AA…"/></label>
        <small>{t('botTokenHint')}</small>
        <button disabled={busy}>{t('saveToken')}</button>
      </form>}
      <form className="welcome" onSubmit={e => { e.preventDefault(); save(bot, {welcome_text: String(new FormData(e.currentTarget).get('welcome') || '')}); }}>
        <label>{t('welcomeText')}<textarea name="welcome" rows={3} maxLength={2000} defaultValue={bot.welcome_text ?? ''}/></label>
        <small>{t('welcomeHint')}</small>
        <button disabled={busy}>{t('save')}</button>
      </form>
      <div className="bot-actions">
        <button className="primary" disabled={!bot.configured} onClick={() => { setEditing(bot); window.scrollTo({top: 0, behavior: 'smooth'}); }}>🎨 {t('appearance')}</button>
        <button disabled={busy} className={bot.enabled ? 'danger' : 'primary'} onClick={() => save(bot, {enabled: !bot.enabled})}>{t(bot.enabled ? 'disable' : 'enable')}</button>
      </div>
    </article>)}</div>
    <Empty show={!bots.loading && bots.data.length === 0}/>
  </>;
}
