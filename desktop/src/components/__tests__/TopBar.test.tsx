import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TopBar from '../TopBar'

describe('TopBar', () => {
  beforeEach(() => {
    vi.stubGlobal('navigator', {
      ...navigator,
      platform: 'Win32',
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders logo and app name', () => {
    render(
      <TopBar
        onOpenCommandPalette={() => {}}
        onOpenSettings={() => {}}
        theme="light"
        onToggleTheme={() => {}}
      />
    )
    expect(screen.getByText('Bitmap Vector Studio')).toBeInTheDocument()
  })

  it('triggers command palette on click', () => {
    const mock = vi.fn()
    render(
      <TopBar
        onOpenCommandPalette={mock}
        onOpenSettings={() => {}}
        theme="light"
        onToggleTheme={() => {}}
      />
    )
    fireEvent.click(screen.getByText(/搜索预设、命令、文件/))
    expect(mock).toHaveBeenCalled()
  })

  it('toggles theme', () => {
    const mock = vi.fn()
    render(
      <TopBar
        onOpenCommandPalette={() => {}}
        onOpenSettings={() => {}}
        theme="light"
        onToggleTheme={mock}
      />
    )
    fireEvent.click(screen.getByTitle(/切换亮色主题|切换暗色主题/))
    expect(mock).toHaveBeenCalled()
  })

  it('opens settings when settings button clicked', () => {
    const mock = vi.fn()
    render(
      <TopBar
        onOpenCommandPalette={() => {}}
        onOpenSettings={mock}
        theme="light"
        onToggleTheme={() => {}}
      />
    )
    fireEvent.click(screen.getByTitle('设置'))
    expect(mock).toHaveBeenCalled()
  })

  it('opens user menu when user button clicked', () => {
    const mock = vi.fn()
    render(
      <TopBar
        onOpenCommandPalette={() => {}}
        onOpenSettings={() => {}}
        onOpenUserMenu={mock}
        theme="light"
        onToggleTheme={() => {}}
      />
    )
    fireEvent.click(screen.getByTitle('用户'))
    expect(mock).toHaveBeenCalled()
  })
})
