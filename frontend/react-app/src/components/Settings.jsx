import React, { useState, useEffect } from 'react';
import { useToast } from './Toast.jsx';
import { useAuth } from '../context/AuthContext.jsx';

export default function Settings() {
  const toast = useToast();
  const { walletAddress, connectWallet, disconnectWallet, userProfile, fetchUserProfile } = useAuth();
  
  const [showKey, setShowKey] = useState(false);

  // Local state for profile edits
  const [nameInput, setNameInput] = useState('');
  const [isNameModalOpen, setIsNameModalOpen] = useState(false);
  useEffect(() => {
    if (userProfile.name) setNameInput(userProfile.name);
  }, [userProfile.name]);
  const [tgToken, setTgToken] = useState(() => localStorage.getItem('tg_token') || '');
  const [tgNotifs, setTgNotifs] = useState(false);

  // ── Private Key ──────────────────────────────────────────────────
  const [hlKey, setHlKey] = useState('');
  const [keyStatus, setKeyStatus] = useState(() => localStorage.getItem('hl_key_status') || null);

  useEffect(() => {
    if (userProfile?.has_private_key) {
      setKeyStatus('saved');
      setHlKey(userProfile.private_key || '');
    } else {
      setHlKey('');
      setKeyStatus(null);
    }
  }, [userProfile?.has_private_key, userProfile?.private_key]);

  const handleSaveKey = async () => {
    if (!walletAddress) {
      toast({ type: 'error', title: 'Wallet Required', message: 'Please connect your wallet first.', duration: 5000 });
      return;
    }
    setKeyStatus('saving');
    try {
      const res = await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl_private_key: hlKey, hl_wallet: walletAddress }),
      });
      const text = await res.text();
      if (!res.ok) {
        const d = (() => { try { return JSON.parse(text); } catch { return {}; } })();
        throw new Error(d.detail || text);
      }
      
      if (!hlKey) {
        setKeyStatus(null);
        localStorage.removeItem('hl_key_status');
        toast({ type: 'success', title: 'Private Key Removed', message: 'Your Hyperliquid key has been removed.', duration: 5000 });
      } else {
        setKeyStatus('saved');
        localStorage.setItem('hl_key_status', 'saved');
        toast({ type: 'success', title: 'Private Key Saved', message: 'Your Hyperliquid key has been saved and is ready for trading.', duration: 5000 });
      }
      await fetchUserProfile(walletAddress); // Refresh profile to get updated key
    } catch (err) {
      setKeyStatus('error');
      localStorage.removeItem('hl_key_status');
      toast({ type: 'error', title: 'Invalid Private Key', message: err.message, duration: 7000 });
    }
  };

  // ── Wallet Connect ───────────────────────────────────────────────
  const [walletStatus, setWalletStatus] = useState(() => walletAddress ? 'connected' : null);

  useEffect(() => {
    setWalletStatus(walletAddress ? 'connected' : null);
  }, [walletAddress]);

  const handleConnectWallet = async () => {
    try {
      setWalletStatus('connecting');
      const address = await connectWallet();
      setWalletStatus('connected');
      toast({ type: 'success', title: 'Wallet Connected', message: `${address.substring(0,6)}...${address.slice(-4)} is now connected.`, duration: 5000 });
    } catch (err) {
      setWalletStatus('error');
      toast({ type: 'error', title: 'Wallet Connection Failed', message: err.message, duration: 7000 });
    }
  };

  const handleSaveProfile = async (e) => {
    e?.preventDefault();
    if (!walletAddress) return toast({ type: 'error', title: 'Not connected', message: 'Connect wallet first' });
    try {
      await fetch('/api/settings/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl_wallet: walletAddress, name: nameInput }),
      });
      await fetchUserProfile(walletAddress);
      toast({ type: 'success', title: 'Profile Updated', message: 'Your name has been saved.' });
      setIsNameModalOpen(false);
    } catch (err) {
      toast({ type: 'error', title: 'Error', message: 'Failed to update profile' });
    }
  };

  const showTelegramComingSoon = () => {
    toast({
      type: 'info',
      title: 'Coming Soon',
      message: 'Telegram trade alerts will be available in a future Synap Pro release.',
      duration: 4500,
    });
  };

  return (
    <div className="main-content dashboard fade-in settings-page" style={{ padding: '40px', overflowY: 'auto', flex: 1, backgroundColor: 'var(--bg)' }}>
      <header className="dash-header" style={{ marginBottom: 40, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 36, margin: 0, fontWeight: 900, letterSpacing: '-1px', color: 'var(--t1)' }}>Settings</h2>
          <p style={{ color: 'var(--t3)', fontSize: 15, marginTop: 8, fontWeight: 500 }}>Manage your profile, API keys, and subscription plan.</p>
        </div>
      </header>

      <div className="settings-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '32px', maxWidth: '1200px' }}>
        
        {/* Left Column */}
        <div className="settings-column" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          
          {/* User Profile Section */}
          <section className="settings-card" style={{ backgroundColor: 'var(--card)', borderRadius: 24, padding: 32, border: '1px solid var(--border)', boxShadow: 'var(--shadow)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: -50, right: -50, width: 200, height: 200, background: 'radial-gradient(circle, rgba(108, 92, 231, 0.15) 0%, rgba(255,255,255,0) 70%)', borderRadius: '50%' }}></div>
            
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 24, letterSpacing: '1.5px', textTransform: 'uppercase' }}>User Profile</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
              <div style={{ width: 88, height: 88, borderRadius: '50%', background: 'linear-gradient(135deg, #6c5ce7, #00d2d3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 36, fontWeight: 800, color: '#fff', boxShadow: '0 8px 32px rgba(108, 92, 231, 0.4)' }}>
                {userProfile?.name ? userProfile.name.substring(0, 2).toUpperCase() : walletAddress ? walletAddress.substring(2, 4).toUpperCase() : '?'}
              </div>
              <div style={{ flex: 1, zIndex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <h4 style={{ fontSize: 26, margin: 0, fontWeight: 800, letterSpacing: '-0.5px', color: 'var(--t1)' }}>{userProfile?.name ? userProfile.name : walletAddress ? `${walletAddress.substring(0,6)}...${walletAddress.slice(-4)}` : 'Not Connected'}</h4>
                  {walletAddress && (
                    <button onClick={() => setIsNameModalOpen(true)} style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--t2)', cursor: 'pointer', padding: 6, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s' }} onMouseOver={e => { e.currentTarget.style.color = 'var(--accent)'; e.currentTarget.style.borderColor = 'var(--accent)'; }} onMouseOut={e => { e.currentTarget.style.color = 'var(--t2)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                    </button>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 12 }}>
                  <button onClick={disconnectWallet} disabled={!walletAddress} style={{ padding: '10px 24px', height: 'auto', fontSize: 13, borderRadius: 12, fontWeight: 700, background: 'rgba(233, 69, 96, 0.1)', color: 'var(--red)', transition: 'all 0.2s', opacity: !walletAddress ? 0.5 : 1 }}>Disconnect</button>
                </div>
              </div>
            </div>
          </section>

          {/* Hyperliquid API Settings */}
          <section className="settings-card" style={{ backgroundColor: 'var(--card)', borderRadius: 24, padding: 32, border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 24, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Exchange Integration</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

              {/* ── Step 1: Private Key ── */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <label style={{ fontSize: 14, fontWeight: 800, color: 'var(--t1)' }}>Hyperliquid API Wallet (Agent) Key</label>
                  {keyStatus === 'saved' && (
                    <span style={{ fontSize: 11, color: 'var(--green)', fontWeight: 800, background: 'rgba(24,184,122,0.15)', padding: '4px 10px', borderRadius: 8 }}>SAVED ✓</span>
                  )}
                </div>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showKey ? 'text' : 'password'}
                    placeholder="Enter your API Wallet Private Key (0x...)"
                    value={hlKey}
                    onChange={(e) => setHlKey(e.target.value)}
                    style={{
                      width: '100%', padding: '14px 80px 14px 16px', borderRadius: 14,
                      border: `1px solid ${keyStatus === 'saved' ? 'var(--green)' : 'var(--border)'}`,
                      background: 'var(--bg)', color: 'var(--t1)', fontSize: 14,
                      fontWeight: 600, fontFamily: 'monospace', outline: 'none',
                      transition: 'border 0.2s', letterSpacing: '1px',
                    }}
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', background: 'var(--border)', padding: '6px 14px', borderRadius: 10, fontSize: 12, fontWeight: 800, color: 'var(--t2)' }}
                  >
                    {showKey ? 'HIDE' : 'SHOW'}
                  </button>
                </div>
                <p style={{ fontSize: 12, color: 'var(--t3)', marginTop: 10, lineHeight: 1.6, fontWeight: 500 }}>
                  This API/Agent key can only perform trading actions on your behalf and has **no withdrawal permissions**, keeping your funds 100% secure.
                </p>
                <button
                  onClick={handleSaveKey}
                  disabled={keyStatus === 'saving' || !hlKey}
                  style={{
                    marginTop: 12, width: '100%', padding: '13px', borderRadius: 12, fontSize: 13,
                    fontWeight: 800, background: keyStatus === 'saved' ? 'var(--green)' : 'var(--accent)',
                    color: '#fff', border: 'none', opacity: (!hlKey || keyStatus === 'saving') ? 0.5 : 1,
                    transition: 'all 0.2s', cursor: !hlKey ? 'not-allowed' : 'pointer',
                  }}
                >
                  {keyStatus === 'saving' ? 'Saving...' : keyStatus === 'saved' ? 'Private Key Saved ✓' : 'Save Private Key'}
                </button>
              </div>

              <div style={{ height: 1, background: 'var(--border)' }} />

              {/* ── Step 2: Wallet Address ── */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <label style={{ fontSize: 14, fontWeight: 800, color: 'var(--t1)' }}>Wallet Address</label>
                  {walletStatus === 'connected' && (
                    <span style={{ fontSize: 11, color: 'var(--green)', fontWeight: 800, background: 'rgba(24,184,122,0.15)', padding: '4px 10px', borderRadius: 8 }}>CONNECTED ✓</span>
                  )}
                </div>

                {walletAddress ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(24,184,122,0.08)', border: '1px solid rgba(24,184,122,0.25)', borderRadius: 14, padding: '14px 16px' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 10px var(--green)', flexShrink: 0 }} />
                    <span style={{ fontFamily: 'monospace', fontSize: 13, fontWeight: 700, color: 'var(--t1)', wordBreak: 'break-all' }}>{walletAddress}</span>
                  </div>
                ) : (
                  <p style={{ fontSize: 13, color: 'var(--t3)', marginBottom: 0, fontWeight: 500 }}>
                    <button onClick={() => window.dispatchEvent(new Event('trigger_wallet_connect'))} 
                    disabled={walletStatus === 'connecting'}
                    style={{ 
                    padding: '16px 24px', fontSize: 15, fontWeight: 800, borderRadius: 16, border: 'none',
                    background: walletStatus === 'connected' ? 'rgba(24,184,122,0.15)' : 'linear-gradient(135deg, #6c5ce7, #00d2d3)',
                    color: walletStatus === 'connected' ? 'var(--green)' : '#fff',
                    border: walletStatus === 'connected' ? '1px solid rgba(24,184,122,0.4)' : 'none',
                    transition: 'all 0.2s', cursor: walletStatus === 'connecting' ? 'wait' : 'pointer',
                    boxShadow: walletStatus === 'connected' ? 'none' : '0 8px 24px rgba(108,92,231,0.4)'
                  }}>
                    {walletStatus === 'connecting' ? 'Connecting...' : walletStatus === 'connected' ? 'Wallet Connected ✓' : '🔗 Connect Wallet'}
                  </button>
                  </p>
                )}
              </div>

            </div>
          </section>


        </div>

        {/* Right Column */}
        <div className="settings-column" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          
          {/* Subscription Model */}
          <section className="settings-card subscription-card" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{ 
              background: 'linear-gradient(145deg, #1e2329, #0d1117)', 
              borderRadius: 24, padding: '2px', position: 'relative', overflow: 'hidden',
              boxShadow: '0 12px 30px rgba(0,0,0,0.1)'
            }}>
              <div style={{ 
                background: 'linear-gradient(145deg, #2b3139, #1a1e24)', 
                borderRadius: 22, padding: 24, height: '100%', display: 'flex', flexDirection: 'column'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                  <div>
                    <h3 style={{ fontSize: 12, fontWeight: 800, color: 'var(--t3)', marginBottom: 8, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Subscription</h3>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <h2 style={{ fontSize: 32, fontWeight: 900, color: '#fff', margin: 0, letterSpacing: '-1px' }}>Early Access</h2>
                    </div>
                    <p style={{ color: 'rgba(255,255,255,0.62)', fontSize: 13, lineHeight: 1.5, marginTop: 8, maxWidth: 520, fontWeight: 600 }}>
                      All features are free for early users. Advanced automation will move into Synap Pro later, and early users will be rewarded in future platform programs.
                    </p>
                  </div>
                  <div style={{ background: 'rgba(24,184,122,0.18)', color: '#7ee0ad', padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 800, letterSpacing: '1px' }}>
                    FREE NOW
                  </div>
                </div>

                <div style={{ flex: 1 }}>
                  <h4 style={{ color: '#fff', fontSize: 13, fontWeight: 900, margin: '0 0 14px 0', letterSpacing: '1px', textTransform: 'uppercase' }}>
                    Future subscription access
                  </h4>
                  <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 18px 0', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {[
                      { tier: 'Pro', title: 'Automatic AI trading', desc: 'Run trades from the Synap.surf AI card using your configured risk parameters.' },
                      { tier: 'Pro', title: 'Strategy auto-trading', desc: 'Subscribed users can let selected strategies execute automatically.' },
                      { tier: 'Pro', title: 'Unlimited AI chat', desc: 'Pro users get unlimited AI market prompts.' },
                      { tier: 'Pro', title: 'Telegram trade notifications', desc: 'Receive Telegram alerts for every trade opened, updated, or closed.' },
                    ].map((feat) => (
                      <li key={feat.title} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, color: '#e6edf3', fontSize: 13, fontWeight: 600, lineHeight: 1.4 }}>
                        <span style={{
                          minWidth: 40, height: 20, borderRadius: 999, flexShrink: 0, marginTop: 1,
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                          background: feat.tier === 'Free' ? 'rgba(255,255,255,0.08)' : 'rgba(24,184,122,0.14)',
                          color: feat.tier === 'Free' ? 'rgba(255,255,255,0.72)' : '#7ee0ad',
                          fontSize: 10, fontWeight: 900, textTransform: 'uppercase'
                        }}>{feat.tier}</span>
                        <span>
                          <span style={{ display: 'block', color: '#fff', fontWeight: 850 }}>{feat.title}</span>
                          <span style={{ display: 'block', color: 'rgba(255,255,255,0.58)', fontSize: 12, marginTop: 2 }}>{feat.desc}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                  <div style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14, padding: '12px 14px', color: 'rgba(255,255,255,0.7)', fontSize: 12, lineHeight: 1.5, fontWeight: 600 }}>
                    Early users can currently use the platform for free and will be rewarded in future. Pricing will be announced before subscriptions are enforced.
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Account Settings */}
          <section className="settings-card" style={{ backgroundColor: 'var(--card)', borderRadius: 24, padding: 32, border: '1px solid var(--border)', boxShadow: 'var(--shadow)' }}>
            <h3 style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', marginBottom: 28, letterSpacing: '1.5px', textTransform: 'uppercase' }}>Security & Preferences</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 6, color: 'var(--t1)' }}>Telegram Notifications</div>
                    <div style={{ fontSize: 13, color: 'var(--t2)', fontWeight: 650, lineHeight: 1.5 }}>
                      Coming soon. Trade alerts will be included with Synap Pro when subscriptions launch.
                    </div>
                  </div>
                  <label
                    className="switch mini"
                    title="Coming soon: Telegram trade alerts will be included with Synap Pro."
                    onClick={(e) => { e.preventDefault(); showTelegramComingSoon(); }}
                    style={{ opacity: 0.55, cursor: 'not-allowed' }}
                  >
                    <input type="checkbox" checked={false} readOnly disabled />
                    <span className="slider round" />
                  </label>
                </div>
                <input 
                  type="text" 
                  placeholder="Telegram setup will be available soon"
                  value={tgToken}
                  readOnly
                  disabled
                  onClick={showTelegramComingSoon}
                  style={{ width: '100%', padding: '12px 16px', borderRadius: 12, border: '1px solid var(--border)', background: 'rgba(255,255,255,0.02)', color: 'var(--t2)', fontSize: 13, cursor: 'not-allowed', opacity: 0.72 }}
                />
              </div>
            </div>
          </section>

        </div>
      </div>

      {/* Name Edit Modal */}
      {isNameModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(10px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'toastIn 0.2s ease' }}>
          <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 24, padding: 32, width: '100%', maxWidth: 400, boxShadow: '0 24px 60px rgba(0,0,0,0.4)', animation: 'slideUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)' }}>
            <h3 style={{ fontSize: 20, fontWeight: 900, marginBottom: 8, color: 'var(--t1)' }}>Edit Profile Name</h3>
            <p style={{ fontSize: 13, color: 'var(--t3)', marginBottom: 24 }}>Set a custom display name to personalize your dashboard experience.</p>
            <form onSubmit={handleSaveProfile}>
              <input 
                type="text" 
                placeholder="Enter your full name"
                autoFocus
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', padding: '14px 16px', borderRadius: 12, color: 'var(--t1)', fontSize: 15, marginBottom: 24, width: '100%', fontWeight: 600, outline: 'none' }} 
              />
              <div style={{ display: 'flex', gap: 12 }}>
                <button type="button" onClick={() => setIsNameModalOpen(false)} style={{ flex: 1, padding: '14px 0', borderRadius: 12, background: 'rgba(255,255,255,0.05)', color: 'var(--t1)', border: '1px solid rgba(255,255,255,0.1)', fontWeight: 700, cursor: 'pointer', transition: 'background 0.2s' }} onMouseOver={e => e.currentTarget.style.background='rgba(255,255,255,0.1)'} onMouseOut={e => e.currentTarget.style.background='rgba(255,255,255,0.05)'}>Cancel</button>
                <button type="submit" style={{ flex: 1, padding: '14px 0', borderRadius: 12, background: 'var(--accent)', color: '#fff', border: 'none', fontWeight: 800, cursor: 'pointer', transition: 'transform 0.2s' }} onMouseOver={e => e.currentTarget.style.transform='translateY(-2px)'} onMouseOut={e => e.currentTarget.style.transform='none'}>Save Name</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
