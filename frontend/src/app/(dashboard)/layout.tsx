'use client';

import React from 'react';
import ErrorBoundary from '../../components/shared/ErrorBoundary';
import MainLayout from '../../components/shared/MainLayout';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <MainLayout>
      <ErrorBoundary>{children}</ErrorBoundary>
    </MainLayout>
  );
}
