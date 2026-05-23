import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function AIPage() {
  const [messages, setMessages] = useState([]);
  const [feedbacks, setFeedbacks] = useState({});
  const wallet = localStorage.getItem('wallet_address');
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const handleReset = () => {
      setMessages([]);
      setInput('');
      setIsTyping(false);
    };
    window.addEventListener('resetAIPage', handleReset);
    return () => window.removeEventListener('resetAIPage', handleReset);
  }, []);

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
      await fetch('http://localhost:8000/api/ai/feedback', {
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
        body: JSON.stringify({ prompt: userMsg, context_type: contextType, wallet: wallet })
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);

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


  // Wallet is no longer required to view the AI page

  return (
    <div className="main-content fade-in" style={{ 
      display: 'flex', flexDirection: 'column', flex: 1, 
      background: 'radial-gradient(circle at 50% 0%, rgba(255, 159, 67, 0.1) 0%, var(--bg) 60%)', 
      height: '100vh', minHeight: 0, position: 'relative', overflow: 'hidden' 
    }}>
      
      {/* Dynamic Background Glows */}
      <div style={{ position: 'absolute', top: '-10%', left: '-10%', width: '40%', height: '40%', background: 'radial-gradient(circle, rgba(72, 219, 251, 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: 0, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-10%', right: '-10%', width: '40%', height: '40%', background: 'radial-gradient(circle, rgba(255, 159, 67, 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: 0, pointerEvents: 'none' }} />



      {/* Chat Area */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '40px 40px 160px 40px', display: 'flex', flexDirection: 'column', zIndex: 1 }}>
        <div style={{ maxWidth: '900px', width: '100%', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 32, flex: 1 }}>
          
          {messages.length === 0 ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', animation: 'fadeIn 1s ease-out' }}>
              <div style={{ textAlign: 'center', marginBottom: 48 }}>
                <h1 style={{ fontSize: 48, fontWeight: 900, color: 'var(--t1)', letterSpacing: '-2px', marginBottom: 16 }}>How can I help you dominate the markets?</h1>
                <p style={{ fontSize: 18, color: 'var(--t3)', fontWeight: 500 }}>
                  Select a prompt below or type your own question.<br/>
                  <span style={{ fontSize: 14, color: 'var(--accent)', marginTop: 8, display: 'inline-block', fontWeight: 600 }}>
                    (in free trial only 5 credits / prompts are available)
                  </span>
                </p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, width: '100%', maxWidth: '800px' }}>
                {[
                  { title: 'Market Analysis', desc: 'Analyze current momentum across the top crypto markets', icon: '📈', id: 'market_analysis' },
                  { title: 'Strategy Generation', desc: 'What is the best trading strategy right now based on current market conditions?', icon: '🧠', id: 'strategy_generation' },
                  { title: 'Smart money holder', desc: 'Analyze smart money flows and holder behavior', icon: '📰', id: 'smart_money_holder' },
                  { title: 'Risk Management', desc: 'Calculate optimal position sizing', icon: '🛡️', id: 'risk_management' }
                ].map((item, i) => (
                  <button 
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
              {/* Back Button */}
              <div style={{ display: 'flex', justifyContent: 'flex-start', animation: 'fadeIn 0.5s' }}>
                <button 
                  onClick={() => setMessages([])}
                  style={{
                    background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)', borderRadius: 12, padding: '10px 20px',
                    color: 'var(--t2)', fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8,
                    cursor: 'pointer', transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)', backdropFilter: 'blur(10px)'
                  }}
                  onMouseOver={e => { e.currentTarget.style.color = '#ff9f43'; e.currentTarget.style.borderColor = '#ff9f43'; e.currentTarget.style.background = 'rgba(255,159,67,0.1)'; }}
                  onMouseOut={e => { e.currentTarget.style.color = 'var(--t2)'; e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'rgba(0,0,0,0.2)'; }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
                  Back to Options
                </button>
              </div>
              
              {messages.map((msg, i) => (
                <div key={i} style={{ display: 'flex', gap: 20, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', animation: 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                  <div style={{ 
                    background: msg.role === 'user' ? 'rgba(255,255,255,0.06)' : 'transparent', 
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
                              h1: ({node, ...props}) => <h1 style={{fontSize: 20, fontWeight: 700, color: '#fff', marginBottom: 16, marginTop: 8}} {...props} />,
                              h2: ({node, ...props}) => <h2 style={{fontSize: 18, fontWeight: 700, color: '#fff', marginBottom: 12, marginTop: 16}} {...props} />,
                              h3: ({node, ...props}) => <h3 style={{fontSize: 16, fontWeight: 600, color: '#e2e8f0', marginBottom: 8, marginTop: 12}} {...props} />,
                              p: ({node, ...props}) => <p style={{marginBottom: 16, color: 'rgba(255, 255, 255, 0.9)', lineHeight: 1.7, fontSize: 15}} {...props} />,
                              strong: ({node, ...props}) => <strong style={{color: '#fff', fontWeight: 600}} {...props} />,
                              ul: ({node, ...props}) => <ul style={{paddingLeft: 24, marginBottom: 16}} {...props} />,
                              ol: ({node, ...props}) => <ol style={{paddingLeft: 24, marginBottom: 16}} {...props} />,
                              li: ({node, ...props}) => <li style={{marginBottom: 8, color: 'rgba(255, 255, 255, 0.9)', lineHeight: 1.7}} {...props} />,
                              code: ({node, inline, ...props}) => inline
                                ? <code style={{background: 'rgba(255,255,255,0.1)', color: '#e2e8f0', padding: '2px 6px', borderRadius: 4, fontSize: 13.5, fontFamily: 'monospace'}} {...props} />
                                : <code style={{display: 'block', background: '#1e1e1e', color: '#d4d4d4', padding: '16px', borderRadius: 8, fontSize: 13.5, fontFamily: 'monospace', overflowX: 'auto', marginBottom: 16}} {...props} />,
                              blockquote: ({node, ...props}) => <blockquote style={{borderLeft: '3px solid rgba(255,255,255,0.2)', paddingLeft: 16, color: 'rgba(255, 255, 255, 0.6)', fontStyle: 'italic', margin: '16px 0'}} {...props} />,
                              hr: ({node, ...props}) => <hr style={{border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '24px 0'}} {...props} />,
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
                              style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center' }}
                              title="Copy"
                            >
                              <svg id={`copy-icon-${i}`} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                              </svg>
                            </button>
                            <button 
                              onClick={() => handleFeedback(i, 'like', msg.content)}
                              style={{ background: 'none', border: 'none', color: feedbacks[i] === 'like' ? '#10b981' : '#fff', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', transition: 'color 0.2s' }}
                              title="Good response"
                            >
                              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                              </svg>
                            </button>
                            <button 
                              onClick={() => handleFeedback(i, 'dislike', msg.content)}
                              style={{ background: 'none', border: 'none', color: feedbacks[i] === 'dislike' ? '#ef4444' : '#fff', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', transition: 'color 0.2s' }}
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

      {/* Clean Input Area */}
      <div style={{ position: 'fixed', bottom: 0, left: 90, right: 0, padding: '16px 40px 12px 40px', zIndex: 100, background: 'linear-gradient(to top, var(--bg) 80%, transparent)' }}>
        <div style={{ 
          maxWidth: '768px', margin: '0 auto', position: 'relative',
          background: '#2A2A2A', borderRadius: 24,
          border: '1px solid rgba(255,255,255,0.08)',
          transition: 'border 0.3s ease, box-shadow 0.3s ease',
          display: 'flex', flexDirection: 'column'
        }}
        onFocus={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; e.currentTarget.style.background = '#2F2F2F'; }}
        onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.background = '#2A2A2A'; }}
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
                background: input.trim() && !isTyping ? '#fff' : 'rgba(255,255,255,0.05)', 
                width: 36, height: 36, borderRadius: '50%', 
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: input.trim() && !isTyping ? 'pointer' : 'default',
                transition: 'all 0.2s',
                border: 'none',
                marginLeft: 12,
                color: input.trim() && !isTyping ? '#000' : 'var(--t3)'
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5"></line>
                <polyline points="5 12 12 5 19 12"></polyline>
              </svg>
            </button>
          </div>
        </div>
        <p style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 8, marginBottom: 0, paddingBottom: 0, fontWeight: 400, letterSpacing: 0.2, lineHeight: 1 }}>
          AI can make mistakes. Please double-check responses.
        </p>
      </div>

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
      `}</style>
    </div>
  );
}
