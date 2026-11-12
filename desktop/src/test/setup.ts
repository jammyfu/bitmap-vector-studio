import '@testing-library/jest-dom'
import { beforeEach, vi } from 'vitest'

// jsdom does not implement matchMedia; stores subscribe during module import.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
  })),
})

beforeEach(() => {
  localStorage.removeItem('bvs_locale')
})
