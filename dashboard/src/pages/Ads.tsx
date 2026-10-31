import {useEffect, useMemo, useRef, useState} from 'react';
import {useI18n} from '../services/i18n';
import {useMutation, useResource} from '../services/useResource';
import {dateTime, number} from '../services/format';
import {Empty, Messages} from '../components/ui';
import {Icon} from '../components/Icon';
import {PostEditor, fromTelegram, type PostEditorHandle} from '../components/PostEditor';
import {api, ApiError, type Row} from '../services/api';

const TEXT_LIMIT = 4096, CAPTION_LIMIT = 1024;
const ACTIVE = new Set(['sending', 'deleting']);

/** multipart POST (photo + fields); the session cookie authenticates it. */
async function postForm<T = Row>(route: string, fields: Record<string, string | Blob | null>): Promise<T> {
  const body = new FormData();
  Object.entries(fields).forEach(([key, value]) => { if (value !== null) body.append(key, value); });
  const response = await fetch('/api/' + route, {method: 'POST', credentials: 'include', body});
  const payload = await response.json().catch(() => ({detail: `HTTP ${response.status}`}));
  if (!response.ok) throw new ApiError(response.status, typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail));
  return payload;
}

/** The post as Telegram shows it: photo, formatted text, button. */
function Preview({html, photo, button, bot}: {html: string; photo: string | null; button: {text: string; url: string}; bot: string}) {
  const {t} = useI18n();
  return <div className="tg-chat" aria-label={t('preview')}>
    <div className="tg-bubble">
      <div className="tg-from">{bot}</div>
      {photo && <img src={photo} alt=""/>}
      {html ? <div className="tg-text" dir="auto" dangerouslySetInnerHTML={{__html: fromTelegram(html)}}/>
        : <div className="tg-text tg-empty">{t('postPlaceholder')}</div>}
      <span className="tg-time">{new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}</span>
    </div>
    {button.text && <div className="tg-button">{button.text} ↗</div>}
  </div>;
}

function Progress({item}: {item: Row}) {
  const total = Math.max(item.audience, 1);
  const done = item.status === 'deleting' || item.status === 'deleted' ? item.deleted + item.not_deleted : item.processed;
  const of = item.status === 'deleting' || item.status === 'deleted' ? Math.max(item.delivered, 1) : total;
  return <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={of} aria-valuenow={done}>
    <div style={{width: `${Math.min(100, (done / of) * 100)}%`, background: item.status.startsWith('delet') ? 'var(--danger)' : 'var(--primary)'}}/>
  </div>;
}

