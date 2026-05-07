'use client';

import { Component } from 'react';

import CustomButton from './CustomButton';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="flex size-12 items-center justify-center rounded-xl bg-destructive/10">
            <span className="text-lg text-destructive">!</span>
          </div>
          <div>
            <p className="text-[14px] font-medium text-foreground">Something went wrong</p>
            <p className="mt-1 max-w-sm text-[13px] text-muted-foreground">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
          </div>
          <CustomButton type="default" onClick={this.handleReset}>
            Try Again
          </CustomButton>
        </div>
      );
    }

    return this.props.children;
  }
}
