import { useState } from 'react';

const features = [
  {
    label: 'Dashboard',
    title: 'Trading Dashboard',
    desc: 'Track connected wallet activity, active positions, synced Hyperliquid fills, and recent trade history from one workspace.',
  },
  {
    label: 'AI Hub',
    title: 'AI Analysis + Auto Trading',
    desc: 'Ask for market reads, review AI reasoning, or let the bot trade from AI decisions while respecting your leverage, stop loss, take profit, and capital settings.',
  },
  {
    label: 'Strategies',
    title: 'Backtest Before Action',
    desc: 'Select a coin, capital, leverage, stop loss, take profit, and test strategy performance before committing real exposure.',
  },
  {
    label: 'Charts',
    title: 'TradingView Multi-Chart',
    desc: 'Open a TradingView-powered terminal, compare multiple assets, switch timeframes, and use correlation mode to understand how markets move together.',
  },
  {
    label: 'Bot Mode',
    title: 'Parameter-Based Execution',
    desc: 'Choose manual control, configure your own trade parameters, or rely on AI mode to generate entries, exits, sizing, and risk controls.',
  },
];

const workflow = [
  'Connect wallet',
  'Sync Hyperliquid data',
  'Scan volatile markets',
  'Review AI reasoning',
  'Backtest or execute',
];

const liveNow = [
  'Wallet-aware trading dashboard',
  'Hyperliquid trade sync',
  'AI chat and signal reasoning',
  'AI auto-trading mode with user parameters',
  'Strategy backtesting terminal',
  'Integrated TradingView multi-chart terminal',
  'Correlation analysis mode',
  'Telegram trade notifications',
];

const nextUp = [
  'No-code strategy builder',
  'Copy and social trading',
  'Multichain perpetual markets',
  'Multichain user portfolio',
  'More alert types',
  'Deeper portfolio reporting',
];

const developers = [
  {
    name: 'Kabir Singh Lamba',
    role: 'Developer',
    href: 'https://www.linkedin.com/in/kabir-singh-lamba-datawizard/',
  },
];

