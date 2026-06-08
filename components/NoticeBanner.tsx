import React from 'react';
import { AlertCircle } from 'lucide-react';

interface NoticeBannerProps {
  message: string;
  type?: 'info' | 'warning' | 'error';
}

export default function NoticeBanner({ message, type = 'info' }: NoticeBannerProps) {
  let bgClass = 'bg-blue-50 border-blue-200 text-blue-800';
  if (type === 'warning') {
    bgClass = 'bg-amber-50 border-amber-200 text-amber-800';
  } else if (type === 'error') {
    bgClass = 'bg-rose-50 border-rose-200 text-rose-800';
  }

  return (
    <div className={`flex items-start gap-3 p-4 rounded-lg border ${bgClass} text-sm font-medium`}>
      <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>{message}</div>
    </div>
  );
}
