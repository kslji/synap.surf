export const relTime = (iso) => {
  try {
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return Math.round(s) + 's ago';
    if (s < 3600) return Math.round(s / 60) + 'm ago';
    if (s < 86400) return Math.round(s / 3600) + 'h ago';
    return Math.round(s / 86400) + 'd ago';
  } catch { return '—'; }
};

export const absTime = (iso) => {
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(',', '');
  } catch { return '—'; }
}

export const fmt = (n) => Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const coinIcon = (coin) => {
  return (coin || '??').slice(0, 2).toUpperCase();
};

export const coinClass = (coin) => {
  return 'def';
};
