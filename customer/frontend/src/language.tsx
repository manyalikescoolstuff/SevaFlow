import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

type Language = 'en' | 'hi';
const LanguageContext = createContext({
  language: 'en' as Language,
  setLanguage: (_value: Language) => {},
  t: (english: string, _hindi: string) => english,
});
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, update] = useState<Language>(() => {
    try { return localStorage.getItem('sevaflow_language') === 'hi' ? 'hi' : 'en'; }
    catch { return 'en'; }
  });
  const setLanguage = (value: Language) => {
    update(value);
    document.documentElement.lang = value;
    try { localStorage.setItem('sevaflow_language', value); } catch { /* UI still works */ }
  };
  useEffect(() => { document.documentElement.lang = language; }, [language]);
  return <LanguageContext.Provider value={{ language, setLanguage, t: (en, hi) => language === 'hi' ? hi : en }}>{children}</LanguageContext.Provider>;
}
export const useLanguage = () => useContext(LanguageContext);
