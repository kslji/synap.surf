import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function AIPage() {
  const [messages, setMessages] = useState([]);
  const [feedbacks, setFeedbacks] = useState({});
  const wallet = localStorage.getItem('wallet_address');
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  // Chat Sessions and History State
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [deleteConfirmSessionId, setDeleteConfirmSessionId] = useState(null);

  const fetchSessions = async () => {
    if (!wallet) return;
    setIsLoadingSessions(true);
    try {
      const res = await fetch(`/api/chat/sessions?wallet=${encodeURIComponent(wallet)}`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data || []);
      }
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [wallet]);

  const loadSession = async (sessionId) => {
    if (isTyping) return;
    try {
      const res = await fetch(`/api/chat/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
        setActiveSessionId(sessionId);
      } else {
        console.error('Failed to load session:', res.statusText);
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const deleteSession = (sessionId, e) => {
    e.stopPropagation();
    setDeleteConfirmSessionId(sessionId);
  };

  const startNewChat = () => {
    setMessages([]);
    setActiveSessionId(null);
    setInput('');
    setIsTyping(false);
  };

  useEffect(() => {
    const handleReset = () => {
      startNewChat();
      fetchSessions();
    };
    window.addEventListener('resetAIPage', handleReset);
    return () => window.removeEventListener('resetAIPage', handleReset);
  }, [wallet]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const accumulatedRef = useRef('');

  const handleFeedback = async (index, type, text) => {
    const current = feedbacks[index];
    const newFeedback = current === type ? null : type;
    
    setFeedbacks(prev => ({ ...prev, [index]: newFeedback }));
    
    try {
      await fetch('/api/ai/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_index: index, feedback: newFeedback || 'none', text: text.substring(0, 100) })
      });
    } catch(err) {}
  };

  const handleSend = async (text, contextType = 'general') => {
    const userMsg = typeof text === 'string' ? text : input.trim();
    if (!userMsg || isTyping) return;

    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setIsTyping(true);
    accumulatedRef.current = '';
    
    // Add AI message with thinking state
    setMessages(prev => [...prev, { role: 'ai', content: '', isThinking: true, thinkTime: 0 }]);
    
    const startTime = Date.now();
    const interval = setInterval(() => {
      setMessages(prev => prev.map((m, i) => 
        i === prev.length - 1 ? { ...m, thinkTime: Math.floor((Date.now() - startTime) / 1000) } : m
      ));
    }, 1000);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: userMsg, 
          context_type: contextType, 
          wallet: wallet,
          session_id: activeSessionId || undefined
        })
      });

      if (!res.ok) {
        let errMsg = `Server error ${res.status}`;
        try {
          const errData = await res.json();
          if (errData && errData.detail) {
            errMsg = errData.detail;
          }
        } catch (e) {}
        throw new Error(errMsg);
      }

      // Check if backend returned a new Session ID in the headers
      const resSessionId = res.headers.get('X-Session-Id');
      if (resSessionId && resSessionId !== activeSessionId) {
        setActiveSessionId(resSessionId);
      }

      // Stop the timer as soon as we get the first byte (headers)
      clearInterval(interval);
      setMessages(prev => prev.map((m, i) => 
        i === prev.length - 1 ? { ...m, isThinking: false } : m
      ));

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulatedRef.current += chunk;
        const snapshot = accumulatedRef.current;
        setMessages(prev => prev.map((m, i) =>
          i === prev.length - 1 ? { ...m, content: snapshot } : m
        ));
      }
      
      // Refresh the session list once the stream finishes so the new chat shows up immediately
      fetchSessions();
    } catch (err) {
      clearInterval(interval);
      setMessages(prev =>
        prev.map((m, i) =>
          i === prev.length - 1 ? { ...m, content: `Connection Error: ${err.message}`, isThinking: false } : m
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="main-content fade-in ai-page" style={{ 
      display: 'flex', flexDirection: 'row', flex: 1, 
      background: 'radial-gradient(circle at 50% 0%, rgba(255, 159, 67, 0.1) 0%, var(--bg) 60%)', 
      height: '100vh', minHeight: 0, position: 'relative', overflow: 'hidden' 
    }}>
      
      {/* Dynamic Background Glows */}
      <div style={{ position: 'absolute', top: '-10%', left: '-10%', width: '40%', height: '40%', background: 'radial-gradient(circle, rgba(72, 219, 251, 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: 0, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-10%', right: '-10%', width: '40%', height: '40%', background: 'radial-gradient(circle, rgba(255, 159, 67, 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: 0, pointerEvents: 'none' }} />

      {/* LEFT SIDEBAR: CHAT HISTORY */}
      <div className="ai-history-sidebar" style={{
        width: '260px',
        borderRight: '1px solid var(--border)',
        background: 'rgba(255, 255, 255, 0.01)',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 2,
        height: '100%',
        flexShrink: 0
      }}>
        {/* Sidebar Header */}
        <div style={{ padding: '24px 20px 16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '11px', fontWeight: 900, color: 'var(--t1)', letterSpacing: '1px' }}>SYNAP CHATS</span>
          <button
            onClick={startNewChat}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--accent)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
            onMouseOver={e => { e.currentTarget.style.background = 'rgba(79, 124, 138, 0.1)'; }}
            onMouseOut={e => { e.currentTarget.style.background = 'none'; }}
            title="Start New Chat"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
        </div>

        {/* Sidebar Content (Sessions List) */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <h4 style={{ fontSize: '11px', fontWeight: 800, color: 'var(--t3)', letterSpacing: '0.8px', textTransform: 'uppercase', paddingLeft: '8px', marginBottom: '8px' }}>
            Recent Chats
          </h4>

          {isLoadingSessions ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '8px' }}>
              {[1, 2, 3].map(i => (
                <div key={i} style={{ height: '54px', background: 'var(--sub-bg)', borderRadius: '12px', opacity: 0.5, animation: 'pulse 1.5s infinite' }} />
              ))}
            </div>
          ) : !wallet ? (
            <div style={{ padding: '16px 8px', textAlign: 'center', color: 'var(--t3)', fontSize: '13px', fontWeight: 500 }}>
              Connect wallet to view chat history.
            </div>
          ) : sessions.length === 0 ? (
            <div style={{ padding: '16px 8px', textAlign: 'center', color: 'var(--t3)', fontSize: '13px', fontWeight: 500 }}>
              No recent chats found.
            </div>
          ) : (
            sessions.map(s => {
              const isActive = activeSessionId === s.session_id;
              return (
                <div
                  key={s.session_id}
                  onClick={() => loadSession(s.session_id)}
                  style={{
                    background: isActive ? 'var(--sub-bg)' : 'transparent',
                    border: isActive ? '1px solid var(--border)' : '1px solid transparent',
                    borderRadius: '12px',
                    padding: '12px 14px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    position: 'relative',
                    transition: 'all 0.2s ease'
                  }}
                  className="ai-session-item"
                  onMouseOver={e => {
                    if (!isActive) e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  }}
                  onMouseOut={e => {
                    if (!isActive) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  {/* Delete Button */}
                  <button
                    onClick={(e) => deleteSession(s.session_id, e)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '12px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--t3)',
                      cursor: 'pointer',
                      padding: '4px',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.2s ease',
                      zIndex: 3
                    }}
                    className="ai-session-delete"
                    onMouseOver={e => { e.stopPropagation(); e.currentTarget.style.color = 'var(--red)'; e.currentTarget.style.background = 'rgba(233, 69, 96, 0.1)'; }}
                    onMouseOut={e => { e.currentTarget.style.color = 'var(--t3)'; e.currentTarget.style.background = 'none'; }}
                    title="Delete Session"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      <line x1="10" y1="11" x2="10" y2="17"></line>
                      <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                  </button>

                  <div style={{ 
                    fontSize: '13px', 
                    fontWeight: isActive ? 700 : 500, 
                    color: isActive ? 'var(--t1)' : 'var(--t2)',
                    marginRight: '20px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {s.title || 'Untitled Session'}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                      fontSize: '9px',
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      letterSpacing: '0.4px',
                      color: s.context_type === 'market_analysis' ? '#00d2d3' :
                             s.context_type === 'strategy_generation' ? '#6c5ce7' :
                             s.context_type === 'smart_money_holder' ? '#ff9f43' :
                             s.context_type === 'risk_management' ? '#ff6b6b' : '#ff9f43',
                      background: s.context_type === 'market_analysis' ? 'rgba(0, 210, 211, 0.1)' :
                                  s.context_type === 'strategy_generation' ? 'rgba(108, 92, 231, 0.1)' :
                                  s.context_type === 'smart_money_holder' ? 'rgba(255, 159, 115, 0.1)' :
                                  s.context_type === 'risk_management' ? 'rgba(255, 107, 107, 0.1)' : 'rgba(255, 159, 67, 0.1)',
                      padding: '2px 6px',
                      borderRadius: '6px'
                    }}>
                      {s.context_type?.replace('_', ' ') || 'General'}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--t3)', fontWeight: 500 }}>
                      {s.message_count || 0} msgs
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* RIGHT PANEL: CHAT WORKSPACE */}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0, height: '100%', position: 'relative' }}>
        
        {/* Chat Area */}
        <div className="ai-scroll" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '40px 40px 160px 40px', display: 'flex', flexDirection: 'column', zIndex: 1 }}>
          <div className="ai-inner" style={{ maxWidth: '900px', width: '100%', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 32, flex: 1 }}>
            
            {messages.length === 0 ? (
              <div className="ai-empty-state" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', animation: 'fadeIn 1s ease-out' }}>
                <div className="ai-hero-copy" style={{ textAlign: 'center', marginBottom: 48 }}>
                  <h1 style={{ fontSize: 48, fontWeight: 900, color: 'var(--t1)', letterSpacing: '-2px', marginBottom: 16 }}>How can I help you dominate the markets?</h1>
                  <p style={{ fontSize: 18, color: 'var(--t3)', fontWeight: 500 }}>
                    Select a prompt below or type your own question.<br/>
                    <span style={{ fontSize: 14, color: 'var(--accent)', marginTop: 8, display: 'inline-block', fontWeight: 600 }}>
                      Beta Limit: 2 AI Prompts Per Day (Resets Every 24 Hours)
                    </span>
                  </p>
                </div>
                <div className="ai-prompt-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, width: '100%', maxWidth: '800px' }}>
                  {[
                    { title: 'Market Analysis', desc: 'Analyze current momentum across the top crypto markets', icon: '📈', id: 'market_analysis' },
                    { title: 'Strategy Generation', desc: 'What is the best trading strategy right now based on current market conditions?', icon: '🧠', id: 'strategy_generation' },
                    { title: 'Smart money holder', desc: 'Analyze smart money flows and holder behavior', icon: '📰', id: 'smart_money_holder' },
                    { title: 'Risk Management', desc: 'Calculate optimal position sizing', icon: '🛡️', id: 'risk_management' }
                  ].map((item, i) => (
                    <button
                      className="ai-prompt-card" 
                      key={i} 
                      onClick={() => handleSend(item.desc, item.id)}
                      style={{ 
                        background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 20, padding: 24, 
                        textAlign: 'left', transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)', cursor: 'pointer',
                        display: 'flex', flexDirection: 'column', gap: 12, boxShadow: 'var(--shadow)'
                      }}
                      onMouseOver={e => { e.currentTarget.style.borderColor = '#00d2d3'; e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 12px 24px rgba(0, 210, 211, 0.15)'; }}
                      onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'var(--shadow)'; }}
                    >
                      <span style={{ fontSize: 28 }}>{item.icon}</span>
                      <div>
                        <h4 style={{ fontSize: 16, fontWeight: 800, color: 'var(--t1)', marginBottom: 4 }}>{item.title}</h4>
                        <p style={{ fontSize: 13, color: 'var(--t3)', fontWeight: 500 }}>{item.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 32, paddingBottom: 40 }}>
                {/* Header Row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', animation: 'fadeIn 0.5s' }}>
                  <button
                    onClick={startNewChat}
                    style={{
                      background: 'var(--sub-bg)', border: '1px solid var(--border)', borderRadius: 12, padding: '10px 20px',
                      color: 'var(--t2)', fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8,
                      cursor: 'pointer', transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)', backdropFilter: 'blur(10px)'
                    }}
                    onMouseOver={e => { e.currentTarget.style.color = '#ff9f43'; e.currentTarget.style.borderColor = '#ff9f43'; e.currentTarget.style.background = 'rgba(255,159,67,0.1)'; }}
                    onMouseOut={e => { e.currentTarget.style.color = 'var(--t2)'; e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--sub-bg)'; }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
                    New Chat Options
                  </button>
                </div>
                
                {messages.map((msg, i) => (
                  <div key={i} style={{ display: 'flex', gap: 20, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', animation: 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                    <div style={{
                      background: msg.role === 'user' ? 'var(--sub-bg)' : 'transparent',
                      color: 'var(--t1)',
                      padding: msg.role === 'user' ? '12px 20px' : '8px 0', 
                      borderRadius: '20px',
                      fontSize: 15,
                      lineHeight: 1.75,
                      fontWeight: 400,
                      maxWidth: '85%',
                      letterSpacing: '0.1px'
                    }}>
                      {msg.role === 'ai' ? (
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          {msg.isThinking ? (
                            <div style={{ color: 'var(--t3)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8, fontStyle: 'italic', marginBottom: 12 }}>
                              <div style={{ width: 14, height: 14, border: '2px solid var(--t3)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                              Thinking...
                            </div>
                          ) : null}
                          
                          {msg.content && (
                            <ReactMarkdown
                              components={{
                                h1: ({node, ...props}) => <h1 style={{fontSize: 20, fontWeight: 700, color: 'var(--t1)', marginBottom: 16, marginTop: 8}} {...props} />,
                                h2: ({node, ...props}) => <h2 style={{fontSize: 18, fontWeight: 700, color: 'var(--t1)', marginBottom: 12, marginTop: 16}} {...props} />,
                                h3: ({node, ...props}) => <h3 style={{fontSize: 16, fontWeight: 600, color: 'var(--t1)', marginBottom: 8, marginTop: 12}} {...props} />,
                                p: ({node, ...props}) => <p style={{marginBottom: 16, color: 'var(--t1)', lineHeight: 1.7, fontSize: 15}} {...props} />,
                                strong: ({node, ...props}) => <strong style={{color: 'var(--t1)', fontWeight: 600}} {...props} />,
                                ul: ({node, ...props}) => <ul style={{paddingLeft: 24, marginBottom: 16}} {...props} />,
                                ol: ({node, ...props}) => <ol style={{paddingLeft: 24, marginBottom: 16}} {...props} />,
                                li: ({node, ...props}) => <li style={{marginBottom: 8, color: 'var(--t1)', lineHeight: 1.7}} {...props} />,
                                code: ({node, inline, ...props}) => inline
                                  ? <code style={{background: 'var(--sub-bg)', color: 'var(--t1)', padding: '2px 6px', borderRadius: 4, fontSize: 13.5, fontFamily: 'monospace'}} {...props} />
                                  : <code style={{display: 'block', background: 'var(--surface)', color: 'var(--t1)', padding: '16px', borderRadius: 8, fontSize: 13.5, fontFamily: 'monospace', overflowX: 'auto', marginBottom: 16, border: '1px solid var(--border)'}} {...props} />,
                                blockquote: ({node, ...props}) => <blockquote style={{borderLeft: '3px solid var(--border)', paddingLeft: 16, color: 'var(--t2)', fontStyle: 'italic', margin: '16px 0'}} {...props} />,
                                hr: ({node, ...props}) => <hr style={{border: 'none', borderTop: '1px solid var(--border)', margin: '24px 0'}} {...props} />,
                              }}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          )}
                          {isTyping && i === messages.length - 1 && (
                            <span style={{ display: 'inline-block', width: 8, height: 16, background: 'rgba(255,255,255,0.8)', marginLeft: 4, animation: 'blink 1s infinite', borderRadius: 2, verticalAlign: 'middle' }}></span>
                          )}

                          {/* Action Icons (Copy, Like, Dislike) */}
                          {!msg.isThinking && msg.content && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12, opacity: 0.6 }}>
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(msg.content);
                                  const el = document.getElementById(`copy-icon-${i}`);
                                  if (el) {
                                    el.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
                                    setTimeout(() => {
                                      el.innerHTML = '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>';
                                    }, 2000);
                                  }
                                }}
                                style={{ background: 'none', border: 'none', color: 'var(--t2)', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center' }}
                                title="Copy"
                              >
                                <svg id={`copy-icon-${i}`} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                </svg>
                              </button>
                              <button
                                onClick={() => handleFeedback(i, 'like', msg.content)}
                                style={{ background: 'none', border: 'none', color: feedbacks[i] === 'like' ? '#10b981' : 'var(--t2)', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', transition: 'color 0.2s' }}
                                title="Good response"
                              >
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                                </svg>
                              </button>
                              <button
                                onClick={() => handleFeedback(i, 'dislike', msg.content)}
                                style={{ background: 'none', border: 'none', color: feedbacks[i] === 'dislike' ? '#ef4444' : 'var(--t2)', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', transition: 'color 0.2s' }}
                                title="Bad response"
                              >
                                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                                </svg>
                              </button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: 16, fontWeight: 500, lineHeight: 1.6 }}>
                          {msg.content}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Clean Input Area - position: absolute relative to right panel workspace */}
        <div className="ai-composer-bar" style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: '16px 40px 12px 40px', zIndex: 100, background: 'linear-gradient(to top, var(--bg) 80%, transparent)' }}>
          <div className="ai-composer" style={{
            maxWidth: '768px', margin: '0 auto', position: 'relative',
            background: 'var(--white)', borderRadius: 24,
            border: '1px solid var(--border)',
            transition: 'border 0.3s ease, box-shadow 0.3s ease',
            display: 'flex', flexDirection: 'column'
          }}
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(79,124,138,0.1)'; }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; }}
          >
            <div style={{ display: 'flex', alignItems: 'center', width: '100%', padding: '8px 12px 8px 20px' }}>
              <input 
                type="text" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Message Synap..."
                style={{ 
                  flex: 1, padding: '12px 0', 
                  border: 'none', background: 'transparent', 
                  color: 'var(--t1)', fontSize: 15, fontWeight: 400,
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isTyping}
                style={{
                  background: input.trim() && !isTyping ? 'var(--accent)' : 'var(--sub-bg)',
                  width: 36, height: 36, borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: input.trim() && !isTyping ? 'pointer' : 'default',
                  transition: 'all 0.2s',
                  border: '1px solid var(--border)',
                  marginLeft: 12,
                  color: input.trim() && !isTyping ? '#fff' : 'var(--t3)'
                }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="19" x2="12" y2="5"></line>
                  <polyline points="5 12 12 5 19 12"></polyline>
                </svg>
              </button>
            </div>
          </div>
          <p style={{ textAlign: 'center', color: 'var(--t3)', fontSize: 11, marginTop: 8, marginBottom: 0, paddingBottom: 0, fontWeight: 400, letterSpacing: 0.2, lineHeight: 1 }}>
            AI can make mistakes. Please double-check responses.
          </p>
        </div>
      </div>

      {/* DELETE CONFIRMATION MODAL */}
      {deleteConfirmSessionId && (
        <div style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          animation: 'fadeIn 0.2s ease-out'
        }}>
          <div style={{
            background: 'var(--white)',
            border: '1px solid var(--border)',
            borderRadius: '24px',
            padding: '32px',
            maxWidth: '400px',
            width: '90%',
            boxShadow: 'var(--shadow)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
          }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '16px',
              background: 'rgba(233, 69, 96, 0.1)',
              color: 'var(--red)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '24px',
              marginBottom: '20px'
            }}>
              🗑️
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 900, color: 'var(--t1)', marginBottom: '8px' }}>
              Delete Chat History?
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--t3)', fontWeight: 500, lineHeight: 1.5, marginBottom: '24px' }}>
              This action cannot be undone. All messages in this session will be permanently deleted from our servers.
            </p>
            <div style={{ display: 'flex', gap: '12px', width: '100%' }}>
              <button
                onClick={() => setDeleteConfirmSessionId(null)}
                style={{
                  flex: 1,
                  background: 'var(--sub-bg)',
                  border: '1px solid var(--border)',
                  color: 'var(--t2)',
                  borderRadius: '12px',
                  padding: '12px 0',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseOver={e => e.currentTarget.style.background = 'var(--border)'}
                onMouseOut={e => e.currentTarget.style.background = 'var(--sub-bg)'}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  const id = deleteConfirmSessionId;
                  setDeleteConfirmSessionId(null);
                  try {
                    const res = await fetch(`/api/chat/sessions/${id}`, {
                      method: 'DELETE'
                    });
                    if (res.ok) {
                      if (activeSessionId === id) {
                        startNewChat();
                      }
                      fetchSessions();
                    }
                  } catch (err) {
                    console.error('Failed to delete session:', err);
                  }
                }}
                style={{
                  flex: 1,
                  background: 'var(--red)',
                  color: '#fff',
                  borderRadius: '12px',
                  padding: '12px 0',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  boxShadow: '0 4px 12px rgba(233, 69, 96, 0.2)'
                }}
                onMouseOver={e => e.currentTarget.style.background = '#d83b54'}
                onMouseOut={e => e.currentTarget.style.background = 'var(--red)'}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
