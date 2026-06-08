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
  }
}
