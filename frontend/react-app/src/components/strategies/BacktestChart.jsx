import React, { useEffect, useRef, useState } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';

export default function BacktestChart({ symbol, interval, trades }) {
  const chartContainerRef = useRef();
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    let isMounted = true;
    const fetchCandles = async () => {
      setLoading(true);
      try {
        // Calculate 1-month lookback
        const tfCandles = {'1m': 43200, '5m': 8640, '15m': 2880, '1h': 720, '4h': 180, '1d': 30};
        const lookback = Math.min(2000, Math.max(50, tfCandles[interval] || 720));
        
        const res = await fetch(`/api/candles?coin=${symbol}&timeframe=${interval}&lookback=${lookback}`);
        const data = await res.json();
        
        // Remove duplicates and sort by time
        const uniqueData = Array.from(new Map(data.map(item => [item.time, item])).values())
                                .sort((a, b) => a.time - b.time);
                                
        if (isMounted) setChartData(uniqueData);
      } catch (err) {
        console.error("Failed to fetch candles", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchCandles();
    return () => { isMounted = false; };
  }, [symbol, interval]);

  useEffect(() => {
    if (!chartContainerRef.current || chartData.length === 0) return;
    
    const containerWidth = chartContainerRef.current.clientWidth;
    if (containerWidth === 0) return; // Wait for layout

    const chart = createChart(chartContainerRef.current, {
      width: containerWidth,
      height: 400,
      layout: {
        background: { type: 'solid', color: 'rgba(26, 30, 35, 1)' },
        textColor: '#D9D9D9',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00e5ff',
      downColor: '#ff3366',
      borderDownColor: '#ff3366',
      borderUpColor: '#00e5ff',
      wickDownColor: '#ff3366',
      wickUpColor: '#00e5ff',
    });

    candleSeries.setData(chartData);

    if (trades && trades.length > 0) {
      const validTimes = new Set(chartData.map(d => d.time));
      
      const markers = trades
        .filter(trade => validTimes.has(trade.time))
        .map(trade => ({
          time: trade.time,
          position: trade.side === 'buy' ? 'belowBar' : 'aboveBar',
          color: trade.side === 'buy' ? '#00e5ff' : '#ff3366',
          shape: trade.side === 'buy' ? 'arrowUp' : 'arrowDown',
          text: trade.text || (trade.side === 'buy' ? 'BUY' : 'SELL'),
        }));
      
      // Sort markers by time as required by lightweight-charts
      markers.sort((a, b) => a.time - b.time);
      candleSeries.setMarkers(markers);
    }

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [chartData, trades]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '400px', marginTop: '20px', marginBottom: '20px', borderRadius: '16px', overflow: 'hidden', border: '1px solid var(--border)' }}>
      {loading && (
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10, background: 'rgba(26, 30, 35, 0.8)' }}>
          <div className="spinner-glow" style={{ width: 40, height: 40 }}></div>
        </div>
      )}
      <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}
