'use client';

import { CircleCheck, CircleX, Info, TriangleAlert } from 'lucide-react';
import { Toaster as Sonner, type ToasterProps } from 'sonner';

const Toaster = ({ ...props }: ToasterProps) => (
  <Sonner
    theme="light"
    position="top-right"
    className="toaster group"
    gap={12}
    closeButton
    icons={{
      success: <CircleCheck className="size-[18px] text-emerald-500" strokeWidth={2.5} />,
      info: <Info className="size-[18px] text-blue-500" strokeWidth={2.5} />,
      warning: <TriangleAlert className="size-[18px] text-amber-500" strokeWidth={2.5} />,
      error: <CircleX className="size-[18px] text-red-500" strokeWidth={2.5} />,
    }}
    toastOptions={{
      unstyled: true,
      classNames: {
        toast:
          'w-[356px] flex items-center gap-3 rounded-xl border border-border/60 bg-white px-4 py-3.5 shadow-[0_4px_24px_-4px_rgba(0,0,0,0.1)] backdrop-blur-sm data-[type=success]:border-l-[3px] data-[type=success]:border-l-emerald-500 data-[type=error]:border-l-[3px] data-[type=error]:border-l-red-500 data-[type=warning]:border-l-[3px] data-[type=warning]:border-l-amber-500 data-[type=info]:border-l-[3px] data-[type=info]:border-l-blue-500',
        icon: 'mt-0.5 shrink-0',
        content: 'flex-1 min-w-0',
        title: 'text-[13px] font-semibold leading-tight text-gray-900',
        description: 'mt-1 text-[12px] leading-snug text-gray-500',
        closeButton:
          'absolute top-2.5 right-2.5 cursor-pointer rounded-md p-0.5 text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 hover:text-gray-600 hover:bg-gray-100',
      },
    }}
    {...props}
  />
);

export { Toaster };
