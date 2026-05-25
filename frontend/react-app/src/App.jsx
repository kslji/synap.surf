import { useState, useEffect, lazy, Suspense } from 'react';
import { useDashboard } from './hooks/useDashboard.js';
import Sidebar from './components/Sidebar.jsx';
import RightPanel from './components/RightPanel.jsx';
import Dashboard from './components/dashboard/Dashboard.jsx';
import LandingPage from './components/LandingPage.jsx';
import { ToastProvider } from './components/Toast.jsx';

// Lazy load heavy pages — they won't be downloaded until user navigates to them
// This splits the 571KB bundle into smaller chunks, making initial load ~3x faster
const MultiChartTerminal = lazy(() => import('./components/charts/MultiChartTerminal.jsx'));
const StrategyTerminal   = lazy(() => import('./components/strategies/StrategyTerminal.jsx'));
const ProposalPage       = lazy(() => import('./components/proposals/ProposalPage.jsx'));
const Settings           = lazy(() => import('./components/Settings.jsx'));
const AIPage             = lazy(() => import('./components/AIPage.jsx'));
import { useAuth } from './context/AuthContext.jsx';

const getInitialTheme = () => {
  const storedTheme = localStorage.getItem('theme');
  const defaultVersion = localStorage.getItem('theme_default_v2');

  if (!defaultVersion) {
    localStorage.setItem('theme_default_v2', 'dark');
    if (!storedTheme || storedTheme === 'light') {
      localStorage.setItem('theme', 'dark');
      return 'dark';
    }
  }

  return storedTheme || 'dark';
};

function MobileDesktopNotice() {
  const [showNotice, setShowNotice] = useState(false);

  useEffect(() => {
    const dismissed = sessionStorage.getItem('desktop_notice_dismissed') === 'true';
    const isMobileViewport = window.matchMedia('(max-width: 767px)').matches;
    const isTouchDevice = window.matchMedia('(pointer: coarse)').matches;

    if (!dismissed && isMobileViewport && isTouchDevice) {
      setShowNotice(true);
    }
  }, []);

  const dismissNotice = () => {
    sessionStorage.setItem('desktop_notice_dismissed', 'true');
    setShowNotice(false);
  };

  if (!showNotice) return null;

  return (
    <div className="mobile-desktop-notice" role="dialog" aria-modal="true" aria-labelledby="mobileDesktopNoticeTitle">
      <div className="mobile-desktop-notice-card">
        <div className="mobile-desktop-notice-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="12" rx="2" />
            <path d="M8 20h8" />
            <path d="M12 16v4" />
          </svg>
        </div>
        <h2 id="mobileDesktopNoticeTitle">Best viewed on desktop</h2>
        <p>
          Synap has advanced charts, AI trading controls, and portfolio panels. For the best user experience, please open it on a desktop or laptop.
        </p>
        <button type="button" onClick={dismissNotice}>Continue on mobile</button>
      </div>
    </div>
  );
}

export default function App() {
  const { connectWallet } = useAuth();
  const [showLanding, setShowLanding] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('landing') === 'true' || !localStorage.getItem('seen_landing');
  });
  const [view, setView] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('view') || localStorage.getItem('app_view') || 'dashboard';
  });
  
  const changeView = (newView) => {
    setView(newView);
    const url = new URL(window.location);
    url.searchParams.set('view', newView);
    window.history.pushState({ view: newView }, '', url);
  };

  useEffect(() => {
    localStorage.setItem('app_view', view);
  }, [view]);

  useEffect(() => {
    const handleTrigger = async () => {
      try {
        const address = await connectWallet('metamask');
        if (address && fetchAll) fetchAll();
      } catch (e) {
        console.error("Wallet connect failed:", e);
      }
    };
    window.addEventListener('trigger_wallet_connect', handleTrigger);
    
    return () => window.removeEventListener('trigger_wallet_connect', handleTrigger);
  }, [connectWallet]);

  // Handle browser Back/Forward buttons
  useEffect(() => {
    const onPopState = (e) => {
      const params = new URLSearchParams(window.location.search);
      if (params.get('landing') === 'true') {
        setShowLanding(true);
        return;
      }

      setShowLanding(false);
      const newView = e.state?.view || params.get('view') || 'dashboard';
      setView(newView);
      // Ensure nested views like the AI chat are cleared when navigating back
      window.dispatchEvent(new Event('resetAIPage'));
    };

    if (!window.history.state) {
      const url = new URL(window.location);
      url.searchParams.set('view', view);
      window.history.replaceState({ view }, '', url);
    }

    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [view]);

  const [tradingMode, setTradingMode] = useState(() => localStorage.getItem('trading_mode') || 'bot');
  const [theme, setTheme] = useState(getInitialTheme);
  const { stats, trades, decisions, perps, intel, topCoins, fetchAll } = useDashboard();

  const safeStats = stats || { equity: 0, pnl_pct: 0, win_rate: 0, realized_pnl: 0, total_trades: 0, positions: [], last_updated: '' };
  const safeTrades = trades || [];
  const safeDecisions = decisions || [];
  const safePerps = perps || [];
  const safeIntel = intel || { market_view: 'Syncing market data...', fear_greed: null, trending_coins: [], trending_narratives: [] };

  const handleSetTradingMode = (mode) => {
    localStorage.setItem('trading_mode', mode);
    setTradingMode(mode);
  };

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const openLanding = () => {
    const url = new URL(window.location);
    url.searchParams.set('landing', 'true');
    window.history.pushState({ landing: true }, '', url);
    setShowLanding(true);
  };

  const launchApp = () => {
    const url = new URL(window.location);
    url.searchParams.delete('landing');
    url.searchParams.set('view', view);
    window.history.pushState({ view }, '', url);
    setShowLanding(false);
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const renderView = () => {
    switch (view) {
      case 'dashboard':
        return (
          <Dashboard
            stats={safeStats}
            trades={safeTrades}
            perps={safePerps}
            intel={safeIntel}
            onShowCharts={() => changeView('charts')}
            onRefresh={fetchAll}
          />
        );
      case 'charts':
        return (
          <MultiChartTerminal
            coins={topCoins}
            theme={theme}
            onBack={() => changeView('dashboard')}
          />
        );
      case 'strategies':
        return <StrategyTerminal />;
      case 'proposals':
        return <ProposalPage />;
      case 'settings':
        return <Settings />;
      case 'ai':
        return <AIPage />;
      default:
        return null;
    }
  };

  if (showLanding) {
    return (
      <ToastProvider>
        <LandingPage onLaunch={launchApp} theme={theme} toggleTheme={toggleTheme} />
        <MobileDesktopNotice />
      </ToastProvider>
    );
  }

  return (
    <ToastProvider>
      <div className="shell">
        <Sidebar view={view} setView={changeView} theme={theme} toggleTheme={toggleTheme} onHome={openLanding} />
        <Suspense fallback={
          <div className="main-content route-loading">
            <div className="route-loading-card">Loading workspace...</div>
          </div>
        }>
          {renderView()}
        </Suspense>
        {view !== 'strategies' && view !== 'proposals' && view !== 'settings' && view !== 'ai' && (
          <RightPanel
            view={view}
            stats={safeStats}
            decisions={safeDecisions}
            tradingMode={tradingMode}
            setTradingMode={handleSetTradingMode}
          />
        )}
      </div>
      <MobileDesktopNotice />
    </ToastProvider>
  );
}
