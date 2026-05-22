import { useState, useEffect, lazy, Suspense } from 'react';
import { useDashboard } from './hooks/useDashboard.js';
import Sidebar from './components/Sidebar.jsx';
import RightPanel from './components/RightPanel.jsx';
import Dashboard from './components/dashboard/Dashboard.jsx';
import { ToastProvider } from './components/Toast.jsx';

// Lazy load heavy pages — they won't be downloaded until user navigates to them
// This splits the 571KB bundle into smaller chunks, making initial load ~3x faster
const MultiChartTerminal = lazy(() => import('./components/charts/MultiChartTerminal.jsx'));
const StrategyTerminal   = lazy(() => import('./components/strategies/StrategyTerminal.jsx'));
const ProposalPage       = lazy(() => import('./components/proposals/ProposalPage.jsx'));
const Settings           = lazy(() => import('./components/Settings.jsx'));
const AIPage             = lazy(() => import('./components/AIPage.jsx'));

export default function App() {
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

  // Handle browser Back/Forward buttons
  useEffect(() => {
    const onPopState = (e) => {
      const newView = e.state?.view || new URLSearchParams(window.location.search).get('view') || 'dashboard';
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
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
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

  return (
    <ToastProvider>
      <div className="shell">
        <Sidebar view={view} setView={changeView} theme={theme} toggleTheme={toggleTheme} />
        <Suspense fallback={null}>
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
    </ToastProvider>
  );
}
