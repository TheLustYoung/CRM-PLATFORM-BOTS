import {useEffect, useState} from 'react';
import {api, upload, type Row} from '../services/api';
import {languageName, useI18n} from '../services/i18n';
import {Messages} from './ui';
import {Flag} from './Flag';

type Command = {command: string; description: string};
type Profile = {name: string; short_description: string; description: string; commands: Command[]};
const EMPTY: Profile = {name: '', short_description: '', description: '', commands: []};

function Counter({value, max}: {value: string; max: number}) {
  return <small className={value.length > max ? 'over' : ''}>{value.length} / {max}</small>;
}

/** Bot name, descriptions, menu commands and profile photo, per language, written straight to Telegram. */
export function BotAppearance({bot, onClose}: {bot: Row; onClose: () => void}) {
  const {t} = useI18n();
  const [lang, setLang] = useState('');
  const [languages, setLanguages] = useState<Record<string, string>>({});
  const [profile, setProfile] = useState<Profile>(EMPTY);
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false);
  const [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [photoRev, setPhotoRev] = useState(0), [hasPhoto, setHasPhoto] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setNotice('');
    api(`admin/bots/${bot.id}/profile?lang=${lang}`)
      .then(r => { if (active) { setProfile({name: r.name, short_description: r.short_description, description: r.description, commands: r.commands}); setLanguages(r.languages); } })
      .catch(e => { if (active) setError(e.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [bot.id, lang]);

  async function run(action: () => Promise<unknown>, done: string) {
    setBusy(true); setError(''); setNotice('');
    try { await action(); setNotice(done); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const save = () => run(async () => {
    const r = await api(`admin/bots/${bot.id}/profile?lang=${lang}`, 'PUT', {...profile, commands: profile.commands.filter(c => c.command.trim())});
    setProfile({name: r.name, short_description: r.short_description, description: r.description, commands: r.commands});
  }, t('saved'));
  const setCommand = (i: number, patch: Partial<Command>) =>
    setProfile({...profile, commands: profile.commands.map((c, j) => j === i ? {...c, ...patch} : c)});
  const label = (code: string) => code ? <><Flag code={code} size={16}/>{languageName(code, languages[code])}</> : t('allLanguages');

  return <section className="panel appearance">
    <div className="panel-title">
      <div><h2>{t('appearance')} · {bot.id}</h2><p>{bot.username ? '@' + bot.username : '—'} · {t('appearanceHint')}</p></div>
      <button onClick={onClose}>{t('close')} ✕</button>
    </div>
    <div className="appearance-body">
      <div className="photo-block">
        {hasPhoto
          ? <img src={`/api/admin/bots/${bot.id}/photo?r=${photoRev}`} alt={t('photo')} onError={() => setHasPhoto(false)}/>
          : <div className="photo-empty">{t('noPhoto')}</div>}
        <label className="file-button">{t('uploadPhoto')}
          <input type="file" accept="image/jpeg,image/png" disabled={busy} onChange={e => {
            const file = e.target.files?.[0];
            e.target.value = '';
            if (file) run(async () => { await upload(`admin/bots/${bot.id}/photo`, file); setHasPhoto(true); setPhotoRev(x => x + 1); }, t('saved'));
          }}/>
        </label>
        {hasPhoto && <button className="danger" disabled={busy} onClick={() => { if (confirm(t('confirmRemovePhoto')))
          run(async () => { await api(`admin/bots/${bot.id}/photo`, 'DELETE'); setHasPhoto(false); }, t('saved')); }}>{t('removePhoto')}</button>}
        <small>{t('photoHint')}</small>
      </div>
      <div className="profile-form">
        <div className="lang-tabs" role="tablist">{['', ...Object.keys(languages).filter(Boolean)].map(code =>
          <button key={code || 'default'} role="tab" aria-selected={lang === code} className={lang === code ? 'active' : ''} onClick={() => setLang(code)}>{label(code)}</button>)}
        </div>
        <Messages error={error} notice={notice}/>
        {loading ? <p className="empty">{t('loading')}</p> : <form onSubmit={e => { e.preventDefault(); save(); }}>
          <label>{t('botName')}<input value={profile.name} maxLength={64} dir="auto" onChange={e => setProfile({...profile, name: e.target.value})}/><Counter value={profile.name} max={64}/></label>
          <label>{t('shortDescription')}<input value={profile.short_description} maxLength={120} dir="auto" onChange={e => setProfile({...profile, short_description: e.target.value})}/><Counter value={profile.short_description} max={120}/></label>
          <label>{t('botDescription')}<textarea rows={5} value={profile.description} maxLength={512} dir="auto" onChange={e => setProfile({...profile, description: e.target.value})}/><Counter value={profile.description} max={512}/></label>
          <fieldset><legend>{t('menuCommands')}</legend>
            {profile.commands.map((c, i) => <div className="command-row" key={i}>
              <span>/</span><input aria-label={t('command')} value={c.command} maxLength={32} pattern="[a-z0-9_]{1,32}" onChange={e => setCommand(i, {command: e.target.value.toLowerCase()})}/>
              <input aria-label={t('commandDescription')} value={c.description} maxLength={256} dir="auto" placeholder={t('commandDescription')} onChange={e => setCommand(i, {description: e.target.value})}/>
              <button type="button" aria-label={t('remove')} onClick={() => setProfile({...profile, commands: profile.commands.filter((_, j) => j !== i)})}>✕</button>
            </div>)}
            <button type="button" onClick={() => setProfile({...profile, commands: [...profile.commands, {command: '', description: ''}]})}>+ {t('addCommand')}</button>
          </fieldset>
          <button className="primary" disabled={busy}>{busy ? t('loading') : t('save')}</button>
        </form>}
      </div>
    </div>
  </section>;
}
