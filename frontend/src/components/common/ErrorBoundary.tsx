import React, { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  correlationId: string;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    correlationId: "",
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    const errorWithId = error as Error & { requestId?: string };
    const generatedId =
      errorWithId.requestId ||
      `err_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 8)}`;
    return {
      hasError: true,
      error,
      correlationId: generatedId,
    };
  }

  public componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    // Log structured frontend error to console
    console.error("[EazyDoc ErrorBoundary Caught Exception]", {
      correlationId: this.state.correlationId,
      message: error.message,
      name: error.name,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
    });
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      correlationId: "",
    });
    if (this.props.onReset) {
      this.props.onReset();
    } else {
      window.location.reload();
    }
  };

  private handleCopyCorrelationId = () => {
    if (this.state.correlationId) {
      navigator.clipboard.writeText(this.state.correlationId);
    }
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-slate-50 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8">
          <div className="max-w-md w-full bg-white shadow-xl rounded-2xl p-8 border border-slate-100 text-center">
            <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <h1 className="text-2xl font-bold text-slate-900 tracking-tight mb-2">
              An unexpected error occurred
            </h1>
            <p className="text-sm text-slate-600 mb-6 leading-relaxed">
              Our engineering team has been notified. If this issue persists,
              please share the incident correlation ID below with support.
            </p>

            {this.state.correlationId && (
              <div className="mb-6 p-3 bg-slate-100 rounded-lg border border-slate-200 text-left">
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 flex justify-between items-center">
                  <span>Incident Reference ID</span>
                  <button
                    type="button"
                    onClick={this.handleCopyCorrelationId}
                    className="text-primary hover:text-primary-dark text-xs underline font-medium focus:outline-none"
                  >
                    Copy
                  </button>
                </div>
                <div className="font-mono text-xs text-slate-800 break-all select-all">
                  {this.state.correlationId}
                </div>
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                type="button"
                onClick={this.handleReset}
                className="w-full sm:w-auto px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg text-sm transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Reload Page
              </button>
              <a
                href="/"
                className="w-full sm:w-auto px-5 py-2.5 bg-white hover:bg-slate-50 text-slate-700 font-medium rounded-lg text-sm border border-slate-300 transition-colors inline-flex justify-center items-center focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2"
              >
                Go to Homepage
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

