import { useState } from 'react';
import { useToast } from '../Toast';

export default function ProposalPage() {
  const [type, setType] = useState('suggestion');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    const wallet_address = localStorage.getItem('wallet_address');
    
    if (!wallet_address || wallet_address === 'null') {
      toast({ type: 'error', title: 'Wallet Not Connected', message: 'Please connect your wallet to submit a proposal.', duration: 5000 });
      setIsSubmitting(false);
      return;
    }
    
    try {
      const res = await fetch('/api/proposals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address,
          type,
          subject,
          description
        })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to submit proposal');
      }
      
      setSubmitted(true);
      setSubject('');
      setDescription('');
      toast({ type: 'success', title: 'Proposal Sent', message: 'Thank you! Your feedback has been recorded.', duration: 5000 });
      setTimeout(() => setSubmitted(false), 3000);
    } catch (err) {
      toast({ type: 'error', title: 'Submission Failed', message: err.message, duration: 6000 });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="proposal-terminal" style={{ 
      flex: 1, 
      padding: '60px 20px', 
      background: 'var(--bg)', 
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      <div style={{ width: '100%', maxWidth: 720 }}>
        <header style={{ textAlign: 'center', marginBottom: 50 }}>
          <div style={{ 
            display: 'inline-flex', 
            background: 'rgba(79, 124, 138, 0.1)', 
            color: 'var(--accent)', 
            padding: '8px 20px', 
            borderRadius: 30, 
            fontSize: 11, 
            fontWeight: 800, 
            marginBottom: 20,
            textTransform: 'uppercase',
            letterSpacing: '1px'
          }}>
            Community Hub
          </div>
          <h1 style={{ fontSize: 42, fontWeight: 900, color: 'var(--t1)', marginBottom: 16, letterSpacing: '-1.5px' }}>
            Shape the Future
          </h1>
          <p style={{ color: 'var(--t3)', fontSize: 16, lineHeight: 1.6, maxWidth: 600, margin: '0 auto' }}>
            Your insights drive our evolution. Submit bugs, suggest features, or propose new algorithmic concepts to earn rewards.
          </p>
          <div style={{ 
            marginTop: 24, 
            padding: '16px 24px', 
            background: 'var(--surface)', 
            border: '1px solid var(--border)', 
            borderRadius: 20,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 12
          }}>
            <div style={{ background: 'var(--accent)', width: 8, height: 8, borderRadius: '50%' }}></div>
            <span style={{ fontSize: 13, color: 'var(--t1)', fontWeight: 700 }}>
              Team-reviewed proposals earn <span style={{ color: 'var(--accent)' }}>Bonus Points</span> for future benefits.
            </span>
          </div>
        </header>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 32 }}>
          <div 
            className={`strat-item${type === 'bug' ? ' active' : ''}`} 
            style={{ 
              padding: '24px 32px', 
              cursor: 'pointer', 
              borderRadius: 24,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              background: type === 'bug' ? 'rgba(246, 70, 93, 0.03)' : 'var(--surface)',
              borderColor: type === 'bug' ? 'var(--red)' : 'var(--border)'
            }}
            onClick={() => setType('bug')}
          >
            <div style={{ 
              background: type === 'bug' ? 'var(--red)' : 'rgba(246, 70, 93, 0.1)', 
              color: type === 'bug' ? '#fff' : 'var(--red)', 
              width: 48, 
              height: 48, 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 16,
              transition: 'all 0.3s'
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </div>
            <div>
              <h4 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>Report Bug</h4>
              <p style={{ margin: '6px 0 0 0', fontSize: 13, color: 'var(--t3)', lineHeight: 1.4 }}>Help us squash glitches and improve stability.</p>
            </div>
          </div>

          <div 
            className={`strat-item${type === 'suggestion' ? ' active' : ''}`} 
            style={{ 
              padding: '24px 32px', 
              cursor: 'pointer', 
              borderRadius: 24,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              background: type === 'suggestion' ? 'rgba(79, 124, 138, 0.03)' : 'var(--surface)',
              borderColor: type === 'suggestion' ? 'var(--accent)' : 'var(--border)'
            }}
            onClick={() => setType('suggestion')}
          >
            <div style={{ 
              background: type === 'suggestion' ? 'var(--accent)' : 'rgba(79, 124, 138, 0.1)', 
              color: type === 'suggestion' ? '#fff' : 'var(--accent)', 
              width: 48, 
              height: 48, 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 16,
              transition: 'all 0.3s'
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 5v14M5 12h14"/></svg>
            </div>
            <div>
              <h4 style={{ margin: 0, fontSize: 18, fontWeight: 800 }}>New Proposal</h4>
              <p style={{ margin: '6px 0 0 0', fontSize: 13, color: 'var(--t3)', lineHeight: 1.4 }}>Suggest new features or strategy logic.</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ 
          background: 'var(--surface)', 
          padding: 40, 
          borderRadius: 32, 
          border: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 32,
          boxShadow: 'var(--shadow)'
        }}>
          <div className="exec-field">
            <label style={{ fontSize: 11, letterSpacing: '0.5px', marginBottom: 12, display: 'block' }}>SUBJECT</label>
            <div className="exec-input-wrap" style={{ height: 60, borderRadius: 16 }}>
              <input 
                placeholder={type === 'bug' ? "What went wrong?" : "What's your big idea?"}
                required 
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                style={{ fontSize: 15 }}
              />
            </div>
          </div>

          <div className="exec-field">
            <label style={{ fontSize: 11, letterSpacing: '0.5px', marginBottom: 12, display: 'block' }}>DETAILED DESCRIPTION</label>
            <div style={{ 
              background: 'var(--sub-bg)', 
              border: '1px solid var(--border)', 
              borderRadius: 20, 
              padding: 24,
              transition: 'all 0.2s',
              borderWidth: 2
            }}>
              <textarea 
                style={{ 
                  width: '100%', 
                  background: 'transparent', 
                  border: 'none', 
                  color: 'var(--t1)', 
                  minHeight: 220, 
                  outline: 'none',
                  fontFamily: 'inherit',
                  fontSize: 15,
                  lineHeight: 1.6,
                  resize: 'none'
                }} 
                placeholder={type === 'bug' ? "Steps to reproduce, expected behavior, and actual results..." : "Describe the feature, technical reasoning, and potential impact..."}
                required
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>

          <button 
            className="exec-btn" 
            style={{ 
              height: 64, 
              borderRadius: 20, 
              fontSize: 17, 
              background: submitted ? 'var(--green)' : 'var(--accent)',
              boxShadow: 'none'
            }} 
            type="submit"
          >
            {submitted ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><polyline points="20 6 9 17 4 12"/></svg>
                PROPOSAL SUBMITTED
              </div>
            ) : isSubmitting ? (
              'SENDING...'
            ) : (
              'SEND PROPOSAL'
            )}
          </button>
        </form>

        <footer style={{ marginTop: 40, textAlign: 'center', opacity: 0.6 }}>
          <p style={{ fontSize: 12, color: 'var(--t3)' }}>
            &copy; 2026 Synap Intelligence Unit &middot; Decentralized Feedback Protocol
          </p>
        </footer>
      </div>
    </div>
  );
}
