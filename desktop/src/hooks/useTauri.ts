import { useCallback } from 'react'
import { invoke } from '@tauri-apps/api/tauri'

/// Custom hook wrapping Tauri invoke calls for the Bitmap Vector Studio backend.
export function useTauri() {
  /// Convert a single image via the Python CLI.
  const convertImage = useCallback(async (inputPath: string, options: string): Promise<string> => {
    return invoke('convert_image', { inputPath, options })
  }, [])

  /// Batch convert multiple images with a preset.
  const batchConvert = useCallback(async (files: string[], preset: string): Promise<string[]> => {
    return invoke('batch_convert', { files, preset })
  }, [])

  /// Get available conversion presets.
  const getPresets = useCallback(async (): Promise<string> => {
    return invoke('get_presets')
  }, [])

  /// Save a user-defined preset.
  const savePreset = useCallback(async (name: string, options: string, description: string): Promise<void> => {
    return invoke('save_preset', { name, options, description })
  }, [])

  /// Delete a user-defined preset.
  const deletePreset = useCallback(async (name: string): Promise<void> => {
    return invoke('delete_preset', { name })
  }, [])

  /// Get conversion history.
  const getHistory = useCallback(async (limit: number): Promise<string> => {
    return invoke('get_history', { limit })
  }, [])

  /// Open a native file dialog for selecting images.
  const openFileDialog = useCallback(async (): Promise<string[]> => {
    return invoke('open_file_dialog')
  }, [])

  /// Open the output folder in the system file manager.
  const openOutputFolder = useCallback(async (path: string): Promise<void> => {
    return invoke('open_output_folder', { path })
  }, [])

  /// Start the Python API server.
  const startApi = useCallback(async (port: number): Promise<number> => {
    return invoke('start_api', { port })
  }, [])

  /// Stop the Python API server.
  const stopApi = useCallback(async (pid: number): Promise<void> => {
    return invoke('stop_api', { pid })
  }, [])

  /// Check the Python environment.
  const checkEnv = useCallback(async (): Promise<string> => {
    return invoke('check_env')
  }, [])

  /// Recommend a preset for an image.
  const recommendPreset = useCallback(async (inputPath: string): Promise<string> => {
    return invoke('recommend_preset', { inputPath })
  }, [])

  /// Open an SVG with an external editor.
  const openWithEditor = useCallback(async (svgPath: string, editor?: string): Promise<void> => {
    return invoke('open_with_editor', { svgPath, editor })
  }, [])

  /// Get installed plugins.
  const getPlugins = useCallback(async (): Promise<string> => {
    return invoke('get_plugins')
  }, [])

  /// Enable a plugin.
  const enablePlugin = useCallback(async (name: string): Promise<void> => {
    return invoke('enable_plugin', { name })
  }, [])

  /// Disable a plugin.
  const disablePlugin = useCallback(async (name: string): Promise<void> => {
    return invoke('disable_plugin', { name })
  }, [])

  /// Get application configuration.
  const getConfig = useCallback(async (): Promise<string> => {
    return invoke('get_config')
  }, [])

  /// Set a configuration value.
  const setConfig = useCallback(async (key: string, value: string): Promise<void> => {
    return invoke('set_config', { key, value })
  }, [])

  /// Get market preset list.
  const marketList = useCallback(async (): Promise<string> => {
    return invoke('market_list')
  }, [])

  /// Install a market preset.
  const marketInstall = useCallback(async (id: string, name?: string): Promise<string> => {
    return invoke('market_install', { id, name })
  }, [])

  /// Get available OCR languages.
  const getOcrLanguages = useCallback(async (): Promise<string> => {
    return invoke('get_ocr_languages')
  }, [])

  /// Detect text regions with optional language support.
  const detectTextRegionsMultilang = useCallback(async (inputPath: string, lang?: string, vertical?: boolean): Promise<string> => {
    return invoke('detect_text_regions_multilang', { inputPath, lang, vertical })
  }, [])

  /// Recognize text with optional language support.
  const recognizeTextMultilang = useCallback(async (inputPath: string, lang?: string): Promise<string> => {
    return invoke('recognize_text_multilang', { inputPath, lang })
  }, [])

  /// Get performance stats from backend.
  const getPerformanceStats = useCallback(async (inputPath: string): Promise<string> => {
    return invoke('get_performance_stats', { inputPath })
  }, [])

  /// Save workspace.
  const saveWorkspace = useCallback(async (name: string | null, openFiles: string[], preset: string): Promise<string> => {
    return invoke('save_workspace', { name, openFiles: JSON.stringify(openFiles), preset })
  }, [])

  /// Load workspace.
  const loadWorkspace = useCallback(async (name: string): Promise<string> => {
    return invoke('load_workspace', { name })
  }, [])

  /// List workspaces.
  const listWorkspaces = useCallback(async (): Promise<string> => {
    return invoke('list_workspaces')
  }, [])

  /// Get checkpoints.
  const getCheckpoints = useCallback(async (): Promise<string> => {
    return invoke('get_checkpoints')
  }, [])

  /// Resume checkpoint.
  const resumeCheckpoint = useCallback(async (checkpointId: string): Promise<string> => {
    return invoke('resume_checkpoint', { checkpointId })
  }, [])

  /// v2.0: Run AI task on image.
  const runAiTask = useCallback(async (inputPath: string, task: string, style?: string, scale?: number): Promise<string> => {
    return invoke('run_ai_task', { inputPath, task, style, scale })
  }, [])

  /// v2.0: Get engine orchestrator recommendation.
  const recommendPipeline = useCallback(async (inputPath: string): Promise<string> => {
    return invoke('recommend_pipeline', { inputPath })
  }, [])

  /// v2.0: Run recommended pipeline.
  const runPipeline = useCallback(async (inputPath: string, pipeline: string, outputPath: string): Promise<string> => {
    return invoke('run_pipeline', { inputPath, pipeline, outputPath })
  }, [])

  /// v2.0: Create collaboration room.
  const createCollabRoom = useCallback(async (): Promise<string> => {
    return invoke('create_collab_room', {})
  }, [])

  /// v2.0: Join collaboration room.
  const joinCollabRoom = useCallback(async (roomId: string): Promise<string> => {
    return invoke('join_collab_room', { roomId })
  }, [])

  /// v2.0: Generate animation from SVG.
  const generateAnimation = useCallback(async (svgPath: string, preset: string, format: string, outputPath: string): Promise<string> => {
    return invoke('generate_animation', { svgPath, preset, format, outputPath })
  }, [])

  /// v2.0: Run workflow.
  const runWorkflow = useCallback(async (template: string, inputPath: string): Promise<string> => {
    return invoke('run_workflow', { template, inputPath })
  }, [])

  /// v2.0: Sync workspaces.
  const syncWorkspaces = useCallback(async (serverUrl: string): Promise<string> => {
    return invoke('sync_workspaces', { serverUrl })
  }, [])

  /// Enable plugin hotreload.
  const enableHotreload = useCallback(async (): Promise<void> => {
    return invoke('enable_hotreload')
  }, [])

  /// Disable plugin hotreload.
  const disableHotreload = useCallback(async (): Promise<void> => {
    return invoke('disable_hotreload')
  }, [])

  return {
    convertImage,
    batchConvert,
    getPresets,
    savePreset,
    deletePreset,
    getHistory,
    openFileDialog,
    openOutputFolder,
    startApi,
    stopApi,
    checkEnv,
    recommendPreset,
    openWithEditor,
    getPlugins,
    enablePlugin,
    disablePlugin,
    getConfig,
    setConfig,
    marketList,
    marketInstall,
    getOcrLanguages,
    detectTextRegionsMultilang,
    recognizeTextMultilang,
    getPerformanceStats,
    saveWorkspace,
    loadWorkspace,
    listWorkspaces,
    getCheckpoints,
    resumeCheckpoint,
    // v2.0
    runAiTask,
    recommendPipeline,
    runPipeline,
    createCollabRoom,
    joinCollabRoom,
    generateAnimation,
    runWorkflow,
    syncWorkspaces,
    enableHotreload,
    disableHotreload,
  }
}
