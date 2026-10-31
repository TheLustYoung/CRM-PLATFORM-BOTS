import {useEffect, useMemo, useRef, useState} from 'react';
import {useI18n} from '../services/i18n';
import {useMutation, useResource} from '../services/useResource';
import {dateTime, number} from '../services/format';
import {Empty, Messages} from '../components/ui';
import {Icon} from '../components/Icon';
import {PostEditor, fromTelegram, type PostEditorHandle} from '../components/PostEditor';
import {api, ApiError, type Row} from '../services/api';

const TEXT_LIMIT = 4096, CAPTION_LIMIT = 1024, MAX_BUTTONS = 6;
type Button = {text: string; url: string};

async function postForm<T = Row>(route: string, fields: Record<string, string | Blob | null>): Promise<T> {
  const body = new FormData();
  Object.entries(fields).forEach(([key, value]) => { if (value !== null) body.append(key, value); });
  const response = await fetch('/api/' + route, {method: 'POST', credentials: 'include', body});
  const payload = await response.json().catch(() => ({detail: `HTTP ${response.status}`}));
  if (!response.ok) throw new ApiError(response.status, typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail));
  return payload;
}

/** datetime-local value (local time) ↔ ISO with the browser's time zone. */
const toLocalInput = (iso: string) => { const d = new Date(iso); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16); };

/** The channel post as Telegram shows it. */
function Preview({html, media, kind, buttons, title}: {html: string; media: string | null; kind: string | null; buttons: Button[]; title: string}) {
  const {t} = useI18n();
  return <div className="tg-chat" aria-label={t('preview')}>
    <div className="tg-bubble">
      <div className="tg-from">{title}</div>
      {media && kind === 'video' && <video src={media} controls muted playsInline/>}
      {media && kind !== 'video' && <img src={media} alt=""/>}
      {html ? <div className="tg-text" dir="auto" dangerouslySetInnerHTML={{__html: fromTelegram(html)}}/>
        : !media && <div className="tg-text tg-empty">{t('postPlaceholder')}</div>}
      <span className="tg-time">👁 · {new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}</span>
    </div>
    {buttons.filter(b => b.text).map((b, i) => <div className="tg-button" key={i}>{b.text} ↗</div>)}
  </div>;
}

function Rights({rights}: {rights: Row}) {
  const {t} = useI18n();
  return <>{[['can_post_messages', 'rightPost'], ['can_edit_messages', 'rightEdit'], ['can_delete_messages', 'rightDelete'], ['can_pin_messages', 'rightPin']]
    .map(([key, label]) => <span key={key} className={'badge ' + (rights?.[key] ? 'active' : 'failed')}>{rights?.[key] ? '✓' : '✕'} {t(label)}</span>)}</>;
}

/** Every connected bot: a tick to use it with the channel and a lamp — green when it is an administrator there. */
function BotPicker({statuses, picked, all, onToggle, onAll}: {statuses: Row[]; picked: string[]; all: boolean; onToggle: (bot: string) => void; onAll: () => void}) {
  const {t} = useI18n();
  return <div className="bot-picker">
    <div className="bot-picker-head"><span>{t('channelBots')}</span>
      <button type="button" className={all ? 'primary' : ''} onClick={onAll}>{all ? '✓ ' : ''}{t('channelAllBots')}</button></div>
    <ul className="proxy-list">{statuses.map(b => {
      const on = all || picked.includes(b.bot), known = b.admin === true || b.admin === false;
      return <li key={b.bot} className={(known ? (b.admin ? 'is-ok' : 'is-bad') : '') + (on ? '' : ' is-dim')}>
        <label className="checkbox pick"><input type="checkbox" checked={on} disabled={all} onChange={() => onToggle(b.bot)}/>
          <span className="lamp" title={b.admin ? t('channelBotAdmin') : t('channelNotAdmin')}/><code>{b.bot}</code></label>
        {known && <span className="row-actions"><Rights rights={b.rights}/></span>}
        {b.admin === false && <small className="hint reason">{t('channelNotAdmin')}{b.error ? ` (${b.error})` : ''}</small>}
      </li>;
    })}</ul>
    {statuses.length === 0 && <p className="hint">{t('channelNoBots')}</p>}
  </div>;
}

function ChannelCard({info}: {info: Row}) {
  const {t, lang} = useI18n();
  if (!info?.connected) return info?.error ? <p className="hint reason">⚠ {info.error}</p> : null;
  return <div className="channel-card">
    <div className="channel-head">
      <span className="lamp-dot" data-ok={info.admin ? '1' : '0'}/>
      <div><strong>{info.title}</strong><small>{info.username ? '@' + info.username : t('channelPrivate')}</small></div>
      <div className="channel-members"><b>{number(info.members ?? 0, lang)}</b><small>{t('channelSubscribers')}</small></div>
      {info.link && <a className="button" href={info.link} target="_blank" rel="noreferrer">{t('openInTelegram')} ↗</a>}
    </div>
    <p className={'hint' + (info.posting_bot ? '' : ' reason')}>
      {info.posting_bot ? t('channelPostingAs').replace('{bot}', info.posting_bot) : t('channelNoPoster')}</p>
  </div>;
}

