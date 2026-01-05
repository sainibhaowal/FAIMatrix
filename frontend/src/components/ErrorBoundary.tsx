"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { ErrorState } from "./ui/EmptyState";
import { Button } from "./ui/Button";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex h-[50vh] w-full items-center justify-center p-4">
          <ErrorState
            title="Something went wrong"
            message={this.state.error?.message || "An unexpected error occurred."}
            onRetry={() => this.setState({ hasError: false })}
            onGoBack={() => window.location.reload()}
          />
        </div>
      );
    }

    return this.props.children;
  }
}
