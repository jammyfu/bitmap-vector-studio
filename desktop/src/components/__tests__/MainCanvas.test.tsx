import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MainCanvas from '../MainCanvas'

describe('MainCanvas', () => {
  it('renders drop zone when no image', () => {
    render(<MainCanvas originalImage={null} resultSvg={undefined} />)
    expect(screen.getByText('拖拽图片到此处')).toBeInTheDocument()
    expect(screen.getByText('或 点击上传')).toBeInTheDocument()
  })

  it('calls onClickUpload when drop zone clicked', () => {
    const mock = vi.fn()
    render(
      <MainCanvas
        originalImage={null}
        resultSvg={undefined}
        onClickUpload={mock}
      />
    )
    fireEvent.click(screen.getByText('拖拽图片到此处'))
    expect(mock).toHaveBeenCalled()
  })

  it('calls onDropFiles when files dropped', () => {
    const mock = vi.fn()
    const { container } = render(
      <MainCanvas
        originalImage={null}
        resultSvg={undefined}
        onDropFiles={mock}
      />
    )

    const dropZone = screen.getByText('拖拽图片到此处').closest('button')!
    const file = new File([], 'test.png')
    Object.defineProperty(file, 'path', { value: '/path/to/test.png' })

    const fileList = {
      length: 1,
      item: (index: number) => (index === 0 ? file : null),
      0: file,
      [Symbol.iterator]: function* () {
        for (let i = 0; i < this.length; i++) yield this[i as unknown as keyof typeof this]
      },
    } as unknown as FileList

    fireEvent.dragOver(dropZone)
    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: fileList,
      },
    })
    expect(mock).toHaveBeenCalledWith(['/path/to/test.png'])
  })

  it('renders side-by-side panels when image provided', () => {
    render(
      <MainCanvas
        originalImage="data:image/png;base64,abc"
        resultSvg="data:image/svg+xml;base64,xyz"
      />
    )
    expect(screen.getByText('原图')).toBeInTheDocument()
    expect(screen.getByText('矢量结果')).toBeInTheDocument()
  })

  it('switches to overlay mode', () => {
    render(
      <MainCanvas
        originalImage="data:image/png;base64,abc"
        resultSvg="data:image/svg+xml;base64,xyz"
      />
    )
    fireEvent.click(screen.getByText('叠加'))
    expect(screen.getByAltText('Original')).toBeInTheDocument()
    expect(screen.getByAltText('Result')).toBeInTheDocument()
  })

  it('zooms in and out', () => {
    render(
      <MainCanvas
        originalImage="data:image/png;base64,abc"
        resultSvg="data:image/svg+xml;base64,xyz"
      />
    )
    const zoomIn = screen.getByText('+').closest('button')!
    const zoomOut = screen.getByText('−').closest('button')!
    const scaleLabel = screen.getByText('100%')

    expect(scaleLabel).toBeInTheDocument()
    fireEvent.click(zoomIn)
    expect(screen.getByText('125%')).toBeInTheDocument()
    fireEvent.click(zoomOut)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('resets zoom on double click', () => {
    const { container } = render(
      <MainCanvas
        originalImage="data:image/png;base64,abc"
        resultSvg="data:image/svg+xml;base64,xyz"
      />
    )
    const zoomIn = screen.getByText('+').closest('button')!
    fireEvent.click(zoomIn)
    expect(screen.getByText('125%')).toBeInTheDocument()

    const canvas = container.firstChild as HTMLElement
    fireEvent.doubleClick(canvas)
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('shows file name in footer', () => {
    render(
      <MainCanvas
        originalImage="data:image/png;base64,abc"
        resultSvg={undefined}
        fileName="example.png"
      />
    )
    expect(screen.getByText('example.png')).toBeInTheDocument()
  })
})
