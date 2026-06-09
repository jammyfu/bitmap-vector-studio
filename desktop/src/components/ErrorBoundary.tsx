import React, { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info)
    // 可以上报到错误追踪服务
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ padding: 32, textAlign: 'center' }}>
          <h2 style={{ color: 'var(--error)' }}>⚠️ 出错了</h2>
          <p style={{ color: 'var(--text-secondary)' }}>
            组件渲染时发生错误。请刷新页面重试。
          </p>
          <button 
            onClick={() => window.location.reload()}
            style={{ marginTop: 16, padding: '8px 16px' }}
          >
            刷新页面
          </button>
          {import.meta.env.DEV && (
            <pre style={{ marginTop: 16, textAlign: 'left', fontSize: 12 }}>
              {this.state.error?.stack}
            </pre>
          )}
        </div>
      )
    }
    return this.props.children
  }
}
