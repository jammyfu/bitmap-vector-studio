import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAppStore } from '../appStore'

describe('appStore', () => {
  beforeEach(() => {
    useAppStore.setState({
      theme: 'system',
      toast: null,
      commandPaletteOpen: false,
      isReady: false,
      envStatus: 'Checking...',
    })
  })

  it('toggles theme', () => {
    useAppStore.getState().setTheme('dark')
    expect(useAppStore.getState().theme).toBe('dark')
  })

  it('cycles theme with toggleTheme', () => {
    useAppStore.getState().setTheme('light')
    useAppStore.getState().toggleTheme()
    expect(useAppStore.getState().theme).toBe('dark')
    useAppStore.getState().toggleTheme()
    expect(useAppStore.getState().theme).toBe('system')
    useAppStore.getState().toggleTheme()
    expect(useAppStore.getState().theme).toBe('light')
  })

  it('shows and auto-hides toast', async () => {
    vi.useFakeTimers()
    useAppStore.getState().showToast('Test message', 'success')
    expect(useAppStore.getState().toast).toEqual({ message: 'Test message', type: 'success' })

    vi.advanceTimersByTime(3500)
    expect(useAppStore.getState().toast).toBeNull()
    vi.useRealTimers()
  })

  it('hides toast immediately', () => {
    useAppStore.getState().showToast('Test message', 'error')
    expect(useAppStore.getState().toast).not.toBeNull()
    useAppStore.getState().hideToast()
    expect(useAppStore.getState().toast).toBeNull()
  })

  it('opens and closes command palette', () => {
    useAppStore.getState().openCommandPalette()
    expect(useAppStore.getState().commandPaletteOpen).toBe(true)
    useAppStore.getState().closeCommandPalette()
    expect(useAppStore.getState().commandPaletteOpen).toBe(false)
  })

  it('sets ready and env status', () => {
    useAppStore.getState().setReady(true)
    expect(useAppStore.getState().isReady).toBe(true)
    useAppStore.getState().setEnvStatus('Ready')
    expect(useAppStore.getState().envStatus).toBe('Ready')
  })
})
