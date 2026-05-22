import { useAuth } from '../context/AuthContext.jsx';

export default function Sidebar({ view, setView, theme, toggleTheme }) {
  const { walletAddress, connectWallet, disconnectWallet } = useAuth();
  return (
    <aside className="sidebar">
      <div className="sb-logo" onClick={() => setView('dashboard')} style={{ cursor: 'pointer' }}>
        <svg width="46" height="46" viewBox="0 0 100 100" fill="none">
          <defs>
            <linearGradient id="logoAccent" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--accent)" />
              <stop offset="100%" stopColor="#fff" />
            </linearGradient>
          </defs>
          {/* Synap 'S' Shape */}
          <path d="M80 25H40L30 50h40l-10 25H20" stroke="url(#logoAccent)" strokeWidth="12" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
          <circle cx="50" cy="50" r="40" stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>
        </svg>
      </div>
      <nav className="sb-nav">
        <a className={`sb-item${view === 'dashboard' ? ' active' : ''}`} href="#" title="Dashboard"
           style={{ '--hover-color': '#00d2d3' }}
           onClick={e => { e.preventDefault(); setView('dashboard'); }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
          </svg>
        </a>
        <a className={`sb-item${view === 'charts' ? ' active' : ''}`} href="#" title="Chart"
           style={{ '--hover-color': '#10ac84' }}
           onClick={e => { e.preventDefault(); setView('charts'); }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </a>
        <a className={`sb-item${view === 'strategies' ? ' active' : ''}`} href="#" title="Strategy"
           style={{ '--hover-color': '#6c5ce7' }}
           onClick={e => { e.preventDefault(); setView('strategies'); }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
          </svg>
        </a>
        <a className={`sb-item${view === 'ai' ? ' active' : ''}`} href="#" title="AI Hub"
           style={{ '--hover-color': '#ff9f43' }}
           onClick={e => { 
             e.preventDefault(); 
             if (view === 'ai') {
               window.dispatchEvent(new Event('resetAIPage'));
             }
             setView('ai'); 
           }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/>
            <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/>
          </svg>
        </a>
        <a className={`sb-item${view === 'proposals' ? ' active' : ''}`} href="#" title="Feedback"
           style={{ '--hover-color': '#fbc531' }}
           onClick={e => { e.preventDefault(); setView('proposals'); }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </a>
        <a className={`sb-item${view === 'settings' ? ' active' : ''}`} href="#" title="Settings"
           style={{ '--hover-color': '#ff6b6b' }}
           onClick={e => { e.preventDefault(); setView('settings'); }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </a>
        <a className="sb-item theme-toggle" href="#" title={theme === 'light' ? 'Dark Mode' : 'Light Mode'}
           style={{ '--hover-color': '#feca57' }}
           onClick={e => { e.preventDefault(); toggleTheme(); }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            {theme === 'light' 
              ? <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              : <>
                  <circle cx="12" cy="12" r="5"/>
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                </>
            }
          </svg>
        </a>
        <a className={`sb-item ${walletAddress ? 'active' : ''}`} href="#" title={walletAddress ? 'Disconnect Wallet' : 'Connect Wallet'}
           style={{ '--hover-color': walletAddress ? '#ff6b6b' : '#1dd1a1', marginTop: 'auto' }}
           onClick={async e => { 
             e.preventDefault(); 
             if (walletAddress) disconnectWallet();
             else await connectWallet(); 
           }}>
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
            <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
            <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
          </svg>
        </a>
      </nav>
    </aside>
  );
}
