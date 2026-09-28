import { useLanguage } from '../language';
export function Header() {
  const { language, setLanguage, t } = useLanguage();
  return <header className="customer-header">
    <div className="brand"><span className="brand-icon" aria-hidden="true">SF</span><div><strong>SevaFlow</strong><small>{t('SERVICE COUNTER', 'सेवा काउंटर')}</small></div></div>
    <div className="language-toggle" role="group" aria-label={t('Language', 'भाषा')}>
      <button type="button" aria-pressed={language === 'en'} onClick={() => setLanguage('en')}>EN</button>
      <button type="button" aria-pressed={language === 'hi'} onClick={() => setLanguage('hi')}>हिंदी</button>
    </div>
  </header>;
}
