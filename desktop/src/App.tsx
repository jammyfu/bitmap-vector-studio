import { useEffect, useCallback, Suspense } from 'react'
import { listen } from '@tauri-apps/api/event'
import { useAppStore, useQueueStore, useConvertStore, useSettingsStore } from './stores'
import TopBar from './components/TopBar'
import CoreParams from './components/CoreParams'
import SmartRecommend from './components/SmartRecommend'
import ControlBar from './components/ControlBar'
import QueueBar from './components/QueueBar'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LazyMainCanvas, LazyCommandPalette, LazyAdvancedDrawer } from './utils/lazyLoad'
import { useTauri } from './hooks/useTauri'
import { usePresets } from './hooks/usePresets'
import { useI18n } from './i18n'
import type { TraceOptions, ConversionTask } from './types'
import './App.css'

function toQueueTasks(items: ReturnType<typeof useQueueStore.getState>['items']): ConversionTask[] {
  return items.map((item) => ({
    id: item.id,
    fileName: item.fileName,
    inputPath: item.filePath,
    outputPath: item.outputPath || '',
    status: item.status === 'converting' ? 'running' : item.status === 'done' ? 'completed' : item.status === 'error' ? 'failed' : 'pending',
    progress: item.progress,
    preset: 'default',
    error: item.error,
  }))
}

function buildTraceOptions(state: ReturnType<typeof useConvertStore.getState>): TraceOptions {
  return {
    colormode: state.colormode,
    hierarchical: 'stacked',
    mode: state.mode,
    filter_speckle: state.filterSpeckle,
    color_precision: state.colorPrecision,
    layer_difference: state.layerDifference,
    corner_threshold: state.cornerThreshold,
    length_threshold: state.lengthThreshold,
    max_iterations: state.maxIterations,
    splice_threshold: state.spliceThreshold,
    path_precision: state.pathPrecision,
    denoise: state.denoise,
    posterize: state.posterize,
    max_input_side: state.maxInputSide,
  }
}

