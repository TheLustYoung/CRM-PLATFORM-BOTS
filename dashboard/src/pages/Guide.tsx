import {useI18n} from '../services/i18n';
import {Icon} from '../components/Icon';
import {BotGuideCards} from '../components/BotGuide';

const SECTIONS: {title: string; icon: string; items: string[]}[] = [
  {title: 'guideMenuTitle', icon: 'menu', items: ['guide_menu_1', 'guide_menu_2', 'guide_menu_3']},
  {title: 'guideAdminTitle', icon: 'shield', items: ['guide_admin_1', 'guide_admin_2', 'guide_admin_3', 'guide_admin_4', 'guide_admin_5']},
  {title: 'guideTipsTitle', icon: 'alert', items: ['guide_tip_1', 'guide_tip_2', 'guide_tip_3']},
];

export function Guide({revision}: {revision: number}) {
  const {t} = useI18n();
  return <div className="grid">
    <section className="panel">
      <div className="panel-title">
        <div><h2>{t('guideTitle')}</h2><p>{t('guideSub')}</p></div>
        <a className="button" href="/admin-guide.pdf" target="_blank" rel="noreferrer"><Icon name="files" size={16}/>{t('adminGuidePdf')}</a>
      </div>
      <BotGuideCards revision={revision}/>
    </section>
    <div className="guide-sections">{SECTIONS.map(s => <section className="panel" key={s.title}>
      <div className="panel-title"><h2>{t(s.title)}</h2><span className="stat-icon"><Icon name={s.icon} size={16}/></span></div>
      <ul className="guide-notes">{s.items.map(k => <li key={k}><Icon name="check" size={16}/><span>{t(k)}</span></li>)}</ul>
    </section>)}</div>
  </div>;
}
