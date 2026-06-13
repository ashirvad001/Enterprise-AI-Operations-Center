import React from 'react';

interface CardProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  className?: string;
  style?: React.CSSProperties;
  action?: React.ReactNode;
  padding?: string;
}

export function Card({ children, title, subtitle, className = '', style, action, padding }: CardProps) {
  return (
    <div className={`glass-card ${className}`} style={style}>
      {(title || action) && (
        <div className="card-header">
          <div>
            {title && <div className="card-title">{title}</div>}
            {subtitle && <div className="card-subtitle">{subtitle}</div>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="card-body" style={padding ? { padding } : undefined}>
        {children}
      </div>
    </div>
  );
}

// Stat card variant
interface StatCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaType?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  iconBg?: string;
  sparkline?: number[];
  className?: string;
}

export function StatCard({ label, value, delta, deltaType = 'up', icon, iconBg, sparkline, className = '' }: StatCardProps) {
  const maxSpark = sparkline ? Math.max(...sparkline) : 1;

  return (
    <div className={`glass-card stat-card ${className}`}>
      <div className="flex items-center justify-between">
        <div className="stat-label">{label}</div>
        {icon && (
          <div className="stat-icon" style={{ background: iconBg || 'rgba(59,130,246,0.15)' }}>
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-center gap-3" style={{ flexWrap: 'wrap' }}>
        <div className="stat-value">{value}</div>
        {delta && (
          <div className={`stat-delta ${deltaType}`}>
            {deltaType === 'up' ? '↑' : deltaType === 'down' ? '↓' : '→'} {delta}
          </div>
        )}
      </div>

      {sparkline && (
        <div className="sparkline">
          {sparkline.map((v, i) => (
            <div
              key={i}
              className="sparkline-bar"
              style={{ height: `${Math.round((v / maxSpark) * 100)}%` }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
