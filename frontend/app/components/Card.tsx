import React from 'react';

interface CardProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
}

export function Card({ children, title, className = '' }: CardProps) {
  return (
    <div className={`glass-panel ${className}`} style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {title && <h3 style={{ fontSize: '1.125rem', color: 'var(--text-primary)', margin: 0 }}>{title}</h3>}
      <div>{children}</div>
    </div>
  );
}
