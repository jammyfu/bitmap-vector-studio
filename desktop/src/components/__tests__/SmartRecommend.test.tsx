import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SmartRecommend from '../SmartRecommend'

describe('SmartRecommend', () => {
  it('does not render when no recommendation', () => {
    const { container } = render(<SmartRecommend />)
    expect(container.firstChild).toBeNull()
  })

  it('does not render when confidence is too low', () => {
    const { container } = render(
      <SmartRecommend recommendedPreset="photo" confidence={0.6} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders when confidence is high enough', () => {
    render(
      <SmartRecommend recommendedPreset="photo" confidence={0.85} />
    )
    expect(screen.getByText(/智能推荐：photo预设/)).toBeInTheDocument()
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('calls onApply when apply button clicked', () => {
    const mock = vi.fn()
    render(
      <SmartRecommend
        recommendedPreset="photo"
        confidence={0.85}
        onApply={mock}
      />
    )
    fireEvent.click(screen.getByText('应用推荐'))
    expect(mock).toHaveBeenCalled()
  })

  it('calls onDismiss when dismiss button clicked', () => {
    const mock = vi.fn()
    render(
      <SmartRecommend
        recommendedPreset="photo"
        confidence={0.85}
        onDismiss={mock}
      />
    )
    fireEvent.click(screen.getByText('忽略'))
    expect(mock).toHaveBeenCalled()
  })
})