export function Ads({revision}: {revision: number}) {
  const {t, lang} = useI18n();
  const [tick, setTick] = useState(0);
  const list = useResource<Row>(`admin/broadcasts?r=${revision}-${tick}`, {});
  const bots: string[] = list.data.bots ?? [];
  const [picked, setPicked] = useState<string[] | null>(null);
  const chosen = picked ?? bots;  // every connected bot by default
  const [skipPremium, setSkipPremium] = useState(true);
  const [html, setHtml] = useState(''), [length, setLength] = useState(0);
  const [photo, setPhoto] = useState<File | null>(null);
  const [buttonText, setButtonText] = useState(''), [buttonUrl, setButtonUrl] = useState('');
  const [chatId, setChatId] = useState(() => { try { return localStorage.getItem('adsTestChat') ?? ''; } catch { return ''; } });
  const editor = useRef<PostEditorHandle>(null);
  const audience = useResource<Row>(chosen.length ? `admin/broadcasts/audience?bots=${chosen.join(',')}&skip_premium=${skipPremium}&r=${tick}` : null, {});
  const {busy, error, notice, run} = useMutation(() => setTick(x => x + 1), t('saved'));
  const photoUrl = useMemo(() => photo ? URL.createObjectURL(photo) : null, [photo]);
  useEffect(() => () => { if (photoUrl) URL.revokeObjectURL(photoUrl); }, [photoUrl]);
  const items: Row[] = list.data.items ?? [];
  useEffect(() => {  // live progress while a post is being sent or deleted
    if (!items.some(i => ACTIVE.has(i.status))) return;
    const timer = setTimeout(() => setTick(x => x + 1), 3000);
    return () => clearTimeout(timer);
  }, [items]);

  const limit = photo ? CAPTION_LIMIT : TEXT_LIMIT;
  const reach = audience.data.total ?? 0;
  const ready = html.trim() && length <= limit && chosen.length > 0 && !!buttonText.trim() === !!buttonUrl.trim();
  const fields = () => ({text: html, button_text: buttonText, button_url: buttonUrl, bots: chosen.join(','), photo});
  const reset = () => { editor.current?.set(''); setPhoto(null); setButtonText(''); setButtonUrl(''); };
  const toggleBot = (bot: string) => setPicked(chosen.includes(bot) ? chosen.filter(b => b !== bot) : bots.filter(b => b === bot || chosen.includes(b)));

  return <div className="grid ads">
    <section className="panel compose">
      <div className="panel-title"><div><h2>{t('composeTitle')}</h2><p>{t('composeHint')}</p></div></div>
      <div className="compose-body">
        <div className="compose-form">
          <PostEditor ref={editor} limit={limit} length={length} onChange={(value, size) => { setHtml(value); setLength(size); }}/>
          <div className="compose-row">
            <label className="file-button secondary"><Icon name="image" size={16}/>{photo ? photo.name : t('addPhoto')}
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => { setPhoto(e.target.files?.[0] ?? null); e.target.value = ''; }}/>
            </label>
            {photo && <button type="button" className="ghost" onClick={() => setPhoto(null)}>{t('removePhotoShort')}</button>}
          </div>
          <fieldset><legend>{t('postButton')}</legend>
            <div className="fields">
              <label>{t('adButton')}<input maxLength={64} value={buttonText} onChange={e => setButtonText(e.target.value)}/></label>
              <label>{t('adUrl')}<input type="url" value={buttonUrl} placeholder="https://" onChange={e => setButtonUrl(e.target.value)}/></label>
            </div>
          </fieldset>
          <fieldset><legend>{t('sendTo')}</legend>
            {bots.map(bot => <label className="checkbox" key={bot}>
              <input type="checkbox" checked={chosen.includes(bot)} onChange={() => toggleBot(bot)}/>
              {bot}{audience.data.per_bot?.[bot] !== undefined && <small> · {number(audience.data.per_bot[bot], lang)}</small>}
            </label>)}
            <label className="checkbox wide"><input type="checkbox" checked={skipPremium} onChange={e => setSkipPremium(e.target.checked)}/>{t('skipPremiumAds')}</label>
          </fieldset>
          <div className="test-row">
            <label>{t('testTitle')}<input inputMode="numeric" placeholder="123456789" value={chatId} onChange={e => setChatId(e.target.value.replace(/\D/g, ''))}/>
              <small>{t('testHint')}</small></label>
            <button type="button" disabled={busy || !ready || !chatId} onClick={() => run(async () => {
              try { localStorage.setItem('adsTestChat', chatId); } catch {}
              await postForm('admin/broadcasts/test', {...fields(), chat_id: chatId});
            })}>{t('sendTest')}</button>
          </div>
          <Messages error={error || list.error} notice={notice && t('done')}/>
          <div className="publish-row">
            <span>{t('audienceTotal').replace('{count}', number(reach, lang))}</span>
            <button type="button" className="primary" disabled={busy || !ready || !reach}
              onClick={() => confirm(t('confirmPublish').replace('{count}', number(reach, lang))) && run(async () => {
                await postForm('admin/broadcasts', {...fields(), skip_premium: String(skipPremium)});
                reset();
              })}><Icon name="upload" size={16}/>{t('publish').replace('{count}', number(reach, lang))}</button>
          </div>
        </div>
        <div className="compose-preview">
          <span className="eyebrow">{t('preview')}</span>
          <Preview html={html} photo={photoUrl} button={{text: buttonText, url: buttonUrl}} bot={chosen[0] ?? 'bot'}/>
        </div>
      </div>
    </section>

    <section className="panel">
      <div className="panel-title"><div><h2>{t('history')}</h2><p>{t('tooOldToDelete').replace('{hours}', String(list.data.delete_window_hours ?? 48))}</p></div></div>
      <div className="post-list">{items.map(item => <article key={item.id} className="post-card">
        <div className="post-card-head">
          <span className={'badge post-' + item.status}>{t('st_' + item.status)}</span>
          <small>{dateTime(item.created_at, lang)} · {item.bots.join(', ')}{item.has_photo ? ` · 🖼 ${t('withPhoto')}` : ''}</small>
        </div>
        <div className="post-snippet" dir="auto" dangerouslySetInnerHTML={{__html: fromTelegram(item.text)}}/>
        <Progress item={item}/>
        <dl className="mini-stats wide post-stats">
          <div><dt>{t('audienceShort')}</dt><dd>{number(item.audience, lang)}</dd></div>
          <div><dt>{t('delivered')}</dt><dd>{number(item.delivered, lang)}</dd></div>
          <div><dt>{t('notDelivered')}</dt><dd>{number(item.failed, lang)}</dd></div>
          <div><dt>{t('removedCount')}</dt><dd>{number(item.deleted, lang)}{item.not_deleted ? <small> · {t('notRemoved')} {number(item.not_deleted, lang)}</small> : null}</dd></div>
        </dl>
        <div className="row-actions">
          <button type="button" onClick={() => { editor.current?.set(item.text); setButtonText(item.button_text ?? ''); setButtonUrl(item.button_url ?? ''); window.scrollTo({top: 0, behavior: 'smooth'}); }}>{t('useAgain')}</button>
          {!['deleting', 'deleted'].includes(item.status) && <button type="button" className="danger" disabled={busy || !item.deletable}
            title={item.deletable ? '' : t('tooOldToDelete').replace('{hours}', String(list.data.delete_window_hours ?? 48))}
            onClick={() => confirm(t('confirmDeletePost')) && run(() => api(`admin/broadcasts/${item.id}/delete`, 'POST'))}>{t('deleteFromChats')}</button>}
        </div>
      </article>)}</div>
      <Empty show={!list.loading && items.length === 0}/>
    </section>
  </div>;
}
