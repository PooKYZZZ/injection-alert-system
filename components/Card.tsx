import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export default function Card({ children, className = '', id }: CardProps) {
  return (
    <div id={id} className={`bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden ${className}`}>
      {children}
    </div>
  );
}
