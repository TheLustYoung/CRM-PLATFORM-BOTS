import {useI18n} from '../services/i18n';
import {useResource} from '../services/useResource';
import type {Row} from '../services/api';
import {Icon} from './Icon';

const BOTS: {id: string; icon: string}[] = [{id: 'video', icon: 'play'}, {id: 'media', icon: 'image'}, {id: 'files', icon: 'folder'}];

/** Three bot cards with numbered steps; shared by the overview and the Guide page. */
export function BotGuideCards({revision}: {revision: number}) {
  const {t} = useI18n();
  const bots = useResource<Row[]>(`admin/bots?r=${revision}`, []);
  const username = (id: string) => bots.data.find(b => b.id === id)?.username as string | undefined;
  return <div className="guide-grid">{BOTS.map(({id, icon}) => {
    const name = username(id);
    return <article className="guide-card" key={id}>
      <div className="guide-card-head">
        <span className="platform-icon"><Icon name={icon} size={18}/></span>
        <div><h3>{t(`guide_${id}_title`)}</h3><small>{name ? '@' + name : '—'}</small></div>
      </div>
      <p>{t(`guide_${id}_text`)}</p>
      <ol className="steps">{[1, 2, 3].map(n => <li key={n}>{t(`guide_${id}_${n}`)}</li>)}</ol>
      {name && <a className="open" href={`https://t.me/${name}`} target="_blank" rel="noreferrer">{t('openBot')} <Icon name="arrowRight" size={14}/></a>}
    </article>;
  })}</div>;
}
