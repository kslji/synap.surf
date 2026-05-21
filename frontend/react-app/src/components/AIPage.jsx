import React, { useState, useRef, useEffect } from 'react';

export default function AIPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const simulateStream = async (fullText) => {
    setIsTyping(true);
    setMessages(prev => [...prev, { role: 'ai', content: '' }]);
    
    let currentText = '';
    const chars = fullText.split('');
    
    for (let i = 0; i < chars.length; i++) {
      await new Promise(resolve => setTimeout(resolve, Math.random() * 15 + 5)); 
      currentText += chars[i];
      setMessages(prev => {
        const newMsgs = [...prev];
        newMsgs[newMsgs.length - 1].content = currentText;
        return newMsgs;
      });
    }
    setIsTyping(false);
  };

  const handleSend = (text) => {
    const userMsg = typeof text === 'string' ? text : input.trim();
    if (!userMsg || isTyping) return;
    
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    
    setTimeout(() => {
      simulateStream(`I'm analyzing the markets regarding: "${userMsg}".\n\nBased on current market conditions, real-time news, and algorithmic indicators, this setup presents a high-probability opportunity. The momentum oscillator is trending upward, and on-chain metrics show accumulation. However, always remember to manage your risk dynamically!`);
    }, 400);
  };

  return (
    <div className="main-content fade-in" style={{ 
      display: 'flex', flexDirection: 'column', flex: 1, 
      background: 'radial-gradient(circle at 50% 0%, rgba(108, 92, 231, 0.08) 0%, var(--bg) 60%)', 
      height: '100%', minHeight: 0, position: 'relative', overflow: 'hidden' 
    }}>
      
      {/* Dynamic Background Glows */}
      <div style={{ position: 'absolute', top: '-10%', left: '-10%', width: '40%', height: '40%', background: 'radial-gradient(circle, rgba(0, 210, 211, 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: 0, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-10%', right: '-10%', width: '40%', height: '40%', background: 'radial-gradient(circle, rgba(108, 92, 231, 0.15) 0%, transparent 70%)', filter: 'blur(60px)', zIndex: 0, pointerEvents: 'none' }} />



      {/* Chat Area */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0 40px 40px 40px', display: 'flex', flexDirection: 'column', zIndex: 1 }}>
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
                  { title: 'Market Analysis', desc: 'Analyze current momentum for BTC and ETH', icon: '📈' },
                  { title: 'Strategy Generation', desc: 'Create a mean-reversion strategy for SOL', icon: '🧠' },
                  { title: 'News Summary', desc: 'Summarize today\'s top crypto news', icon: '📰' },
                  { title: 'Risk Management', desc: 'Calculate optimal position sizing', icon: '🛡️' }
                ].map((item, i) => (
                  <button 
                    key={i} 
                    onClick={() => handleSend(item.desc)}
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
              {messages.map((msg, i) => (
                <div key={i} style={{ display: 'flex', gap: 20, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row', animation: 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                  {msg.role === 'ai' && (
                    <div style={{ 
                      width: 44, height: 44, borderRadius: '14px', background: 'linear-gradient(135deg, #1e2329, #0d1117)', 
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.05)'
                    }}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00d2d3" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2l3 6 6 3-6 3-3 6-3-6-6-3 6-3z"/>
                      </svg>
                    </div>
                  )}
                  <div style={{ 
                    background: msg.role === 'user' ? 'linear-gradient(135deg, #00d2d3, #6c5ce7)' : 'var(--card)', 
                    color: msg.role === 'user' ? '#fff' : 'var(--t1)',
                    padding: '20px 24px', 
                    borderRadius: '24px',
                    borderTopRightRadius: msg.role === 'user' ? 6 : 24,
                    borderTopLeftRadius: msg.role === 'ai' ? 6 : 24,
                    fontSize: 15.5,
                    lineHeight: 1.7,
                    fontWeight: 500,
                    boxShadow: msg.role === 'user' ? '0 12px 24px rgba(108, 92, 231, 0.3)' : 'var(--shadow)',
                    border: msg.role === 'ai' ? '1px solid var(--border)' : 'none',
                    maxWidth: '80%',
                    whiteSpace: 'pre-wrap',
                    letterSpacing: '0.2px'
                  }}>
                    {msg.content}
                    {msg.role === 'ai' && isTyping && i === messages.length - 1 && (
                      <span style={{ display: 'inline-block', width: 10, height: 18, background: '#00d2d3', marginLeft: 6, animation: 'blink 1s infinite', borderRadius: 2 }}></span>
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
      <div style={{ padding: '24px 40px 32px 40px', zIndex: 1, flexShrink: 0, background: 'var(--bg)', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <div style={{ 
          maxWidth: '800px', margin: '0 auto', position: 'relative',
          background: 'var(--card)', borderRadius: 16,
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)', border: '1px solid var(--border)',
          transition: 'border 0.3s ease, box-shadow 0.3s ease'
        }}
        onFocus={e => { e.currentTarget.style.borderColor = '#00d2d3'; }}
        onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; }}
        >
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask ALGO BRAIN anything about trading..."
            style={{ 
              width: '100%', padding: '18px 64px 18px 24px', borderRadius: 16, 
              border: 'none', background: 'transparent', 
              color: 'var(--t1)', fontSize: 15, fontWeight: 500,
              outline: 'none'
            }}
          />
          <button 
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
            style={{ 
              position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', 
              background: input.trim() && !isTyping ? 'linear-gradient(135deg, #00d2d3, #6c5ce7)' : 'transparent', 
              width: 40, height: 40, borderRadius: '12px', 
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: input.trim() && !isTyping ? 'pointer' : 'default',
              transition: 'all 0.2s',
              border: 'none',
              opacity: input.trim() && !isTyping ? 1 : 0.5
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={input.trim() && !isTyping ? '#fff' : 'var(--t3)'} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" style={{ transform: 'translateX(-1px)' }}>
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <p style={{ textAlign: 'center', color: 'var(--t3)', fontSize: 12, marginTop: 12, fontWeight: 500 }}>
          ALGO BRAIN can make mistakes. Consider verifying important trading decisions.
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
