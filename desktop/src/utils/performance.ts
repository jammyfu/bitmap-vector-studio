// 测量组件渲染时间
export function measureRender<T extends (...args: any[]) => any>(
  name: string,
  fn: T
): T {
  return ((...args) => {
    const start = performance.now()
    const result = fn(...args)
    const end = performance.now()
    console.log(`[Performance] ${name}: ${(end - start).toFixed(2)}ms`)
    return result
  }) as T
}

// 防抖
export function debounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number
): T {
  let timer: ReturnType<typeof setTimeout>
  return ((...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }) as T
}

// 节流
export function throttle<T extends (...args: any[]) => void>(
  fn: T,
  limit: number
): T {
  let inThrottle = false
  return ((...args) => {
    if (!inThrottle) {
      fn(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }) as T
}
