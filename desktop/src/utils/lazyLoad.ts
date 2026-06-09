import { lazy } from 'react'

// 懒加载大型组件
export const LazyMainCanvas = lazy(() => import('@components/MainCanvas'))
export const LazyCommandPalette = lazy(() => import('@components/CommandPalette'))
export const LazyAdvancedDrawer = lazy(() => import('@components/AdvancedDrawer'))

// 预加载函数
export function preloadComponent(component: 'canvas' | 'palette' | 'advanced') {
  const map = {
    canvas: () => import('@components/MainCanvas'),
    palette: () => import('@components/CommandPalette'),
    advanced: () => import('@components/AdvancedDrawer'),
  }
  map[component]()
}
