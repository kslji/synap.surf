import { useState, useEffect } from 'react';
import { useDashboard } from './hooks/useDashboard.js';
import Sidebar from './components/Sidebar.jsx';
import RightPanel from './components/RightPanel.jsx';
import Dashboard from './components/dashboard/Dashboard.jsx';
import MultiChartTerminal from './components/charts/MultiChartTerminal.jsx';
import StrategyTerminal from './components/strategies/StrategyTerminal.jsx';
import ProposalPage from './components/proposals/ProposalPage.jsx';
import Settings from './components/Settings.jsx';
import AIPage from './components/AIPage.jsx';
import { ToastProvider } from './components/Toast.jsx';

export default function App() {
  const [view, setView] = useState('dashboard');
  const [tradingMode, setTradingMode] = useState(() => localStorage.getItem('trading_mode') || 'bot');
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
  const { stats, trades, decisions, perps, intel, topCoins, fetchAll } = useDashboard();

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
            stats={stats}
            trades={trades}
            perps={perps}
            intel={intel}
            onShowCharts={() => setView('charts')}
            onRefresh={fetchAll}
          />
        );
      case 'charts':
        return (
          <MultiChartTerminal
            coins={topCoins}
            theme={theme}
            onBack={() => setView('dashboard')}
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
        <Sidebar view={view} setView={setView} theme={theme} toggleTheme={toggleTheme} />
        {renderView()}
        {view !== 'strategies' && view !== 'proposals' && view !== 'settings' && view !== 'ai' && (
          <RightPanel
            view={view}
            stats={stats}
            decisions={decisions}
            tradingMode={tradingMode}
            setTradingMode={handleSetTradingMode}
          />
        )}
      </div>
    </ToastProvider>
  );
}
