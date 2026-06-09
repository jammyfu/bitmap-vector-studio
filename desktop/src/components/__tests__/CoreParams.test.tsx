import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CoreParams from '../CoreParams'
import type { Preset } from '../../types'

const mockPresets: Preset[] = [
  { name: 'default', displayName: '默认', description: '', options: {} as any, isBuiltin: true },
  { name: 'photo', displayName: '照片', description: '', options: {} as any, isBuiltin: false },
]

describe('CoreParams', () => {
  it('renders four select fields', () => {
    render(
      <CoreParams
        preset="default"
        onChangePreset={() => {}}
        presets={mockPresets}
        colorMode="color"
        onChangeColorMode={() => {}}
        curveMode="spline"
        onChangeCurveMode={() => {}}
        optimizeLevel="basic"
        onChangeOptimizeLevel={() => {}}
      />
    )
    const selects = screen.getAllByRole('combobox')
    expect(selects).toHaveLength(4)
    expect(screen.getByText('预设')).toBeInTheDocument()
    expect(screen.getByText('颜色模式')).toBeInTheDocument()
    expect(screen.getByText('曲线模式')).toBeInTheDocument()
    expect(screen.getByText('优化')).toBeInTheDocument()
  })

  it('calls onChangePreset when preset changed', () => {
    const mock = vi.fn()
    render(
      <CoreParams
        preset="default"
        onChangePreset={mock}
        presets={mockPresets}
        colorMode="color"
        onChangeColorMode={() => {}}
        curveMode="spline"
        onChangeCurveMode={() => {}}
        optimizeLevel="basic"
        onChangeOptimizeLevel={() => {}}
      />
    )
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'photo' } })
    expect(mock).toHaveBeenCalledWith('photo')
  })

  it('calls onChangeColorMode when color mode changed', () => {
    const mock = vi.fn()
    render(
      <CoreParams
        preset="default"
        onChangePreset={() => {}}
        presets={mockPresets}
        colorMode="color"
        onChangeColorMode={mock}
        curveMode="spline"
        onChangeCurveMode={() => {}}
        optimizeLevel="basic"
        onChangeOptimizeLevel={() => {}}
      />
    )
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[1], { target: { value: 'binary' } })
    expect(mock).toHaveBeenCalledWith('binary')
  })

  it('calls onChangeCurveMode when curve mode changed', () => {
    const mock = vi.fn()
    render(
      <CoreParams
        preset="default"
        onChangePreset={() => {}}
        presets={mockPresets}
        colorMode="color"
        onChangeColorMode={() => {}}
        curveMode="spline"
        onChangeCurveMode={mock}
        optimizeLevel="basic"
        onChangeOptimizeLevel={() => {}}
      />
    )
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[2], { target: { value: 'polygon' } })
    expect(mock).toHaveBeenCalledWith('polygon')
  })

  it('calls onChangeOptimizeLevel when optimize level changed', () => {
    const mock = vi.fn()
    render(
      <CoreParams
        preset="default"
        onChangePreset={() => {}}
        presets={mockPresets}
        colorMode="color"
        onChangeColorMode={() => {}}
        curveMode="spline"
        onChangeCurveMode={() => {}}
        optimizeLevel="basic"
        onChangeOptimizeLevel={mock}
      />
    )
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[3], { target: { value: 'comprehensive' } })
    expect(mock).toHaveBeenCalledWith('comprehensive')
  })
})
