import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  children: React.ReactNode;
  loading?: boolean;
}

export function Button({
  variant = 'primary',
  size = 'md',
  children,
  loading = false,
  disabled,
  className = '',
  ...props
}: ButtonProps) {
  const variantClass = `btn-${variant}`;
  const sizeClass = size !== 'md' ? `btn-${size}` : '';

  return (
    <button
      className={`btn ${variantClass} ${sizeClass} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span style={{
          width: '12px', height: '12px', borderRadius: '50%',
          border: '2px solid currentColor', borderTopColor: 'transparent',
          display: 'inline-block',
          animation: 'spin 0.6s linear infinite',
        }} />
      )}
      {children}
    </button>
  );
}

// Add spin keyframe via style tag workaround for server components
export function SpinStyle() {
  return (
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  );
}
