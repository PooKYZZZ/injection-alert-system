import React from 'react';

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  
  let bgClass = 'bg-gray-100 text-gray-800 border-gray-200';
  
  if (normalized.includes('verified') || normalized.includes('completed') || normalized.includes('dispatched')) {
    bgClass = 'bg-emerald-50 text-emerald-800 border-emerald-200';
  } else if (normalized.includes('pending') || normalized.includes('processing')) {
    bgClass = 'bg-amber-50 text-amber-800 border-amber-200';
  } else if (normalized.includes('disputed') || normalized.includes('error') || normalized.includes('failed')) {
    bgClass = 'bg-rose-50 text-rose-800 border-rose-200';
  }
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${bgClass}`}>
      {status}
    </span>
  );
}
