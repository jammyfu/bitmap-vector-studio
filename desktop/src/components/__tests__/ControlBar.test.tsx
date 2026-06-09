import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ControlBar from '../ControlBar'

describe('ControlBar', () => {
  it('renders convert button in idle state', () => {
    render(
      <ControlBar
        isConverting={false}
        canDownload={false}
        onConvert={() => {}}
        onDownload={() => {}}
      />
    )
    expect(screen.getByText('开始转换')).toBeInTheDocument()
  })

  it('renders convert button in converting state', () => {
    render(
      <ControlBar
        isConverting={true}
        canDownload={false}
        onConvert={() => {}}
        onDownload={() => {}}
      />
    )
    expect(screen.getByText('转换中...')).toBeInTheDocument()
  })

  it('disables convert button while converting', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={true}
        canDownload={false}
        onConvert={mock}
        onDownload={() => {}}
      />
    )
    fireEvent.click(screen.getByText('转换中...'))
    expect(mock).not.toHaveBeenCalled()
  })

  it('triggers onConvert when clicked in idle state', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={false}
        canDownload={false}
        onConvert={mock}
        onDownload={() => {}}
      />
    )
    fireEvent.click(screen.getByText('开始转换'))
    expect(mock).toHaveBeenCalled()
  })

  it('enables download button when canDownload is true', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={false}
        canDownload={true}
        onConvert={() => {}}
        onDownload={mock}
        downloadFormat="svg"
      />
    )
    fireEvent.click(screen.getByText(/下载 SVG/))
    expect(mock).toHaveBeenCalledWith('svg')
  })

  it('disables download button when canDownload is false', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={false}
        canDownload={false}
        onConvert={() => {}}
        onDownload={mock}
        downloadFormat="svg"
      />
    )
    fireEvent.click(screen.getByText(/下载 SVG/))
    expect(mock).not.toHaveBeenCalled()
  })

  it('opens format menu and downloads selected format', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={false}
        canDownload={true}
        onConvert={() => {}}
        onDownload={mock}
        downloadFormat="svg"
      />
    )
    fireEvent.click(screen.getByText('▼'))
    fireEvent.click(screen.getByText('PDF'))
    expect(mock).toHaveBeenCalledWith('pdf')
  })

  it('calls onAddToQueue when add button clicked', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={false}
        canDownload={false}
        onConvert={() => {}}
        onDownload={() => {}}
        onAddToQueue={mock}
      />
    )
    fireEvent.click(screen.getByText('添加到队列'))
    expect(mock).toHaveBeenCalled()
  })

  it('calls onOpenExternal when external editor clicked', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={false}
        canDownload={true}
        onConvert={() => {}}
        onDownload={() => {}}
        onOpenExternal={mock}
      />
    )
    fireEvent.click(screen.getByText('外部编辑器'))
    expect(mock).toHaveBeenCalled()
  })

  it('disables external editor when canDownload is false', () => {
    const mock = vi.fn()
    render(
      <ControlBar
        isConverting={false}
        canDownload={false}
        onConvert={() => {}}
        onDownload={() => {}}
        onOpenExternal={mock}
      />
    )
    fireEvent.click(screen.getByText('外部编辑器'))
    expect(mock).not.toHaveBeenCalled()
  })
})
