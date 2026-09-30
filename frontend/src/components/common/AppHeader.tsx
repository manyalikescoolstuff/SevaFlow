import { useNavigate } from 'react-router-dom';
import './AppHeader.css';

interface AppHeaderProps {
  /** e.g. "Staff · Counter 01" or "Administrator" */
  contextLabel: string;
  onExit?: () => void;
}

export function AppHeader({ contextLabel, onExit }: AppHeaderProps) {
  const navigate = useNavigate();

  return (
    <header className="app-header">
      <div className="app-header__left">
        <span className="app-header__logo">
          Q<span className="app-header__logo-accent">-FLOW</span>
        </span>
        <span className="app-header__divider" />
        <span className="app-header__context">{contextLabel}</span>
      </div>

      <div className="app-header__right">
        <button
          className="app-header__exit-btn"
          onClick={onExit || (() => navigate('/'))}
        >
          {onExit ? 'Sign out' : '← Switch Role'}
        </button>
      </div>
    </header>
  );
}
