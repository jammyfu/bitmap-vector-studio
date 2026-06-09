import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@components': resolve(__dirname, './src/components'),
      '@stores': resolve(__dirname, './src/stores'),
      '@hooks': resolve(__dirname, './src/hooks'),
      '@types': resolve(__dirname, './src/types'),
      '@styles': resolve(__dirname, './src/styles'),
    },
  },
  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent vite from obscuring rust error messages
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    hmr: {
      overlay: false, // 禁用全屏错误遮罩
    },
    watch: {
      // 3. tell vite to ignore watching `src-tauri`
      ignored: ['**/src-tauri/**'],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    // 代码分割
    rollupOptions: {
      output: {
        manualChunks: {
          // React核心
          'react-vendor': ['react', 'react-dom'],
          // Tauri API
          'tauri-vendor': ['@tauri-apps/api'],
          // 大型组件懒加载
          'canvas': ['./src/components/MainCanvas'],
          'palette': ['./src/components/CommandPalette'],
        },
      },
    },
    // 压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    // 资源内联阈值
    assetsInlineLimit: 4096,
    // chunk大小警告
    chunkSizeWarningLimit: 500,
  },
  // 预构建
  optimizeDeps: {
    include: ['react', 'react-dom', '@tauri-apps/api'],
  },
})