export default function LandingPage({ onLaunch, theme = 'dark', toggleTheme }) {
  const [launching, setLaunching] = useState(false);

  const handleLaunch = () => {
    setLaunching(true);
    setTimeout(() => {
      localStorage.setItem('seen_landing', '1');
      onLaunch();
    }, 420);
  };

  return (
    <>
      <style>{`
        .lp-root {
          --lp-bg-a: #f8fbff;
          --lp-bg-b: #eef4f8;
          --lp-bg-c: #ffffff;
          --lp-text: #101828;
          --lp-title: #111827;
          --lp-muted-text: #526171;
          --lp-soft-text: #667789;
          --lp-card-bg: rgba(255, 255, 255, 0.9);
          --lp-card-solid: #ffffff;
          --lp-card-soft: #f8fbfc;
          --lp-border: #dfe8ee;
          --lp-border-soft: #edf1f4;
          --lp-accent: #4f7c8a;
          --lp-accent-soft: #e8f3f5;
          --lp-accent-border: #d4e8ec;
          --lp-button-bg: #111827;
          --lp-button-text: #ffffff;
          --lp-final-bg: #111827;
          --lp-final-text: #ffffff;
          --lp-final-muted: #c6d0dc;
          min-height: 100vh;
          overflow-x: hidden;
          color: var(--lp-text);
          background:
            linear-gradient(180deg, var(--lp-bg-a) 0%, var(--lp-bg-b) 48%, var(--lp-bg-c) 100%);
          font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
          position: relative;
        }

        .lp-root[data-lp-theme='dark'] {
          --lp-bg-a: #070b10;
          --lp-bg-b: #0d141b;
          --lp-bg-c: #101820;
          --lp-text: #e7edf5;
          --lp-title: #ffffff;
          --lp-muted-text: #a9b6c5;
          --lp-soft-text: #8b9aac;
          --lp-card-bg: rgba(19, 29, 39, 0.92);
          --lp-card-solid: #121c26;
          --lp-card-soft: #0f1822;
          --lp-border: rgba(255, 255, 255, 0.12);
          --lp-border-soft: rgba(255, 255, 255, 0.08);
          --lp-accent: #7fb3c3;
          --lp-accent-soft: rgba(127, 179, 195, 0.13);
          --lp-accent-border: rgba(127, 179, 195, 0.25);
          --lp-button-bg: #ffffff;
          --lp-button-text: #111827;
          --lp-final-bg: #121c26;
          --lp-final-text: #ffffff;
          --lp-final-muted: #a9b6c5;
        }

        .lp-root::before {
          content: '';
          position: fixed;
          inset: 0;
          pointer-events: none;
          background-image:
            linear-gradient(rgba(79, 124, 138, 0.08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(79, 124, 138, 0.08) 1px, transparent 1px);
          background-size: 42px 42px;
          mask-image: linear-gradient(to bottom, #000 0%, transparent 70%);
        }

        @keyframes lp-fade-up {
          from { opacity: 0; transform: translateY(18px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes lp-float {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-8px); }
        }

        @keyframes lp-meter {
          from { width: 8%; }
          to { width: var(--meter-width); }
        }

        @keyframes lp-launch {
          to { opacity: 0; transform: scale(0.985); }
        }

        .lp-root.launching { animation: lp-launch 0.36s ease forwards; }

        .lp-wrap {
          width: min(1120px, calc(100% - 40px));
          margin: 0 auto;
          position: relative;
          z-index: 1;
        }

        .lp-nav {
          min-height: 78px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
        }

        .lp-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          font-weight: 800;
          letter-spacing: 0;
        }

        .lp-logo {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          object-fit: contain;
          background: #101828;
          padding: 5px;
          box-shadow: 0 10px 30px rgba(16, 24, 40, 0.12);
        }

        .lp-pill {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          border: 1px solid #d8e2ea;
          background: var(--lp-card-bg);
          color: var(--lp-accent);
          border-radius: 999px;
          padding: 7px 12px;
          font-size: 12px;
          font-weight: 800;
          box-shadow: 0 8px 24px rgba(16, 24, 40, 0.04);
        }

        .lp-nav-actions {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .lp-theme-toggle {
          width: 42px;
          height: 42px;
          border-radius: 8px;
          border: 1px solid var(--lp-border);
          background: var(--lp-card-bg);
          color: var(--lp-title);
          display: inline-flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
        }

        .lp-theme-toggle:hover {
          transform: translateY(-2px);
          border-color: var(--lp-accent-border);
        }

        .lp-hero {
          min-height: calc(100vh - 78px);
          display: grid;
          grid-template-columns: minmax(0, 0.92fr) minmax(360px, 1.08fr);
          gap: 52px;
          align-items: center;
          padding: 28px 0 70px;
        }

        .lp-copy {
          animation: lp-fade-up 0.58s ease both;
        }

        .lp-kicker {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: var(--lp-accent);
          background: var(--lp-accent-soft);
          border: 1px solid var(--lp-accent-border);
          border-radius: 999px;
          padding: 8px 13px;
          font-size: 12px;
          font-weight: 800;
          margin-bottom: 22px;
        }

        .lp-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #18b87a;
          box-shadow: 0 0 0 5px rgba(24, 184, 122, 0.14);
        }

        .lp-title {
          font-size: clamp(42px, 6vw, 76px);
          line-height: 0.98;
          font-weight: 900;
          letter-spacing: 0;
          margin: 0 0 24px;
          color: var(--lp-title);
          max-width: 760px;
        }

        .lp-title span {
          color: var(--lp-accent);
        }

        .lp-sub {
          font-size: 18px;
          line-height: 1.7;
          color: var(--lp-muted-text);
          max-width: 620px;
          margin: 0 0 30px;
        }

        .lp-actions {
          display: flex;
          align-items: center;
          gap: 14px;
          flex-wrap: wrap;
        }

        .lp-launch-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          min-height: 50px;
          padding: 0 22px;
          border-radius: 8px;
          background: var(--lp-button-bg);
          color: var(--lp-button-text);
          font-size: 14px;
          font-weight: 850;
          box-shadow: 0 16px 34px rgba(17, 24, 39, 0.18);
          transition: transform 0.22s ease, box-shadow 0.22s ease, background 0.22s ease;
        }

        .lp-launch-btn:hover {
          transform: translateY(-2px);
          background: var(--lp-button-bg);
          box-shadow: 0 20px 40px rgba(17, 24, 39, 0.22);
        }

        .lp-ghost {
          color: var(--lp-muted-text);
          font-size: 14px;
          font-weight: 750;
        }

        .lp-product {
          animation: lp-fade-up 0.68s 0.1s ease both, lp-float 6s 1.2s ease-in-out infinite;
        }

        .lp-window {
          border: 1px solid var(--lp-border);
          border-radius: 8px;
          background: var(--lp-card-bg);
          box-shadow: 0 30px 80px rgba(49, 67, 83, 0.16);
          overflow: hidden;
        }

        .lp-window-top {
          height: 44px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 16px;
          border-bottom: 1px solid var(--lp-border-soft);
          background: var(--lp-card-soft);
        }

        .lp-lights {
          display: flex;
          gap: 7px;
        }

        .lp-light {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #d0dae2;
        }

        .lp-status {
          font-size: 11px;
          color: var(--lp-soft-text);
          font-weight: 800;
        }

        .lp-screen {
          padding: 18px;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 14px;
          min-height: 420px;
        }

        .lp-panel {
          border: 1px solid var(--lp-border);
          background: var(--lp-card-solid);
          border-radius: 8px;
          padding: 16px;
        }

        .lp-panel.wide { grid-column: 1 / -1; }

        .lp-panel-h {
          display: flex;
          align-items: center;
          justify-content: space-between;
          color: var(--lp-soft-text);
          font-size: 11px;
          font-weight: 850;
          text-transform: uppercase;
          margin-bottom: 14px;
        }

        .lp-metric {
          display: flex;
          align-items: baseline;
          gap: 8px;
        }

        .lp-metric strong {
          font-size: 30px;
          color: var(--lp-title);
        }

        .lp-positive { color: #18b87a; font-weight: 850; }
        .lp-muted { color: var(--lp-soft-text); }

        .lp-bars {
          display: grid;
          gap: 10px;
          margin-top: 18px;
        }

        .lp-bar {
          height: 9px;
          border-radius: 999px;
          background: var(--lp-border-soft);
          overflow: hidden;
        }

        .lp-bar span {
          display: block;
          height: 100%;
          width: var(--meter-width);
          border-radius: inherit;
          background: linear-gradient(90deg, var(--lp-accent), #18b87a);
          animation: lp-meter 1.25s 0.4s ease both;
        }

        .lp-signal {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 11px 0;
          border-bottom: 1px solid var(--lp-border-soft);
        }

        .lp-signal:last-child { border-bottom: 0; }

        .lp-coin {
          font-weight: 900;
          color: var(--lp-title);
        }

        .lp-chip {
          border-radius: 999px;
          padding: 5px 8px;
          font-size: 11px;
          font-weight: 900;
          background: #e9f8f1;
          color: #12835a;
        }

        .lp-chip.short {
          background: #fff1f3;
          color: #c9354f;
        }

        .lp-route {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 8px;
        }

        .lp-step {
          min-height: 74px;
          border: 1px solid var(--lp-border);
          border-radius: 8px;
          padding: 10px;
          background: var(--lp-card-soft);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          animation: lp-fade-up 0.58s ease both;
        }

        .lp-step:nth-child(2) { animation-delay: 0.08s; }
        .lp-step:nth-child(3) { animation-delay: 0.16s; }
        .lp-step:nth-child(4) { animation-delay: 0.24s; }
        .lp-step:nth-child(5) { animation-delay: 0.32s; }

        .lp-num {
          color: var(--lp-accent);
          font-size: 11px;
          font-weight: 900;
        }

        .lp-step-text {
          font-size: 12px;
          line-height: 1.35;
          font-weight: 800;
          color: var(--lp-title);
        }

        .lp-section {
          padding: 78px 0;
          position: relative;
          z-index: 1;
        }

        .lp-section-head {
          max-width: 700px;
          margin-bottom: 28px;
          animation: lp-fade-up 0.58s ease both;
        }

        .lp-label {
          color: var(--lp-accent);
          text-transform: uppercase;
          font-size: 12px;
          font-weight: 900;
          letter-spacing: 0;
          margin-bottom: 10px;
        }

        .lp-heading {
          font-size: clamp(30px, 4vw, 46px);
          line-height: 1.08;
          font-weight: 900;
          letter-spacing: 0;
          margin: 0;
        }

        .lp-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 14px;
        }

        .lp-card {
          background: var(--lp-card-bg);
          border: 1px solid var(--lp-border);
          border-radius: 8px;
          padding: 18px;
          min-height: 220px;
          box-shadow: 0 14px 34px rgba(49, 67, 83, 0.06);
          transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
          animation: lp-fade-up 0.6s ease both;
        }

        .lp-card:nth-child(2) { animation-delay: 0.08s; }
        .lp-card:nth-child(3) { animation-delay: 0.16s; }
        .lp-card:nth-child(4) { animation-delay: 0.24s; }

        .lp-card:hover {
          transform: translateY(-5px);
          border-color: #bdd2dc;
          box-shadow: 0 20px 44px rgba(49, 67, 83, 0.1);
        }

        .lp-card-label {
          display: inline-flex;
          color: var(--lp-accent);
          background: var(--lp-accent-soft);
          border: 1px solid var(--lp-accent-border);
          border-radius: 999px;
          padding: 5px 8px;
          font-size: 11px;
          font-weight: 900;
          margin-bottom: 28px;
        }

        .lp-card h3 {
          font-size: 18px;
          line-height: 1.25;
          margin: 0 0 10px;
        }

        .lp-card p {
          color: var(--lp-muted-text);
          line-height: 1.62;
          font-size: 14px;
          margin: 0;
        }

        .lp-split {
          display: grid;
          grid-template-columns: 0.9fr 1.1fr;
          gap: 34px;
          align-items: start;
        }

        .lp-list-box {
          border: 1px solid var(--lp-border);
          background: var(--lp-card-solid);
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 16px 36px rgba(49, 67, 83, 0.07);
        }

        .lp-list-box h3 {
          margin: 0 0 16px;
          font-size: 18px;
        }

        .lp-list {
          list-style: none;
          display: grid;
          gap: 10px;
        }

        .lp-list li {
          display: flex;
          align-items: center;
          gap: 10px;
          color: var(--lp-muted-text);
          font-size: 14px;
          line-height: 1.45;
        }

        .lp-check {
          min-width: 22px;
          height: 18px;
          border-radius: 999px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background: #e9f8f1;
          color: #12835a;
          font-size: 9px;
          font-weight: 900;
          flex: 0 0 auto;
        }

        .lp-risk {
          border: 1px solid var(--lp-border);
          background: var(--lp-card-soft);
          border-radius: 8px;
          padding: 22px;
        }

        .lp-risk h3 {
          margin: 0 0 12px;
          font-size: 22px;
        }

        .lp-risk p {
          color: var(--lp-muted-text);
          line-height: 1.7;
          margin: 0;
        }

        .lp-final {
          padding: 64px 0 80px;
          text-align: center;
        }

        .lp-final-box {
          border: 1px solid var(--lp-border);
          background: var(--lp-final-bg);
          color: var(--lp-final-text);
          border-radius: 8px;
          padding: 44px 24px;
          box-shadow: 0 24px 70px rgba(17, 24, 39, 0.2);
        }

        .lp-final h2 {
          font-size: clamp(30px, 4vw, 48px);
          margin: 0 0 12px;
          letter-spacing: 0;
        }

        .lp-final p {
          color: var(--lp-final-muted);
          margin: 0 auto 24px;
          max-width: 560px;
          line-height: 1.7;
        }

        .lp-final .lp-launch-btn {
          background: var(--lp-button-text);
          color: var(--lp-button-bg);
          box-shadow: none;
        }

        .lp-small {
          margin-top: 14px;
          color: #94a3b8;
          font-size: 12px;
          font-weight: 700;
        }

        .lp-devs {
          margin-top: 24px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
        }

        .lp-dev-label {
          color: #94a3b8;
          font-size: 11px;
          font-weight: 900;
          text-transform: uppercase;
          letter-spacing: 0;
        }

        .lp-dev-buttons {
          display: flex;
          justify-content: center;
          gap: 10px;
          flex-wrap: wrap;
        }

        .lp-dev-link {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          min-height: 42px;
          padding: 0 14px;
          border-radius: 8px;
          color: var(--lp-final-text);
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.14);
          font-size: 13px;
          font-weight: 850;
          transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
        }

        .lp-dev-link:hover {
          transform: translateY(-2px);
          background: rgba(255, 255, 255, 0.14);
          border-color: rgba(255, 255, 255, 0.26);
        }

        .lp-dev-in {
          width: 20px;
          height: 20px;
          border-radius: 5px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background: #0a66c2;
          color: #fff;
          font-size: 11px;
          font-weight: 900;
        }

        .lp-dev-role {
          color: var(--lp-final-muted);
          font-size: 11px;
          font-weight: 750;
        }

        @media (max-width: 980px) {
          .lp-hero,
          .lp-split {
            grid-template-columns: 1fr;
          }

          .lp-hero {
            min-height: auto;
            padding-top: 30px;
          }

          .lp-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (max-width: 640px) {
          .lp-wrap {
            width: min(100% - 28px, 1120px);
          }

          .lp-nav {
            min-height: 68px;
          }

          .lp-pill {
            display: none;
          }

          .lp-hero {
            gap: 28px;
            padding-bottom: 46px;
          }

          .lp-title {
            font-size: 42px;
          }

          .lp-sub {
            font-size: 16px;
          }

          .lp-screen {
            grid-template-columns: 1fr;
            min-height: auto;
          }

          .lp-route {
            grid-template-columns: 1fr;
          }

          .lp-grid {
            grid-template-columns: 1fr;
          }

          .lp-section {
            padding: 52px 0;
          }
        }
      `}</style>

      <main className={`lp-root${launching ? ' launching' : ''}`} data-lp-theme={theme}>
        <div className="lp-wrap">
          <nav className="lp-nav" aria-label="Landing page">
            <div className="lp-brand">
              <img className="lp-logo" src="/synap.png" alt="Synap" />
              <span>Synap.surf</span>
            </div>
            <div className="lp-nav-actions">
              <div className="lp-pill">
                <span className="lp-dot" />
                Beta workspace is live
              </div>
              <button
                className="lp-theme-toggle"
                type="button"
                onClick={toggleTheme}
                title={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
                aria-label={theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme'}
              >
                {theme === 'light' ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.6 6.6 0 0 0 21 12.8Z" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="4.5" />
                    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
                  </svg>
                )}
              </button>
            </div>
          </nav>

          <section className="lp-hero">
            <div className="lp-copy">
              <div className="lp-kicker">
                <span className="lp-dot" />
                AI trading workspace for crypto and perps
              </div>
              <h1 className="lp-title">
                Understand markets before you <span>take the trade.</span>
              </h1>
              <p className="lp-sub">
                Synap brings live Hyperliquid data, AI market reasoning, automated bot trading,
                wallet-aware trade tracking, strategy backtesting, and TradingView multi-chart analysis
                into one clean trading dashboard.
              </p>
              <div className="lp-actions">
                <button className="lp-launch-btn" onClick={handleLaunch}>
                  {launching ? 'Opening dashboard...' : 'Launch Dashboard'}
                </button>
                <span className="lp-ghost">No credit card. Crypto-native access only.</span>
              </div>
            </div>

            <div className="lp-product" aria-label="Product preview">
              <div className="lp-window">
                <div className="lp-window-top">
                  <div className="lp-lights">
                    <span className="lp-light" />
                    <span className="lp-light" />
                    <span className="lp-light" />
                  </div>
                  <div className="lp-status">LIVE MARKET WORKSPACE</div>
                </div>
                <div className="lp-screen">
                  <div className="lp-panel">
                    <div className="lp-panel-h">
                      Trading Activity
                      <span className="lp-positive">Synced</span>
                    </div>
                    <div className="lp-metric">
                      <strong>$12.8k</strong>
                      <span className="lp-positive">+4.2%</span>
                    </div>
                    <div className="lp-bars">
                      <div className="lp-bar" style={{ '--meter-width': '78%' }}><span /></div>
                      <div className="lp-bar" style={{ '--meter-width': '46%' }}><span /></div>
                      <div className="lp-bar" style={{ '--meter-width': '64%' }}><span /></div>
                    </div>
                  </div>

                  <div className="lp-panel">
                    <div className="lp-panel-h">
                      AI Bot
                      <span className="lp-muted">Param aware</span>
                    </div>
                    <div className="lp-signal">
                      <span className="lp-coin">BTC</span>
                      <span className="lp-chip">AI Long</span>
                    </div>
                    <div className="lp-signal">
                      <span className="lp-coin">SOL</span>
                      <span className="lp-chip short">AI Short</span>
                    </div>
                    <div className="lp-signal">
                      <span className="lp-coin">Risk</span>
                      <span className="lp-chip">SL / TP</span>
                    </div>
                  </div>

                  <div className="lp-panel wide">
                    <div className="lp-panel-h">
                      How Synap Works
                      <span className="lp-muted">5 steps</span>
                    </div>
                    <div className="lp-route">
                      {workflow.map((item, index) => (
                        <div className="lp-step" key={item}>
                          <span className="lp-num">0{index + 1}</span>
                          <span className="lp-step-text">{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="lp-section">
            <div className="lp-section-head">
              <div className="lp-label">What this website is about</div>
              <h2 className="lp-heading">
                A practical AI trading command center, not a black-box signal feed.
              </h2>
            </div>
            <div className="lp-grid">
              {features.map((feature) => (
                <article className="lp-card" key={feature.title}>
                  <span className="lp-card-label">{feature.label}</span>
                  <h3>{feature.title}</h3>
                  <p>{feature.desc}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="lp-section">
            <div className="lp-split">
              <div className="lp-risk">
                <div className="lp-label">Trading with context</div>
                <h3>You stay close to the reasoning.</h3>
                <p>
                  The AI engine is designed to combine technicals, sentiment, smart-money context,
                  portfolio state, volatility, and risk settings. Users can keep manual control,
                  trade from their own parameters, or allow AI mode to place trades through the bot
                  with configured leverage, stop loss, take profit, and position sizing rules.
                </p>
              </div>

              <div className="lp-list-box">
                <h3>Live now</h3>
                <ul className="lp-list">
                  {liveNow.map((item) => (
                    <li key={item}><span className="lp-check">OK</span>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          <section className="lp-section">
            <div className="lp-split">
              <div className="lp-list-box">
                <h3>Built for</h3>
                <ul className="lp-list">
                  <li><span className="lp-check">OK</span>Active crypto traders watching fast markets</li>
                  <li><span className="lp-check">OK</span>Hyperliquid users who want cleaner trade visibility</li>
                  <li><span className="lp-check">OK</span>Algo traders testing strategies before deployment</li>
                  <li><span className="lp-check">OK</span>Users who want AI auto trading without losing risk control</li>
                </ul>
              </div>

              <div className="lp-list-box">
                <h3>Coming next</h3>
                <ul className="lp-list">
                  {nextUp.map((item) => (
                    <li key={item}><span className="lp-check">+</span>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          <section className="lp-final">
            <div className="lp-final-box">
              <h2>Ready to open the workspace?</h2>
              <p>
                Start with the dashboard, connect your wallet when you are ready,
                and explore AI analysis, charts, strategies, and trade history from one place.
              </p>
              <button className="lp-launch-btn" onClick={handleLaunch}>
                {launching ? 'Opening dashboard...' : 'Launch Dashboard'}
              </button>
              <div className="lp-small">Beta access is currently open</div>
              <div className="lp-devs" aria-label="Developer handle">
                <div className="lp-dev-label">Developer handle</div>
                <div className="lp-dev-buttons">
                  {developers.map((developer) => (
                    <a
                      className="lp-dev-link"
                      key={developer.href}
                      href={developer.href}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <span className="lp-dev-in">in</span>
                      <span>{developer.name}</span>
                      <span className="lp-dev-role">{developer.role}</span>
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </div>
      </main>
    </>
  );
}
