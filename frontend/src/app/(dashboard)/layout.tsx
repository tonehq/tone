'use client';

import React from 'react';
import MainLayout from '../../components/shared/MainLayout';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return <MainLayout>{children}</MainLayout>;
}