export function Channel({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const [tick, setTick] = useState(0);
  const state = useResource<Row>(`admin/channel?r=${revision}-${tick}`, {});
  const {busy, error, notice, run} = useMutation(() => setTick(x => x + 1), t('saved'));
  const s = state.data, posts: Row[] = s.posts ?? [], bots: string[] = s.bots ?? [];
  const [chat, setChat] = useState(''), [picked, setPicked] = useState<string[]>([]), [all, setAll] = useState(true);
  useEffect(() => {
    if (!s.settings) return;
    setChat(s.settings.chat || ''); setPicked(s.settings.bots ?? []); setAll(s.settings.all || !(s.settings.bots ?? []).length);
  }, [s.settings?.chat, JSON.stringify(s.settings?.bots), s.settings?.all]);
  useEffect(() => {  // bots added in the dashboard later appear in the list by themselves
    const again = () => { if (document.visibilityState === 'visible') setTick(x => x + 1); };
    const timer = setInterval(again, 60000);
    window.addEventListener('focus', again);
    return () => { clearInterval(timer); window.removeEventListener('focus', again); };
  }, []);
  const statuses: Row[] = s.channel?.bots ?? bots.map(b => ({bot: b}));

  const editor = useRef<PostEditorHandle>(null);
  const [html, setHtml] = useState(''), [length, setLength] = useState(0);
  const [media, setMedia] = useState<File | null>(null);
  const [buttons, setButtons] = useState<Button[]>([]);
  const [when, setWhen] = useState(''), [later, setLater] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);
  const mediaUrl = useMemo(() => media ? URL.createObjectURL(media) : null, [media]);
  useEffect(() => () => { if (mediaUrl) URL.revokeObjectURL(mediaUrl); }, [mediaUrl]);
  const kind = media ? (media.type.startsWith('video') ? 'video' : 'photo') : editing?.media_kind ?? null;
  const previewMedia = mediaUrl ?? (editing?.media_kind ? `/api/admin/channel/posts/${editing.id}/media` : null);
  const limit = kind ? CAPTION_LIMIT : TEXT_LIMIT;
  const buttonsOk = buttons.every(b => !b.text.trim() === !b.url.trim());
  const ready = (html.trim() || media || editing?.media_kind) && length <= limit && buttonsOk && (!later || when);
  const connected = !!s.channel?.connected;

  const reset = () => { editor.current?.set(''); setMedia(null); setButtons([]); setWhen(''); setLater(false); setEditing(null); };
  const startEdit = (p: Row) => {
    setEditing(p); editor.current?.set(p.text); setButtons(p.buttons ?? []); setMedia(null);
    setLater(p.status === 'scheduled'); setWhen(p.status === 'scheduled' ? toLocalInput(p.publish_at) : '');
    window.scrollTo({top: 0, behavior: 'smooth'});
  };
  const fields = () => ({text: html, buttons: JSON.stringify(buttons.filter(b => b.text.trim() || b.url.trim())),
                         publish_at: later && when ? new Date(when).toISOString() : ''});
  const setButton = (i: number, patch: Partial<Button>) => setButtons(buttons.map((b, k) => k === i ? {...b, ...patch} : b));

  return <div className="grid ads">
    <section className="panel settings youtube-access">
      <div className="panel-title"><div><h2>{t('channelConnect')}</h2><p>{t('channelConnectHint')}</p></div></div>
      <form className="channel-form" onSubmit={e => { e.preventDefault(); run(() => api('admin/channel', 'PUT', {chat, bots: picked, all})); }}>
        <label>{t('channelId')}<input value={chat} placeholder="@my_channel" spellCheck={false} onChange={e => setChat(e.target.value)}/></label>
        <BotPicker statuses={statuses} picked={picked} all={all} onAll={() => setAll(!all)}
          onToggle={b => setPicked(picked.includes(b) ? picked.filter(x => x !== b) : [...picked, b])}/>
        <div className="row-actions"><button className="primary" disabled={busy || !chat.trim() || (!all && !picked.length)}>{t('saveAndCheck')}</button></div>
      </form>
      <ChannelCard info={s.channel}/>
    </section>

    <section className="panel compose">
      <div className="panel-title"><div><h2>{editing ? t('channelEditPost') : t('channelNewPost')}</h2><p>{t('channelComposeHint')}</p></div>
        {editing && <button type="button" onClick={reset}>{t('cancel')}</button>}</div>
      <div className="compose-body">
        <div className="compose-form">
          <PostEditor ref={editor} limit={limit} length={length} onChange={(value, size) => { setHtml(value); setLength(size); }}/>
          {!editing && <div className="compose-row">
            <label className="file-button secondary"><Icon name="image" size={16}/>{media ? media.name : t('addPhotoOrVideo')}
              <input type="file" accept="image/jpeg,image/png,image/webp,video/mp4" onChange={e => { setMedia(e.target.files?.[0] ?? null); e.target.value = ''; }}/>
            </label>
            {media && <button type="button" className="ghost" onClick={() => setMedia(null)}>{t('removePhotoShort')}</button>}
          </div>}
          <fieldset><legend>{t('channelButtons')}</legend>
            {buttons.map((b, i) => <div className="fields" key={i}>
              <label>{t('adButton')}<input maxLength={64} value={b.text} onChange={e => setButton(i, {text: e.target.value})}/></label>
              <label>{t('adUrl')}<input type="url" value={b.url} placeholder="https://" onChange={e => setButton(i, {url: e.target.value})}/></label>
              <button type="button" className="ghost icon-btn" aria-label={t('remove')} onClick={() => setButtons(buttons.filter((_, k) => k !== i))}><Icon name="close" size={16}/></button>
            </div>)}
            {buttons.length < MAX_BUTTONS && <button type="button" onClick={() => setButtons([...buttons, {text: '', url: ''}])}>+ {t('addButton')}</button>}
          </fieldset>
          {(!editing || editing.status !== 'published') && <fieldset><legend>{t('channelWhen')}</legend>
            <label className="checkbox"><input type="radio" checked={!later} onChange={() => setLater(false)}/>{t('channelNow')}</label>
            <label className="checkbox"><input type="radio" checked={later} onChange={() => setLater(true)}/>{t('channelLater')}</label>
            {later && <input type="datetime-local" value={when} min={toLocalInput(new Date().toISOString())} onChange={e => setWhen(e.target.value)}/>}
          </fieldset>}
          <Messages error={error || state.error} notice={notice && t('done')}/>
          <div className="publish-row">
            <span>{connected ? (s.channel.title ?? '') : t('channelConnectFirst')}</span>
            <button type="button" className="primary" disabled={busy || !ready || !connected} onClick={() => run(async () => {
              if (editing) await postForm(`admin/channel/posts/${editing.id}/edit`, fields());
              else await postForm('admin/channel/posts', {...fields(), media});
              reset();
            })}><Icon name="upload" size={16}/>{editing ? t('saveChanges') : later ? t('channelSchedule') : t('channelPublishNow')}</button>
          </div>
        </div>
        <div className="compose-preview">
          <span className="eyebrow">{t('preview')}</span>
          <Preview html={html} media={previewMedia} kind={kind} buttons={buttons} title={s.channel?.title ?? s.settings?.chat ?? 'Channel'}/>
        </div>
      </div>
    </section>

    <section className="panel">
      <div className="panel-title"><div><h2>{t('channelPosts')}</h2><p>{t('channelViewsNote')}</p></div></div>
      <div className="post-list">{posts.map(p => <article key={p.id} className="post-card">
        <div className="post-card-head">
          <span className={'badge post-' + p.status}>{t('cp_' + p.status)}</span>
          {p.pinned && <span className="badge active">📌 {t('pinned')}</span>}
          <small>{p.status === 'published' ? dateTime(p.published_at, lang) : `⏰ ${dateTime(p.publish_at, lang)}`}
            {p.media_kind ? ` · ${p.media_kind === 'video' ? '🎬' : '🖼'} ${p.media_name ?? ''}` : ''}{p.buttons?.length ? ` · 🔘 ${p.buttons.length}` : ''}</small>
        </div>
        {p.text && <div className="post-snippet" dir="auto" dangerouslySetInnerHTML={{__html: fromTelegram(p.text)}}/>}
        {p.error && <p className="hint reason">⚠ {p.error}</p>}
        <div className="row-actions">
          <button type="button" onClick={() => startEdit(p)}>✏️ {t('edit')}</button>
          {['scheduled', 'failed'].includes(p.status) && <button type="button" disabled={busy}
            onClick={() => run(() => api(`admin/channel/posts/${p.id}/publish`, 'POST'))}>🚀 {t('channelPublishNow')}</button>}
          {p.status === 'published' && <button type="button" disabled={busy}
            onClick={() => run(() => api(`admin/channel/posts/${p.id}/pin`, 'POST', {pin: !p.pinned}))}>📌 {t(p.pinned ? 'unpin' : 'pin')}</button>}
          {p.link && <a className="button" href={p.link} target="_blank" rel="noreferrer">{t('openInTelegram')} ↗</a>}
          <button type="button" className="danger" disabled={busy} onClick={() => confirm(t(p.status === 'published' ? 'channelConfirmDelete' : 'channelConfirmCancel'))
            && run(() => api(`admin/channel/posts/${p.id}/delete`, 'POST'))}>{t(p.status === 'published' ? 'channelDelete' : 'cancel')}</button>
        </div>
      </article>)}</div>
      <Empty show={!state.loading && posts.length === 0}/>
    </section>
  </div>;
}