function App() {
  const { showToast, openCommandPalette, closeCommandPalette, commandPaletteOpen, effectiveTheme, toggleTheme } = useAppStore()
  const { items, addFiles, selectedId, isExpanded, toggleExpanded, removeItem, clearCompleted } = useQueueStore()
  const convert = useConvertStore()
  const { loadSettings } = useSettingsStore()
  const tauri = useTauri()
  const { presets, getPresetOptions, selectPreset } = usePresets()
  const { t } = useI18n()

  const selectedItem = items.find((i: typeof items[0]) => i.id === selectedId)
  const originalImage = selectedItem?.filePath || null
  const queueTasks = toQueueTasks(items)
  const traceOptions = buildTraceOptions(convert)

  useEffect(() => {
    checkEnvironment()
    loadSettings()
    const unlistenOpen = listen('menu-open', () => handleOpenFileDialog())
    const unlistenAbout = listen('menu-about', () => showToast('Bitmap Vector Studio v3.0.0', 'success'))
    return () => { unlistenOpen.then((f) => f()); unlistenAbout.then((f) => f()) }
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openCommandPalette() }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'o') { e.preventDefault(); handleOpenFileDialog() }
      if (e.key === 'Escape') closeCommandPalette()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const handleDropFiles = useCallback((files: string[]) => {
    const fileList = files.map((f) => ({ name: f.split(/[/\\]/).pop() || f, path: f }))
    addFiles(fileList)
    showToast(t('toast.files_added', '已添加 {count} 个文件').replace('{count}', String(fileList.length)), 'success')
    if (fileList.length > 0) analyzeAndRecommend(fileList[0].path)
  }, [addFiles, showToast, t])

  async function analyzeAndRecommend(filePath: string) {
    try {
      const result = await tauri.recommendPreset(filePath)
      if (result) {
        const parsed = JSON.parse(result)
        convert.setRecommendation(parsed.preset, parsed.confidence || 0.8)
      }
    } catch { /* ignore */ }
  }

  async function checkEnvironment() {
    try {
      const result = await tauri.checkEnv()
      if (!result.includes('ready') && !result.includes('OK')) showToast(t('toast.env_check', '环境检测: {result}').replace('{result}', result), 'warning')
    } catch (error) { showToast(t('toast.env_error', '环境错误: {error}').replace('{error}', String(error)), 'error') }
  }

  async function handleOpenFileDialog() {
    try {
      const files = await tauri.openFileDialog()
      if (files.length > 0) {
        const fileList = files.map((f) => ({ name: f.split(/[/\\]/).pop() || f, path: f }))
        addFiles(fileList)
        showToast(t('toast.files_added', '已添加 {count} 个文件').replace('{count}', String(files.length)), 'success')
        if (fileList.length > 0) analyzeAndRecommend(fileList[0].path)
      }
    } catch { /* ignore */ }
  }

  async function handleConvert() {
    if (!selectedItem) { showToast(t('toast.no_file'), 'warning'); return }
    convert.startConvert()
    try {
      const options = getPresetOptions(convert.preset)
      const result = await tauri.convertImage(selectedItem.filePath, JSON.stringify({ ...options, colormode: convert.colormode, mode: convert.mode }))
      if (result) {
        const parsed = JSON.parse(result)
        convert.setPreviewResult(parsed.svgPath)
        convert.finishConvert(parsed.svgPath)
        showToast(t('toast.convert_success'), 'success')
      }
    } catch (error) {
      showToast(t('toast.convert_error', '转换失败: {error}').replace('{error}', String(error)), 'error')
      convert.finishConvert('')
    }
  }

  const handleDownload = useCallback((format: 'svg' | 'pdf' | 'png') => {
    if (!convert.previewResult) return
    showToast(t('toast.download_started', '下载 {format} 已开始').replace('{format}', format.toUpperCase()), 'success')
  }, [convert.previewResult, showToast, t])

  const handleSelectPreset = useCallback((name: string) => { convert.setPreset(name); selectPreset(name) }, [convert.setPreset, selectPreset])

  const handleChangeAdvancedOptions = useCallback((opts: TraceOptions) => {
    useConvertStore.setState({
      filterSpeckle: opts.filter_speckle, colorPrecision: opts.color_precision, layerDifference: opts.layer_difference,
      cornerThreshold: opts.corner_threshold, lengthThreshold: opts.length_threshold, maxIterations: opts.max_iterations,
      spliceThreshold: opts.splice_threshold, pathPrecision: opts.path_precision, denoise: opts.denoise,
      posterize: opts.posterize, maxInputSide: opts.max_input_side,
    })
  }, [])

  return (
    <div className="app-container">
      <TopBar onOpenCommandPalette={openCommandPalette} onOpenSettings={() => showToast(t('toast.settings_coming'), 'warning')} theme={effectiveTheme} onToggleTheme={toggleTheme} />
      <div className="app-body">
        <ErrorBoundary>
          <Suspense fallback={<div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b6b6b' }}>{t('app.loading_canvas')}</div>}>
            <LazyMainCanvas originalImage={originalImage} resultSvg={convert.previewResult} onDropFiles={handleDropFiles} onClickUpload={handleOpenFileDialog} fileName={selectedItem?.fileName} />
          </Suspense>
        </ErrorBoundary>
        <div className="app-controls">
          <ErrorBoundary fallback={<div style={{ padding: 16, color: 'var(--error)', textAlign: 'center' }}>{t('app.param_panel_error')}</div>}>
            <CoreParams preset={convert.preset} onChangePreset={handleSelectPreset} presets={presets} colorMode={convert.colormode} onChangeColorMode={(m) => convert.setCoreParam('colormode', m)} curveMode={convert.mode} onChangeCurveMode={(m) => convert.setCoreParam('mode', m)} optimizeLevel={convert.optimizeLevel} onChangeOptimizeLevel={(l) => convert.setCoreParam('optimizeLevel', l)} />
          </ErrorBoundary>
          <SmartRecommend recommendedPreset={convert.recommendedPreset || undefined} confidence={convert.recommendationConfidence} onApply={convert.applyRecommendation} onDismiss={() => convert.setRecommendation('', 0)} />
          <Suspense fallback={null}>
            <LazyAdvancedDrawer options={traceOptions} onChangeOptions={handleChangeAdvancedOptions} defaultOptions={getPresetOptions('default')} />
          </Suspense>
        </div>
        <ControlBar onConvert={handleConvert} onDownload={handleDownload} isConverting={convert.isConverting} canDownload={!!convert.previewResult} />
      </div>
      <QueueBar tasks={queueTasks} isExpanded={isExpanded} onToggleExpand={toggleExpanded} onRemoveTask={removeItem} onClearCompleted={clearCompleted} />
      <Suspense fallback={null}>
        <LazyCommandPalette open={commandPaletteOpen} onClose={closeCommandPalette} presets={presets} onSelectPreset={handleSelectPreset} onOpenCommand={(cmd) => { if (cmd === 'cmd-open') handleOpenFileDialog(); if (cmd === 'cmd-convert') handleConvert() }} />
      </Suspense>
    </div>
  )
}

export default App
