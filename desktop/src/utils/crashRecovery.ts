export const RECOVERY_KEY = 'bvs_crash_recovery'

export interface RecoveryData {
  timestamp: number
  queueItems: any[]
  convertState: any
  settings: any
}

export function saveRecoveryState(data: RecoveryData) {
  try {
    localStorage.setItem(RECOVERY_KEY, JSON.stringify(data))
  } catch { /* ignore */ }
}

export function loadRecoveryState(): RecoveryData | null {
  try {
    const raw = localStorage.getItem(RECOVERY_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearRecoveryState() {
  localStorage.removeItem(RECOVERY_KEY)
}

export function hasRecoveryState(): boolean {
  return !!loadRecoveryState()
}
