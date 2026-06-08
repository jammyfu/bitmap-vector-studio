import { useState, useEffect, useCallback, useRef } from 'react'
import { listen } from '@tauri-apps/api/event'
import { Layout } from './components/Layout'
import { Sidebar } from './components/Sidebar'
import { ParamPanel } from './components/ParamPanel'
import { PreviewPane } from './components/PreviewPane'
import { StatusBar } from './components/StatusBar'
import { DropZone } from './components/DropZone'
import { SettingsModal } from './components/SettingsModal'
import { MarketBrowser } from './components/MarketBrowser'
import { PluginManager } from './components/PluginManager'
import { HistoryPanel } from './components/HistoryPanel'
import { useQueue } from './hooks/useQueue'
import { usePresets } from './hooks/usePresets'
import { useTauri } from './hooks/useTauri'
import type { TraceOptions, AppSettings } from './types'

const DEFAULT_SETTINGS: AppSettings = {
  language: 'en',
  theme: 'system',
  defaultOutputDir: null,
  defaultFormat: 'svg',
  optimizeLevel: 1,
  externalEditor: null,
  apiHost: '127.0.0.1',
  apiPort: 8000,
}

function App() {
  const [envStatus, setEnvStatus] = useState<string>('Checking...')
  const [isReady, setIsReady] = useState(false)
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [marketVisible, setMarketVisible] = useState(false)
  const [pluginVisible, setPluginVisible] = useState(false)
  const [historyVisible, setHistoryVisible] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const toastTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [options, setOptions] = useState<TraceOptions>({
    colormode: 'color',
    hierarchical: 'stacked',
    mode: 'spline',
    filter_speckle: 4,
    color_precision: 6,
    layer_difference: 16,
    corner_threshold: 60,
    length_threshold: 4,
    max_iterations: 10,
    splice_threshold: 45,
    path_precision: 8,
    denoise: false,
    posterize: null,
    max_input_side: null,
  })
  const [livePreview, setLivePreview] = useState(false)
  const [outputFormat, setOutputFormat] = useState<'svg' | 'pdf' | 'png'>('svg')
  const [optimizeLevel, setOptimizeLevel] = useState(1)
  const [previewResult, setPreviewResult] = useState<string | undefined>(undefined)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  const { activePreset, selectPreset, getPresetOptions } = usePresets()
  const queue = useQueue()
  const tauri = useTauri()

  // Toast helper
  const showToast = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type })
    if (toastTimeout.current) clearTimeout(toastTimeout.current)
    toastTimeout.current = setTimeout(() => setToast(null), 3000)
  }, [])

  // Check environment on mount
  useEffect(() => {
    checkEnvironment()
    loadSettings()

    // Listen for menu events
    const unlistenOpen = listen('menu-open', () => {
      handleOpenFileDialog()
    })
    const unlistenAbout = listen('menu-about', () => {
      showToast('Bitmap Vector Studio v0.5.0', 'success')
    })

    return () => {
      unlistenOpen.then((f) => f())
      unlistenAbout.then((f) => f())
    }
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'o':
            e.preventDefault()
            handleOpenFileDialog()
            break
          case 's':
            e.preventDefault()
            // Save preset shortcut handled in ParamPanel
            break
          case ',':
            e.preventDefault()
            setSettingsOpen(true)
            break
          case 'm':
            e.preventDefault()
            setMarketVisible((v) => !v)
            break
          case 'p':
            e.preventDefault()
            setPluginVisible((v) => !v)
            break
          case 'h':
            e.preventDefault()
            setHistoryVisible((v) => !v)
            break
        }
      }
      if (e.key === 'Escape') {
        setMarketVisible(false)
        setPluginVisible(false)
        setHistoryVisible(false)
        setSettingsOpen(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  async function checkEnvironment() {
    try {
      const result = await tauri.checkEnv()
      setEnvStatus(result)
      setIsReady(result.includes('ready') || result.includes('OK'))
    } catch (error) {
      setEnvStatus(`Error: ${error}`)
      setIsReady(false)
    }
  }

  async function loadSettings() {
    try {
      const result = await tauri.getConfig()
      const parsed = JSON.parse(result) as Partial<AppSettings>
      setSettings((prev) => ({ ...prev, ...parsed }))
    } catch {
      // ignore
    }
  }

  async function handleOpenFileDialog() {
    try {
      const files = await tauri.openFileDialog()
      if (files.length > 0) {
        handleAddFiles(files)
      }
    } catch (error) {
      showToast(`Failed to open file dialog: ${error}`, 'error')
    }
  }

  const handleAddFiles = useCallback((files: string[]) => {
    queue.addTasks(files, activePreset)
    showToast(`Added ${files.length} file(s) to queue`, 'success')
  }, [queue, activePreset, showToast])

  const handleStartQueue = useCallback(() => {
    queue.startQueue()
  }, [queue])

  const handlePauseQueue = useCallback(() => {
    queue.pauseQueue()
  }, [queue])

  const handleCancelAll = useCallback(() => {
    queue.tasks.forEach((t) => {
      if (t.status === 'pending' || t.status === 'running') {
        queue.cancelTask(t.id)
      }
    })
  }, [queue])

  const handleClearCompleted = useCallback(() => {
    queue.clearCompleted()
  }, [queue])

  const handleSelectTask = useCallback((id: string) => {
    setSelectedTaskId(id)
    const task = queue.tasks.find((t) => t.id === id)
    if (task) {
      // Load task parameters if available
      const presetOpts = getPresetOptions(task.preset)
      setOptions(presetOpts)
      selectPreset(task.preset)
    }
  }, [queue.tasks, getPresetOptions, selectPreset])

  const handleLoadHistoryParams = useCallback((params: unknown) => {
    const p = params as { inputPath?: string; preset?: string }
    if (p.preset) {
      selectPreset(p.preset)
      setOptions(getPresetOptions(p.preset))
    }
  }, [selectPreset, getPresetOptions])

  const handleSaveSettings = useCallback((newSettings: AppSettings) => {
    setSettings(newSettings)
    showToast('Settings saved', 'success')
  }, [showToast])

  const selectedTask = queue.tasks.find((t) => t.id === selectedTaskId)

  return (
    <div className="app">
      <Layout
        sidebar={
          <Sidebar
            tasks={queue.tasks}
            onRemoveTask={queue.removeTask}
            onCancelTask={queue.cancelTask}
            onReorder={queue.reorderTasks}
            onSelectTask={handleSelectTask}
            selectedTaskId={selectedTaskId}
            onAddFiles={handleAddFiles}
            onLoadHistoryParams={handleLoadHistoryParams}
            onToast={showToast}
          />
        }
        main={
          <ParamPanel
            inputPath={selectedTask?.inputPath}
            options={options}
            onChangeOptions={setOptions}
            livePreview={livePreview}
            onToggleLivePreview={() => setLivePreview((v) => !v)}
            outputFormat={outputFormat}
            onChangeOutputFormat={setOutputFormat}
            optimizeLevel={optimizeLevel}
            onChangeOptimizeLevel={setOptimizeLevel}
            onPreviewResult={setPreviewResult}
            onToast={showToast}
          />
        }
        preview={
          <PreviewPane
            originalSrc={selectedTask?.inputPath}
            resultSrc={previewResult || selectedTask?.outputPath}
            fileName={selectedTask?.fileName}
            inputPath={selectedTask?.inputPath}
            options={JSON.stringify(options)}
            outputFormat={outputFormat}
            onDownload={() => showToast('Download started', 'success')}
            onToast={showToast}
          />
        }
        statusBar={
          <StatusBar
            tasks={queue.tasks}
            isRunning={queue.isRunning}
            onStart={handleStartQueue}
            onPause={handlePauseQueue}
            onCancelAll={handleCancelAll}
            onClearCompleted={handleClearCompleted}
            onToast={showToast}
          />
        }
        dropZone={<DropZone onDropFiles={handleAddFiles} />}
      />

      <div className="app-toolbar">
        <button className="btn btn-sm" onClick={() => setSettingsOpen(true)} title="Settings (Ctrl+,)">
          ⚙ Settings
        </button>
        <button className="btn btn-sm" onClick={() => setMarketVisible(true)} title="Market (Ctrl+M)">
          🛒 Market
        </button>
        <button className="btn btn-sm" onClick={() => setPluginVisible(true)} title="Plugins (Ctrl+P)">
          🔌 Plugins
        </button>
        <button className="btn btn-sm" onClick={() => setHistoryVisible(true)} title="History (Ctrl+H)">
          🕘 History
        </button>
        <div className={`env-badge ${isReady ? 'ready' : 'not-ready'}`} title={envStatus}>
          {isReady ? '● Ready' : '● Not Ready'}
        </div>
      </div>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onSave={handleSaveSettings}
        onToast={showToast}
      />

      <MarketBrowser
        visible={marketVisible}
        onClose={() => setMarketVisible(false)}
        onToast={showToast}
      />

      <PluginManager
        visible={pluginVisible}
        onClose={() => setPluginVisible(false)}
        onToast={showToast}
      />

      <HistoryPanel
        visible={historyVisible}
        onClose={() => setHistoryVisible(false)}
        onLoadTask={(entry) => {
          handleLoadHistoryParams({ preset: entry.preset, inputPath: entry.inputPath })
          showToast(`Loaded history task: ${entry.fileName}`, 'success')
        }}
        onToast={showToast}
      />

      {toast && (
        <div className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  )
}

export default App
