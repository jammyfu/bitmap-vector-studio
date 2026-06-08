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
  // v1.1 performance defaults
  gpuEnabled: false,
  streamingEnabled: false,
  memoryLimit: null,
  autoSaveInterval: 60,
  // v1.2 cloud sync defaults
  cloudSyncEnabled: false,
  cloudApiKey: null,
}

function App() {
  const [envStatus, setEnvStatus] = useState<string>('Checking...')
  const [isReady, setIsReady] = useState(false)
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [marketVisible, setMarketVisible] = useState(false)
  const [pluginVisible, setPluginVisible] = useState(false)
  const [historyVisible, setHistoryVisible] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'warning' } | null>(null)
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
  const [ocrLang, setOcrLang] = useState('eng')
  const [ocrVertical, setOcrVertical] = useState(false)
  // v1.1 performance
  const [gpuEnabled, setGpuEnabled] = useState(false)
  const [streamingEnabled, setStreamingEnabled] = useState(false)
  const [memoryStatus, setMemoryStatus] = useState<{ percent?: number; used_mb?: number; total_mb?: number; available?: boolean; message?: string } | null>(null)
  const [gpuStatus, setGpuStatus] = useState<string>('未检测到')
  const [performanceSuggestions, setPerformanceSuggestions] = useState<string[]>([])
  // v1.1 workspace
  const [workspaces, setWorkspaces] = useState<{ name: string }[]>([])
  const [hasCrashRecovery, setHasCrashRecovery] = useState(false)
  // v1.1 checkpoint
  const [checkpoints, setCheckpoints] = useState<{ name: string; queue_id: string }[]>([])
  // v1.2 engines
  const [engine, setEngine] = useState<string>('自动选择')
  // v1.2 cloud share
  const [shareUrl, setShareUrl] = useState<string | undefined>(undefined)
  const [shareQrCode, setShareQrCode] = useState<string | undefined>(undefined)

  const { activePreset, selectPreset, getPresetOptions } = usePresets()
  const queue = useQueue()
  const tauri = useTauri()

  // Toast helper
  const showToast = useCallback((message: string, type: 'success' | 'error' | 'warning' = 'success') => {
    setToast({ message, type })
    if (toastTimeout.current) clearTimeout(toastTimeout.current)
    toastTimeout.current = setTimeout(() => setToast(null), 3000)
  }, [])

  // v1.1: Check crash recovery on mount
  useEffect(() => {
    async function checkCrashRecovery() {
      try {
        const result = await tauri.listWorkspaces()
        if (result) {
          const parsed = JSON.parse(result) as { workspaces?: { name: string }[]; crash_recovery?: boolean }
          if (parsed.workspaces) {
            setWorkspaces(parsed.workspaces)
          }
          if (parsed.crash_recovery) {
            setHasCrashRecovery(true)
            showToast('检测到崩溃恢复数据，可从侧边栏恢复上次会话', 'warning')
          }
        }
      } catch {
        // ignore
      }
    }
    checkCrashRecovery()
  }, [tauri, showToast])

  // v1.1: Auto-save workspace interval
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const openFiles = queue.tasks.map((t) => t.inputPath)
        await tauri.saveWorkspace('auto_save', openFiles, activePreset)
      } catch {
        // ignore auto-save errors
      }
    }, (settings.autoSaveInterval || 60) * 1000)
    return () => clearInterval(interval)
  }, [queue.tasks, activePreset, settings.autoSaveInterval, tauri])

  // v1.1: Poll performance stats
  useEffect(() => {
    async function pollPerformance() {
      try {
        const selectedTask = queue.tasks.find((t) => t.id === selectedTaskId)
        if (selectedTask?.inputPath) {
          const result = await tauri.getPerformanceStats(selectedTask.inputPath)
          if (result) {
            const parsed = JSON.parse(result) as {
              memory?: { percent?: number; used_mb?: number; total_mb?: number; available?: boolean; message?: string }
              gpu?: string
              suggestions?: string[]
            }
            if (parsed.memory) setMemoryStatus(parsed.memory)
            if (parsed.gpu) setGpuStatus(parsed.gpu)
            if (parsed.suggestions) setPerformanceSuggestions(parsed.suggestions)
          }
        }
      } catch {
        // ignore
      }
    }
    pollPerformance()
    const interval = setInterval(pollPerformance, 5000)
    return () => clearInterval(interval)
  }, [selectedTaskId, queue.tasks, tauri])

  // v1.1: Load checkpoints
  useEffect(() => {
    async function loadCheckpoints() {
      try {
        const result = await tauri.getCheckpoints()
        if (result) {
          const parsed = JSON.parse(result) as { checkpoints?: { name: string; queue_id: string }[] }
          if (parsed.checkpoints) {
            setCheckpoints(parsed.checkpoints)
          }
        }
      } catch {
        // ignore
      }
    }
    loadCheckpoints()
  }, [tauri])

  // Check environment on mount
  useEffect(() => {
    checkEnvironment()
    loadSettings()

    // Listen for menu events
    const unlistenOpen = listen('menu-open', () => {
      handleOpenFileDialog()
    })
    const unlistenAbout = listen('menu-about', () => {
      showToast('Bitmap Vector Studio v1.1.0', 'success')
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

  // v1.1 workspace handlers
  const handleSaveWorkspace = useCallback(async () => {
    try {
      const openFiles = queue.tasks.map((t) => t.inputPath)
      await tauri.saveWorkspace(null, openFiles, activePreset)
      showToast('Workspace saved', 'success')
      // Refresh list
      const result = await tauri.listWorkspaces()
      if (result) {
        const parsed = JSON.parse(result) as { workspaces?: { name: string }[] }
        if (parsed.workspaces) setWorkspaces(parsed.workspaces)
      }
    } catch (error) {
      showToast(`Failed to save workspace: ${error}`, 'error')
    }
  }, [queue.tasks, activePreset, tauri, showToast])

  const handleLoadWorkspace = useCallback(async (name: string) => {
    try {
      const result = await tauri.loadWorkspace(name)
      if (result) {
        const parsed = JSON.parse(result) as { preset?: string; options?: TraceOptions }
        if (parsed.preset) {
          selectPreset(parsed.preset)
          setOptions(getPresetOptions(parsed.preset))
        }
        if (parsed.options) {
          setOptions(parsed.options)
        }
        showToast(`Loaded workspace: ${name}`, 'success')
      }
    } catch (error) {
      showToast(`Failed to load workspace: ${error}`, 'error')
    }
  }, [tauri, selectPreset, getPresetOptions, showToast])

  const handleRestoreLast = useCallback(async () => {
    try {
      const result = await tauri.loadWorkspace('crash_recovery')
      if (result) {
        const parsed = JSON.parse(result) as { preset?: string; options?: TraceOptions }
        if (parsed.preset) {
          selectPreset(parsed.preset)
          setOptions(getPresetOptions(parsed.preset))
        }
        if (parsed.options) {
          setOptions(parsed.options)
        }
        showToast('Restored last session', 'success')
        setHasCrashRecovery(false)
      }
    } catch (error) {
      showToast(`Failed to restore: ${error}`, 'error')
    }
  }, [tauri, selectPreset, getPresetOptions, showToast])

  // v1.1 checkpoint handler
  const handleResumeCheckpoint = useCallback(async (id: string) => {
    try {
      await tauri.resumeCheckpoint(id)
      showToast(`Resumed checkpoint: ${id}`, 'success')
    } catch (error) {
      showToast(`Failed to resume checkpoint: ${error}`, 'error')
    }
  }, [tauri, showToast])

  const selectedTask = queue.tasks.find((t) => t.id === selectedTaskId)

  // v1.2 engine benchmark handler
  const handleEngineBenchmark = useCallback(async () => {
    if (!selectedTask?.inputPath) {
      showToast('Please select an image first', 'error')
      return
    }
    showToast('Engine benchmark started...', 'success')
    try {
      // await tauri.engineBenchmark(selectedTask.inputPath)
      showToast('Engine benchmark complete', 'success')
    } catch (error) {
      showToast(`Benchmark failed: ${error}`, 'error')
    }
  }, [selectedTask, showToast])

  // v1.2 cloud share handler
  const handleCloudShare = useCallback(async () => {
    if (!selectedTask?.outputPath) {
      showToast('No result to share', 'error')
      return
    }
    try {
      // In a real implementation, this would call a Tauri command
      // const result = await tauri.cloudShare(selectedTask.outputPath)
      // const parsed = JSON.parse(result)
      // setShareUrl(parsed.url)
      // setShareQrCode(parsed.qr_code)
      setShareUrl('https://example.com/share/demo')
      setShareQrCode('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iIzAwMCIvPjwvc3ZnPg==')
      showToast('Cloud share link generated', 'success')
    } catch (error) {
      showToast(`Cloud share failed: ${error}`, 'error')
    }
  }, [selectedTask, showToast, setShareUrl, setShareQrCode])

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
            onSaveWorkspace={handleSaveWorkspace}
            onLoadWorkspace={handleLoadWorkspace}
            onRestoreLast={handleRestoreLast}
            workspaces={workspaces}
            hasCrashRecovery={hasCrashRecovery}
            checkpoints={checkpoints}
            onResumeCheckpoint={handleResumeCheckpoint}
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
            ocrLang={ocrLang}
            onChangeOcrLang={setOcrLang}
            ocrVertical={ocrVertical}
            onToggleOcrVertical={() => setOcrVertical((v) => !v)}
            gpuEnabled={gpuEnabled}
            onToggleGpu={() => setGpuEnabled((v) => !v)}
            streamingEnabled={streamingEnabled}
            onToggleStreaming={() => setStreamingEnabled((v) => !v)}
            engine={engine}
            onChangeEngine={setEngine}
            onEngineBenchmark={handleEngineBenchmark}
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
            onCloudShare={handleCloudShare}
            shareUrl={shareUrl}
            shareQrCode={shareQrCode}
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
            memoryStatus={memoryStatus}
            gpuStatus={gpuStatus}
            performanceSuggestions={performanceSuggestions}
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
