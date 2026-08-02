import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[AKAAL Error Boundary] Uncaught Runtime Error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            width: '100vw',
            height: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0B0D11',
            color: '#F9FAFB',
            fontFamily: "'Inter', sans-serif",
            padding: 32,
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              maxWidth: 600,
              width: '100%',
              background: '#14171F',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 16,
              padding: '32px 36px',
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 10,
                  background: 'rgba(239, 68, 68, 0.15)',
                  color: '#EF4444',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: 18,
                }}
              >
                !
              </div>
              <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, color: '#F9FAFB' }}>
                Application Runtime Diagnostic Warning
              </h2>
            </div>

            <p style={{ fontSize: 13, color: '#9CA3AF', lineHeight: 1.5, marginBottom: 20 }}>
              AKAAL encountered an unhandled exception during view rendering. The session vault state remains protected.
            </p>

            {this.state.error && (
              <div
                style={{
                  background: '#0F1117',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: 8,
                  padding: 14,
                  fontSize: 12,
                  fontFamily: "'JetBrains Mono', monospace",
                  color: '#EF4444',
                  marginBottom: 24,
                  maxHeight: 160,
                  overflowY: 'auto',
                  wordBreak: 'break-word',
                }}
              >
                {this.state.error.name}: {this.state.error.message}
              </div>
            )}

            <div style={{ display: 'flex', gap: 12 }}>
              <button
                onClick={this.handleReset}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  background: '#2563EB',
                  color: '#ffffff',
                  border: 'none',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: "'Inter', sans-serif",
                }}
              >
                Reload Application Workspace
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
