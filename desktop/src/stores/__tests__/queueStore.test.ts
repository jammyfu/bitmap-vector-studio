import { describe, it, expect, beforeEach } from 'vitest'
import { useQueueStore } from '../queueStore'

describe('queueStore', () => {
  beforeEach(() => {
    useQueueStore.setState({
      items: [],
      selectedId: null,
      isExpanded: true,
    })
  })

  it('adds files to queue', () => {
    useQueueStore.getState().addFiles([
      { name: 'a.png', path: '/a.png' },
      { name: 'b.png', path: '/b.png' },
    ])
    const items = useQueueStore.getState().items
    expect(items).toHaveLength(2)
    expect(items[0].fileName).toBe('a.png')
    expect(items[0].status).toBe('pending')
    expect(items[1].fileName).toBe('b.png')
  })

  it('removes an item', () => {
    useQueueStore.getState().addFiles([{ name: 'a.png', path: '/a.png' }])
    const id = useQueueStore.getState().items[0].id
    useQueueStore.getState().removeItem(id)
    expect(useQueueStore.getState().items).toHaveLength(0)
  })

  it('updates status and progress', () => {
    useQueueStore.getState().addFiles([{ name: 'a.png', path: '/a.png' }])
    const id = useQueueStore.getState().items[0].id
    useQueueStore.getState().updateStatus(id, 'converting', 50)
    const item = useQueueStore.getState().items[0]
    expect(item.status).toBe('converting')
    expect(item.progress).toBe(50)
  })

  it('sets output and marks done', () => {
    useQueueStore.getState().addFiles([{ name: 'a.png', path: '/a.png' }])
    const id = useQueueStore.getState().items[0].id
    useQueueStore.getState().setOutput(id, '/output/a.svg')
    const item = useQueueStore.getState().items[0]
    expect(item.status).toBe('done')
    expect(item.progress).toBe(100)
    expect(item.outputPath).toBe('/output/a.svg')
  })

  it('sets error status', () => {
    useQueueStore.getState().addFiles([{ name: 'a.png', path: '/a.png' }])
    const id = useQueueStore.getState().items[0].id
    useQueueStore.getState().setError(id, 'Conversion failed')
    const item = useQueueStore.getState().items[0]
    expect(item.status).toBe('error')
    expect(item.error).toBe('Conversion failed')
  })

  it('selects an item', () => {
    useQueueStore.getState().addFiles([{ name: 'a.png', path: '/a.png' }])
    const id = useQueueStore.getState().items[0].id
    useQueueStore.getState().selectItem(id)
    expect(useQueueStore.getState().selectedId).toBe(id)
  })

  it('toggles expanded', () => {
    expect(useQueueStore.getState().isExpanded).toBe(true)
    useQueueStore.getState().toggleExpanded()
    expect(useQueueStore.getState().isExpanded).toBe(false)
  })

  it('clears completed items', () => {
    useQueueStore.getState().addFiles([
      { name: 'a.png', path: '/a.png' },
      { name: 'b.png', path: '/b.png' },
    ])
    const [id1, id2] = useQueueStore.getState().items.map((i) => i.id)
    useQueueStore.getState().setOutput(id1, '/out/a.svg')
    useQueueStore.getState().clearCompleted()
    const items = useQueueStore.getState().items
    expect(items).toHaveLength(1)
    expect(items[0].id).toBe(id2)
  })

  it('reorders items', () => {
    useQueueStore.getState().addFiles([
      { name: 'a.png', path: '/a.png' },
      { name: 'b.png', path: '/b.png' },
      { name: 'c.png', path: '/c.png' },
    ])
    useQueueStore.getState().reorderItems(0, 2)
    const items = useQueueStore.getState().items
    expect(items[0].fileName).toBe('b.png')
    expect(items[1].fileName).toBe('c.png')
    expect(items[2].fileName).toBe('a.png')
  })
})
