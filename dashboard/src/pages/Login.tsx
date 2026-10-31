import {useState} from 'react';
import {api} from '../services/api';
import {useI18n, type Lang} from '../services/i18n';
import {LanguageSelect} from '../components/ui';
import {Icon} from '../components/Icon';
import {LogoMark, Wordmark} from '../components/Logo';

const FEATURES = [
  {icon: 'bots', title: 'loginF1', text: 'loginF1Text'},
  {icon: 'activity', title: 'loginF2', text: 'loginF2Text'},
  {icon: 'shield', title: 'loginF3', text: 'loginF3Text'},
];

export function Login({onLogin, lang, setLang}: {onLogin: (user: string) => void; lang: Lang; setLang: (l: Lang) => void}) {
  const {t} = useI18n();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [reveal, setReveal] = useState(false);
  const [caps, setCaps] = useState(false);

  return <main className="auth">
    <section className="auth-story" aria-labelledby="auth-headline">
      <Wordmark/>
      <div className="auth-copy">
        <span className="eyebrow">Media Hub</span>
        <h1 id="auth-headline">{t('loginHeadline')}</h1>
        <p>{t('loginLead')}</p>
      </div>
      <ul className="auth-features">{FEATURES.map(f => <li key={f.title}>
        <span className="auth-feature-icon"><Icon name={f.icon} size={18}/></span>
        <div><strong>{t(f.title)}</strong><small>{t(f.text)}</small></div>
      </li>)}</ul>
      <small className="auth-foot">© {new Date().getFullYear()} AfoninWebStudio · v1.0</small>
    </section>

    <section className="auth-panel">
      <div className="auth-top">
        <span className="auth-mobile-brand"><LogoMark size={32}/>Media Hub</span>
        <LanguageSelect lang={lang} onChange={setLang}/>
      </div>
      <form className="auth-card" noValidate={false} onSubmit={async e => {
        e.preventDefault(); setBusy(true); setError('');
        try { const r = await api('auth/login', 'POST', Object.fromEntries(new FormData(e.currentTarget))); onLogin(r.username); }
        catch (err) { setError((err as Error).message); }
        finally { setBusy(false); }
      }}>
        <div className="auth-card-head">
          <LogoMark size={44}/>
          <div><h2>{t('welcome')}</h2><p>{t('loginHint')}</p></div>
        </div>

        <label className="field">{t('username')}
          <span className="input-icon"><Icon name="user" size={16}/>
            <input name="username" autoComplete="username" required maxLength={64} autoFocus/></span>
        </label>
        <label className="field">{t('password')}
          <span className="input-icon"><Icon name="lock" size={16}/>
            <input name="password" type={reveal ? 'text' : 'password'} autoComplete="current-password" required maxLength={256}
              onKeyUp={e => setCaps(e.getModifierState('CapsLock'))}/>
            <button type="button" className="reveal" onClick={() => setReveal(v => !v)} aria-pressed={reveal}
              aria-label={t(reveal ? 'loginHide' : 'loginShow')} title={t(reveal ? 'loginHide' : 'loginShow')}>
              <Icon name={reveal ? 'eyeOff' : 'eye'} size={16}/></button>
          </span>
          {caps && <small className="caps"><Icon name="alert" size={14}/>{t('loginCaps')}</small>}
        </label>

        {error && <div role="alert" className="error">{error}</div>}
        <button className="primary auth-submit" disabled={busy}>
          {busy ? t('loading') : t('login')} {!busy && <Icon name="arrowRight" size={16}/>}
        </button>
        <p className="auth-note"><Icon name="shield" size={14}/>{t('loginSecure')}</p>
      </form>
    </section>
  </main>;
}
