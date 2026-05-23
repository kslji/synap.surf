export const parseISO = (iso) => {
  if (!iso) return new Date();
  if (typeof iso === 'string' && !iso.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(iso)) {
    return new Date(iso + 'Z');
  }
  return new Date(iso);
};

export const getTimeZoneAbbrev = (date = new Date()) => {
  try {
    const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
    if (tzName.includes('Kolkata') || tzName.includes('Calcutta') || tzName === 'Asia/Kolkata') {
      return 'IST';
    }
    
    const parts = Intl.DateTimeFormat('en-US', { timeZoneName: 'short' }).formatToParts(date);
    const tzPart = parts.find(p => p.type === 'timeZoneName')?.value || '';
    
    if (tzPart.includes('GMT+5:30') || tzPart.includes('UTC+5:30') || tzPart.includes('India Standard Time')) {
      return 'IST';
    }
    
    if (tzName.includes('New_York') || tzName.includes('Detroit') || tzName.includes('Indiana') || tzName.includes('Kentucky')) {
      const isDST = (date.getTimezoneOffset() === 240);
      return isDST ? 'EDT' : 'EST';
    }
    if (tzName.includes('Chicago') || tzName.includes('Winnipeg') || tzName.includes('Dallas')) {
      const isDST = (date.getTimezoneOffset() === 300);
      return isDST ? 'CDT' : 'CST';
    }
    if (tzName.includes('Denver') || tzName.includes('Phoenix')) {
      if (tzName.includes('Phoenix')) return 'MST';
      const isDST = (date.getTimezoneOffset() === 360);
      return isDST ? 'MDT' : 'MST';
    }
    if (tzName.includes('Los_Angeles') || tzName.includes('Vancouver')) {
      const isDST = (date.getTimezoneOffset() === 420);
      return isDST ? 'PDT' : 'PST';
    }
    
    return tzPart;
  } catch {
    return '';
  }
};

export const relTime = (iso) => {
  try {
    const s = (Date.now() - parseISO(iso).getTime()) / 1000;
    if (s < 60) return Math.round(s) + 's ago';
    if (s < 3600) return Math.round(s / 60) + 'm ago';
    if (s < 86400) return Math.round(s / 3600) + 'h ago';
    return Math.round(s / 86400) + 'd ago';
  } catch { return '—'; }
};

export const absTime = (iso) => {
  try {
    const d = parseISO(iso);
    const formatted = d.toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(',', '');
    const tz = getTimeZoneAbbrev(d);
    return tz ? `${formatted} ${tz}` : formatted;
  } catch { return '—'; }
};

export const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const coinIcon = (coin) => {
  return (coin || '??').slice(0, 2).toUpperCase();
};

export const coinClass = (coin) => {
  return 'def';
};
