'use client';

import React from 'react';

interface ContainerProps {
  children: React.ReactNode;
}

const Container: React.FC<ContainerProps> = ({ children }) => (
  <div className="flex min-h-screen bg-gray-50">
    {/* Left Side - Form */}
    <div className="flex flex-1 flex-col items-center justify-center bg-white p-4">{children}</div>

    {/* Right Side - Branding */}
    <div
      className="relative hidden flex-1 flex-col items-center justify-center overflow-hidden p-4 md:flex"
      style={{ background: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 50%, #ddd6fe 100%)' }}
    >
      {/* Logo */}
      <div className="absolute left-8 top-8">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-gray-800 text-xl font-bold text-white">
            T
          </div>
          <span className="text-xl font-bold text-gray-800">Tone</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[500px] px-4 text-center">
        {/* Badges */}
        <div className="mb-4 flex justify-center gap-4">
          {['AI Agent Leader', 'High Performer', 'High Performer'].map((badge, index) => (
            <div key={index} className="rounded bg-white p-3 shadow-[0_2px_8px_rgba(0,0,0,0.1)]">
              <div className="mb-1 text-[0.6rem] font-semibold text-orange-500">WINTER 2026</div>
              <div
                className={`text-xs font-bold ${index === 0 ? 'text-orange-500' : 'text-red-500'}`}
              >
                {badge}
              </div>
            </div>
          ))}
        </div>

        {/* Headline */}
        <div className="mb-6 text-[3.5rem] font-bold leading-[1.1] text-gray-800">
          The Future
          <br />
          of Voice AI
        </div>

        {/* Rating */}
        <div className="mb-4 flex items-center justify-center gap-6 text-sm text-gray-500">
          <div className="flex items-center gap-1">
            <span className="text-amber-400">★</span>
            4.4★ 200+ reviews
          </div>
          <div className="flex items-center gap-1">
            <div className="flex h-4 w-4 items-center justify-center rounded-full bg-green-500 text-[0.6rem] text-white">
              G
            </div>
            4.5★ 1000+ reviews
          </div>
        </div>

        {/* Testimonials */}
        <div className="mt-4 flex gap-4">
          {[
            '"The AI assistant has dramatically improved how we manage our schedules."',
            '"Tone\'s Voice AI Agents help us book more demos faster."',
          ].map((quote, index) => (
            <div
              key={index}
              className="flex-1 rounded bg-white p-4 text-left text-xs text-gray-600 shadow-[0_2px_8px_rgba(0,0,0,0.05)]"
            >
              {quote}
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

export default Container;
