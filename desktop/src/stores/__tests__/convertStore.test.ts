import { describe, it, expect, beforeEach } from 'vitest'
import { useConvertStore } from '../convertStore'

describe('convertStore', () => {
  beforeEach(() => {
    useConvertStore.getState().resetToDefaults()
  })

  it('sets preset', () => {
    useConvertStore.getState().setPreset('photo')
    expect(useConvertStore.getState().preset).toBe('photo')
  })

  it('sets core params', () => {
    useConvertStore.getState().setCoreParam('colormode', 'binary')
    expect(useConvertStore.getState().colormode).toBe('binary')

    useConvertStore.getState().setCoreParam('mode', 'polygon')
    expect(useConvertStore.getState().mode).toBe('polygon')

    useConvertStore.getState().setCoreParam('optimizeLevel', 'comprehensive')
    expect(useConvertStore.getState().optimizeLevel).toBe('comprehensive')

    useConvertStore.getState().setCoreParam('outputFormat', 'pdf')
    expect(useConvertStore.getState().outputFormat).toBe('pdf')
  })

  it('ignores invalid core params', () => {
    const before = useConvertStore.getState().colormode
    useConvertStore.getState().setCoreParam('colormode', 'invalid')
    expect(useConvertStore.getState().colormode).toBe(before)
  })

  it('toggles advanced panel', () => {
    expect(useConvertStore.getState().advancedOpen).toBe(false)
    useConvertStore.getState().toggleAdvanced()
    expect(useConvertStore.getState().advancedOpen).toBe(true)
  })

  it('sets advanced params', () => {
    useConvertStore.getState().setAdvancedParam('filterSpeckle', 8)
    expect(useConvertStore.getState().filterSpeckle).toBe(8)

    useConvertStore.getState().setAdvancedParam('denoise', true)
    expect(useConvertStore.getState().denoise).toBe(true)

    useConvertStore.getState().setAdvancedParam('aiOcr', true)
    expect(useConvertStore.getState().aiOcr).toBe(true)
  })

  it('ignores unknown advanced params', () => {
    const before = useConvertStore.getState().filterSpeckle
    useConvertStore.getState().setAdvancedParam('unknownKey', 999)
    expect(useConvertStore.getState().filterSpeckle).toBe(before)
  })

  it('starts and finishes conversion', () => {
    useConvertStore.getState().startConvert()
    expect(useConvertStore.getState().isConverting).toBe(true)
    expect(useConvertStore.getState().previewResult).toBeUndefined()

    useConvertStore.getState().finishConvert('<svg></svg>')
    expect(useConvertStore.getState().isConverting).toBe(false)
    expect(useConvertStore.getState().previewResult).toBe('<svg></svg>')
  })

  it('sets preview result', () => {
    useConvertStore.getState().setPreviewResult('result')
    expect(useConvertStore.getState().previewResult).toBe('result')
  })

  it('sets recommendation and applies it', () => {
    useConvertStore.getState().setRecommendation('photo', 0.9)
    expect(useConvertStore.getState().recommendedPreset).toBe('photo')
    expect(useConvertStore.getState().recommendationConfidence).toBe(0.9)

    useConvertStore.getState().applyRecommendation()
    expect(useConvertStore.getState().preset).toBe('photo')
    expect(useConvertStore.getState().recommendedPreset).toBeNull()
    expect(useConvertStore.getState().recommendationConfidence).toBe(0)
  })

  it('resets to defaults', () => {
    useConvertStore.getState().setPreset('photo')
    useConvertStore.getState().setCoreParam('colormode', 'binary')
    useConvertStore.getState().setAdvancedParam('filterSpeckle', 99)
    useConvertStore.getState().resetToDefaults()
    expect(useConvertStore.getState().preset).toBe('default')
    expect(useConvertStore.getState().colormode).toBe('color')
    expect(useConvertStore.getState().filterSpeckle).toBe(4)
  })
})
