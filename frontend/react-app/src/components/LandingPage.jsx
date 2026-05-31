import { useState, useEffect } from 'react';

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
  'Stock market integration',
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
  const [showSubModal, setShowSubModal] = useState(false);
  const [email, setEmail] = useState('');
  const [occupation, setOccupation] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const isSubscribed = localStorage.getItem('synap_subscribed') === '1';
    const isSeen = localStorage.getItem('seen_subscribe_popup') === '1';
    
    if (!isSubscribed && !isSeen) {
      const timer = setTimeout(() => {
        setShowSubModal(true);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleCloseModal = () => {
    localStorage.setItem('seen_subscribe_popup', '1');
    setShowSubModal(false);
  };

  const handleSubmitSubscription = async (e) => {
    e.preventDefault();
    setError('');
    
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError('Please enter your email.');
      return;
    }
    
    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setError('Please enter a valid email address (e.g. name@domain.com).');
      return;
    }
    
    if (!occupation) {
      setError('Please select your occupation.');
      return;
    }
    
    if (occupation === 'Employed' && !companyName.trim()) {
      setError('Please enter your company name.');
      return;
    }
    
    setSubmitting(true);
    try {
      const response = await fetch('/api/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: trimmedEmail,
          occupation: occupation,
          company_name: occupation === 'Employed' ? companyName.trim() : null,
        }),
      });
      
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Subscription failed. Please try again.');
      }
      
      setSuccess(true);
      localStorage.setItem('synap_subscribed', '1');
      
      setTimeout(() => {
        setShowSubModal(false);
      }, 2000);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please check your connection.');
    } finally {
      setSubmitting(false);
    }
  };

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

        /* Subscription Modal Overlay */
        .lp-modal-overlay {
          position: fixed;
          inset: 0;
          z-index: 1000;
          background: rgba(7, 11, 16, 0.65);
          backdrop-filter: blur(12px);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          animation: lp-fade-in 0.28s cubic-bezier(0.16, 1, 0.3, 1) both;
        }

        @keyframes lp-fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        /* Subscription Modal Card */
        .lp-modal-card {
          width: 100%;
          max-width: 480px;
          background: var(--lp-card-bg);
          border: 1px solid var(--lp-border);
          border-radius: 16px;
          box-shadow: 0 32px 64px rgba(0, 0, 0, 0.4), 0 0 0 1px var(--lp-accent-border);
          padding: 32px;
          position: relative;
          color: var(--lp-text);
          animation: lp-slide-up 0.42s cubic-bezier(0.34, 1.56, 0.64, 1) both;
        }

        @keyframes lp-slide-up {
          from { opacity: 0; transform: translateY(30px) scale(0.96); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .lp-modal-close {
          position: absolute;
          top: 20px;
          right: 20px;
          background: transparent;
          border: 0;
          color: var(--lp-soft-text);
          cursor: pointer;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s ease, color 0.2s ease;
        }

        .lp-modal-close:hover {
          background: var(--lp-accent-soft);
          color: var(--lp-accent);
        }

        .lp-modal-header {
          text-align: center;
          margin-bottom: 24px;
        }

        .lp-modal-bell-icon {
          width: 52px;
          height: 52px;
          border-radius: 12px;
          background: var(--lp-accent-soft);
          border: 1px solid var(--lp-accent-border);
          color: var(--lp-accent);
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 16px;
          animation: lp-pulse 2s infinite ease-in-out;
        }

        @keyframes lp-pulse {
          0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(79, 124, 138, 0.2); }
          50% { transform: scale(1.05); box-shadow: 0 0 12px 4px rgba(79, 124, 138, 0.4); }
        }

        .lp-modal-header h3 {
          font-size: 22px;
          font-weight: 800;
          color: var(--lp-title);
          margin: 0 0 8px;
          letter-spacing: -0.5px;
        }

        .lp-modal-header p {
          font-size: 13.5px;
          line-height: 1.55;
          color: var(--lp-muted-text);
          margin: 0;
        }

        .lp-modal-error {
          background: rgba(201, 53, 79, 0.1);
          border: 1px solid rgba(201, 53, 79, 0.25);
          color: #e54b64;
          padding: 12px;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          margin-bottom: 20px;
          text-align: center;
          animation: lp-shake 0.3s ease both;
        }

        @keyframes lp-shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-4px); }
          75% { transform: translateX(4px); }
        }

        .lp-modal-fields {
          display: flex;
          flex-direction: column;
          gap: 16px;
          margin-bottom: 24px;
        }

        .lp-modal-field {
          display: flex;
          flex-direction: column;
          gap: 6px;
          text-align: left;
        }

        .lp-modal-field label {
          font-size: 12px;
          font-weight: 800;
          color: var(--lp-soft-text);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .lp-modal-input,
        .lp-modal-select {
          min-height: 46px;
          background: var(--lp-card-soft);
          border: 1px solid var(--lp-border);
          border-radius: 8px;
          padding: 0 14px;
          font-size: 14px;
          color: var(--lp-title);
          outline: none;
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
          width: 100%;
          box-sizing: border-box;
        }

        .lp-modal-input:focus,
        .lp-modal-select:focus {
          border-color: var(--lp-accent);
          box-shadow: 0 0 0 3px var(--lp-accent-soft);
        }

        .lp-modal-select {
          appearance: none;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%238b9aac' stroke-width='2.5'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5' /%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-position: right 14px center;
          background-size: 16px;
          cursor: pointer;
        }

        /* Animate company field expansion */
        .lp-modal-field-expand {
          animation: lp-expand 0.25s cubic-bezier(0.16, 1, 0.3, 1) both;
        }

        @keyframes lp-expand {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .lp-modal-actions {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .lp-modal-submit-btn {
          min-height: 48px;
          background: var(--lp-button-bg);
          color: var(--lp-button-text);
          border: 0;
          border-radius: 8px;
          font-weight: 850;
          font-size: 14px;
          cursor: pointer;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .lp-modal-submit-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
        }

        .lp-modal-submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .lp-modal-cancel-btn {
          min-height: 40px;
          background: transparent;
          color: var(--lp-soft-text);
          border: 0;
          border-radius: 8px;
          font-weight: 750;
          font-size: 13.5px;
          cursor: pointer;
          transition: color 0.2s ease, background 0.2s ease;
        }

        .lp-modal-cancel-btn:hover:not(:disabled) {
          color: var(--lp-text);
          background: var(--lp-border-soft);
        }

        /* Success State */
        .lp-modal-success-state {
          text-align: center;
          padding: 16px 0;
          animation: lp-fade-in 0.3s ease both;
        }

        .lp-modal-success-icon {
          width: 68px;
          height: 68px;
          border-radius: 50%;
          background: #e9f8f1;
          color: #18b87a;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
          box-shadow: 0 0 0 8px rgba(24, 184, 122, 0.08);
          animation: lp-scale-in 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
        }

        @keyframes lp-scale-in {
          from { transform: scale(0); }
          to { transform: scale(1); }
        }

        .lp-modal-success-state h3 {
          font-size: 22px;
          font-weight: 800;
          color: var(--lp-title);
          margin: 0 0 8px;
        }

        .lp-modal-success-state p {
          font-size: 14px;
          color: var(--lp-muted-text);
          line-height: 1.6;
          margin: 0;
        }

        /* Hiring & Funding Callout */
        .lp-modal-hiring-card {
          margin-top: 24px;
          padding-top: 20px;
          border-top: 1px dashed var(--lp-border);
          text-align: center;
        }

        .lp-modal-hiring-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          font-weight: 900;
          color: #12835a;
          background: #e9f8f1;
          border: 1px solid rgba(18, 131, 90, 0.16);
          border-radius: 999px;
          padding: 4px 10px;
          margin-bottom: 10px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .lp-modal-hiring-badge-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #18b87a;
          box-shadow: 0 0 0 3px rgba(24, 184, 122, 0.18);
        }

        .lp-modal-hiring-text {
          font-size: 12.5px;
          line-height: 1.5;
          color: var(--lp-muted-text);
          margin: 0 0 12px 0;
          font-weight: 600;
        }

        .lp-modal-linkedin-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-height: 38px;
          padding: 0 16px;
          border-radius: 6px;
          background: #0a66c2;
          color: #ffffff;
          font-size: 12.5px;
          font-weight: 800;
          text-decoration: none;
          transition: transform 0.2s ease, background 0.2s ease;
          width: 100%;
          box-sizing: border-box;
        }

        .lp-modal-linkedin-btn:hover {
          background: #004b93;
          transform: translateY(-1px);
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

          {/* Hyperliquid Guide Section */}
          <section className="lp-section hyperliquid-guide-lp" style={{ animation: 'lp-fade-up 0.6s ease both' }}>
            <div className="lp-list-box" style={{ padding: '36px', borderRadius: '12px', border: '1px solid var(--lp-border)', background: 'var(--lp-card-bg)', boxShadow: '0 24px 60px rgba(49, 67, 83, 0.05)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '28px' }}>
                <div style={{ width: '48px', height: '48px', borderRadius: '14px', background: 'linear-gradient(135deg, #6c5ce7, #00d2d3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: '900', fontSize: '22px' }}>H</div>
                <div>
                  <h2 style={{ fontSize: '22px', fontWeight: '900', margin: 0, color: 'var(--lp-title)', letterSpacing: '-0.5px' }}>HYPERLIQUID INTEGRATION GUIDE</h2>
                  <p style={{ fontSize: '13.5px', color: 'var(--lp-muted-text)', margin: '4px 0 0 0', fontWeight: '600' }}>Understand how automated trading works and how to safely connect your wallet.</p>
                </div>
              </div>
              
              <div className="lp-split" style={{ gap: '36px', marginBottom: '32px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <h3 style={{ fontSize: '13.5px', fontWeight: '900', color: 'var(--lp-accent)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.8px' }}>What is Hyperliquid?</h3>
                  <p style={{ fontSize: '14px', color: 'var(--lp-muted-text)', lineHeight: '1.7', margin: 0, fontWeight: '500' }}>
                    Hyperliquid is a state-of-the-art decentralized perpetual exchange built on a custom L1 appchain. It supports sub-second order execution, zero gas fees for placing trades, deep liquidity, and highly secure L1 self-custody.
                  </p>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <h3 style={{ fontSize: '13.5px', fontWeight: '900', color: 'var(--lp-accent)', margin: 0, textTransform: 'uppercase', letterSpacing: '0.8px' }}>How to get your API Wallet Key</h3>
                  <ol style={{ fontSize: '14px', color: 'var(--lp-muted-text)', lineHeight: '1.7', margin: 0, paddingLeft: '20px', fontWeight: '500' }}>
                    <li style={{ marginBottom: '8px' }}>Visit the <a href="https://app.hyperliquid.xyz/API" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--lp-accent)', fontWeight: '800', textDecoration: 'underline' }}>Hyperliquid API page</a> and connect your wallet.</li>
                    <li style={{ marginBottom: '8px' }}>Ensure you have deposited USDC into your decentralized L1 trading account.</li>
                    <li style={{ marginBottom: '8px' }}>Enter an API wallet name, click <strong>Generate</strong> to create a dedicated trading key, and click **Connect** to authorize it.</li>
                  </ol>
                </div>
              </div>

              <div style={{ background: 'var(--lp-card-soft)', border: '1px solid var(--lp-border-soft)', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <h4 style={{ fontSize: '12px', fontWeight: '900', color: 'var(--lp-soft-text)', textTransform: 'uppercase', margin: '0 0 6px 0', letterSpacing: '0.5px' }}>Ready to Trade?</h4>
                  <p style={{ fontSize: '13.5px', color: 'var(--lp-muted-text)', margin: 0, lineHeight: '1.5', fontWeight: '500' }}>
                    Save your generated API wallet private key securely in Settings to authorize the AI bot to execute trades.
                  </p>
                </div>
                <button 
                  onClick={handleLaunch} 
                  className="lp-launch-btn"
                  style={{ width: '100%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '48px', fontSize: '13.5px', fontWeight: '850', letterSpacing: '0.5px' }}
                >
                  {launching ? 'Opening dashboard...' : 'Launch Dashboard to Setup 🚀'}
                </button>
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

        {/* Render Subscribe Modal Overlay */}
        {showSubModal && (
          <div className="lp-modal-overlay" onClick={handleCloseModal} role="dialog" aria-modal="true">
            <div className="lp-modal-card" onClick={(e) => e.stopPropagation()}>
              <button className="lp-modal-close" onClick={handleCloseModal} aria-label="Close subscription form">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
              
              {success ? (
                <div className="lp-modal-success-state">
                  <div className="lp-modal-success-icon">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                  <h3>Welcome to the Project!</h3>
                  <p>You have successfully subscribed to future updates. We will stay in touch!</p>
                </div>
              ) : (
                <form onSubmit={handleSubmitSubscription} className="lp-modal-form">
                  <div className="lp-modal-header">
                    <div className="lp-modal-bell-icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                      </svg>
                    </div>
                    <h3>Join the project for future updates</h3>
                    <p>Subscribe to our newsletter to receive the latest development insights, early access announcements, and feature updates.</p>
                  </div>
                  
                  {error && <div className="lp-modal-error">{error}</div>}
                  
                  <div className="lp-modal-fields">
                    <div className="lp-modal-field">
                      <label htmlFor="lp-sub-email">Email Address</label>
                      <input
                        id="lp-sub-email"
                        type="email"
                        className="lp-modal-input"
                        placeholder="e.g. trader@gmail.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={submitting}
                        required
                      />
                    </div>
                    
                    <div className="lp-modal-field">
                      <label htmlFor="lp-sub-occupation">Occupation</label>
                      <select
                        id="lp-sub-occupation"
                        className="lp-modal-select"
                        value={occupation}
                        onChange={(e) => {
                          setOccupation(e.target.value);
                          if (e.target.value !== 'Employed') {
                            setCompanyName('');
                          }
                        }}
                        disabled={submitting}
                        required
                      >
                        <option value="">Select your occupation</option>
                        <option value="Employed">Employed</option>
                        <option value="Founder">Founder / Entrepreneur</option>
                        <option value="Freelancer">Freelancer</option>
                        <option value="Student">Student</option>
                        <option value="Unemployed">Trader / Unemployed</option>
                      </select>
                    </div>
                    
                    {occupation === 'Employed' && (
                      <div className="lp-modal-field lp-modal-field-expand">
                        <label htmlFor="lp-sub-company">Company Name</label>
                        <input
                          id="lp-sub-company"
                          type="text"
                          className="lp-modal-input"
                          placeholder="e.g. Acme Corp"
                          value={companyName}
                          onChange={(e) => setCompanyName(e.target.value)}
                          disabled={submitting}
                          required
                        />
                      </div>
                    )}
                  </div>
                  
                  <div className="lp-modal-actions">
                    <button type="submit" className="lp-modal-submit-btn" disabled={submitting}>
                      {submitting ? 'Joining...' : 'Subscribe to Updates'}
                    </button>
                    <button type="button" className="lp-modal-cancel-btn" onClick={handleCloseModal} disabled={submitting}>
                      Maybe Later
                    </button>
                  </div>
                </form>
              )}
              {/* LinkedIn Hiring & Funding Callout Card */}
              <div className="lp-modal-hiring-card">
                <div className="lp-modal-hiring-badge">
                  <span className="lp-modal-hiring-badge-dot"></span>
                  Open To Work &amp; Funding 🚀
                </div>
                <p className="lp-modal-hiring-text">
                  Are you a Recruiter, Founder, or VC? Let's connect for roles, advisory, or project funding!
                </p>
                <a
                  href="https://www.linkedin.com/in/kabir-singh-lamba-datawizard/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="lp-modal-linkedin-btn"
                >
                  <span className="lp-dev-in" style={{ marginRight: '8px', padding: '1px 5px', fontSize: '10px' }}>in</span>
                  Connect with Kabir on LinkedIn
                </a>
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
