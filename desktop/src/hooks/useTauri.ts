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

  /// Get conversion history.
  const getHistory = useCallback(async (): Promise<string> => {
    return invoke('get_history')
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

  return {
    convertImage,
    batchConvert,
    getPresets,
    getHistory,
    openFileDialog,
    openOutputFolder,
    startApi,
    stopApi,
    checkEnv,
  }
}
