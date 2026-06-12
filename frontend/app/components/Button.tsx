import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  children: React.ReactNode;
}

export function Button({ variant = 'primary', children, style, ...props }: ButtonProps) {
  const baseStyle: React.CSSProperties = {
    padding: '10px 20px',
    borderRadius: 'var(--radius-md)',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'var(--transition-fast)',
    border: 'none',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontSize: '0.875rem',
  };

  const variants = {
    primary: {
      background: 'var(--accent-gradient)',
      color: '#fff',
      boxShadow: '0 4px 14px 0 rgba(59, 130, 246, 0.39)',
    },
    secondary: {
      background: 'var(--bg-surface-hover)',
      color: 'var(--text-primary)',
      border: '1px solid var(--border-strong)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--text-secondary)',
    }
  };

  const appliedStyle = { ...baseStyle, ...variants[variant], ...style };

  return (
    <button style={appliedStyle} {...props}>
      {children}
    </button>
  );
}
