import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import Header from './components/Header'

/// App component - main entry point for the Bitmap Vector Studio desktop application.
/// Provides a simple framework with header, main content area, and Python environment status.
function App() {
  const [envStatus, setEnvStatus] = useState<string>('Checking...')
  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    checkEnvironment()
  }, [])

  /// Check the Python environment by invoking the Rust backend command.
  async function checkEnvironment() {
    try {
      const result = await invoke<string>('check_env')
      setEnvStatus(result)
      setIsReady(result.includes('ready') || result.includes('OK'))
    } catch (error) {
      setEnvStatus(`Error: ${error}`)
      setIsReady(false)
    }
  }

  /// Open a file dialog to select images for conversion.
  async function openFileDialog() {
    try {
      const files = await invoke<string[]>('open_file_dialog')
      console.log('Selected files:', files)
      // TODO: pass files to conversion pipeline
    } catch (error) {
      console.error('Failed to open file dialog:', error)
    }
  }

  /// Start the Python API server on the default port.
  async function startApi() {
    try {
      const pid = await invoke<number>('start_api', { port: 8000 })
      console.log('API server started with PID:', pid)
      setEnvStatus('API server running (PID: ' + pid + ')')
      setIsReady(true)
    } catch (error) {
      console.error('Failed to start API:', error)
      setEnvStatus(`API start failed: ${error}`)
    }
  }

  return (
    <div className="app">
      <Header />
      <main className="main-content">
        <section className="status-panel">
          <h2>Environment Status</h2>
          <div className={`status-badge ${isReady ? 'ready' : 'not-ready'}`}>
            {envStatus}
          </div>
          <div className="actions">
            <button onClick={checkEnvironment}>Refresh</button>
            <button onClick={openFileDialog}>Open Files...</button>
            <button onClick={startApi}>Start API Server</button>
          </div>
        </section>

        <section className="content-area">
          <div className="placeholder">
            <h3>Welcome to Bitmap Vector Studio</h3>
            <p>
              This desktop application provides an Illustrator-like experience for
              bitmap-to-SVG vector conversion powered by VTracer.
            </p>
            <p>
              Use the buttons above to open images or start the backend API server.
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
