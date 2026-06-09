import { createContext, useContext, useState, useCallback } from 'react'

export type Locale = 'zh-CN' | 'en-US' | 'ja-JP'

interface I18nContextValue {
  locale: Locale
  setLocale: (l: Locale) => void
  t: (key: string, fallback?: string) => string
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'zh-CN',
  setLocale: () => {},
  t: (key, fallback) => fallback || key,
})

export function useI18n() {
  return useContext(I18nContext)
}

// 翻译字典
const translations: Record<Locale, Record<string, string>> = {
  'zh-CN': {
    'app.title': 'Bitmap Vector Studio',
    'app.subtitle': '位图转矢量工具',
    'app.loading_canvas': '画布加载中...',
    'app.param_panel_error': '参数面板加载失败',
    'topbar.search': '搜索预设、命令、文件...',
    'topbar.theme_light': '切换亮色主题',
    'topbar.theme_dark': '切换暗色主题',
    'topbar.settings': '设置',
    'topbar.user': '用户',
    'topbar.language': '语言',
    'canvas.drop': '拖拽图片到此处',
    'canvas.upload': '或 点击上传',
    'canvas.original': '原图',
    'canvas.result': '矢量结果',
    'canvas.side_by_side': '并排',
    'canvas.overlay': '叠加',
    'canvas.empty': '无内容',
    'canvas.no_original': '无原图',
    'canvas.no_result': '无结果',
    'params.preset': '预设',
    'params.colormode': '颜色模式',
    'params.curvemode': '曲线模式',
    'params.optimize': '优化',
    'params.color': '彩色',
    'params.binary': '黑白',
    'params.spline': '样条',
    'params.polygon': '多边形',
    'params.pixel': '像素',
    'params.none': '无',
    'params.no_optimize': '无优化',
    'params.basic': '基础',
    'params.comprehensive': '全面',
    'params.aggressive': '激进',
    'control.convert': '开始转换',
    'control.converting': '转换中...',
    'control.download': '下载',
    'control.external_editor': '外部编辑器',
    'control.share': '分享',
    'control.add_to_queue': '添加到队列',
    'queue.title': '文件队列',
    'queue.empty': '暂无文件',
    'queue.pending_files': '{count}个文件待处理',
    'queue.completed_files': '{count}个文件已完成',
    'queue.drag_hint': '暂无文件，拖拽图片到画布添加',
    'queue.filename': '文件名',
    'queue.status': '状态',
    'queue.progress': '进度',
    'queue.action': '操作',
    'queue.clear_completed': '清空已完成',
    'queue.start_all': '全部开始',
    'recommend.title': '智能推荐',
    'recommend.apply': '应用推荐',
    'recommend.dismiss': '忽略',
    'recommend.confidence': '置信度',
    'advanced.title': '高级参数',
    'toast.convert_success': '转换完成！',
    'toast.convert_error': '转换失败: {error}',
    'toast.no_file': '请先选择或上传图片',
    'toast.files_added': '已添加 {count} 个文件',
    'toast.settings_coming': '设置面板即将上线',
    'toast.env_check': '环境检测: {result}',
    'toast.env_error': '环境错误: {error}',
    'toast.download_started': '下载 {format} 已开始',
  },
  'en-US': {
    'app.title': 'Bitmap Vector Studio',
    'app.subtitle': 'Bitmap to Vector Converter',
    'app.loading_canvas': 'Loading canvas...',
    'app.param_panel_error': 'Parameter panel failed to load',
    'topbar.search': 'Search presets, commands, files...',
    'topbar.theme_light': 'Switch to light theme',
    'topbar.theme_dark': 'Switch to dark theme',
    'topbar.settings': 'Settings',
    'topbar.user': 'User',
    'topbar.language': 'Language',
    'canvas.drop': 'Drop image here',
    'canvas.upload': 'or click to upload',
    'canvas.original': 'Original',
    'canvas.result': 'Vector Result',
    'canvas.side_by_side': 'Side by side',
    'canvas.overlay': 'Overlay',
    'canvas.empty': 'Empty',
    'canvas.no_original': 'No original',
    'canvas.no_result': 'No result',
    'params.preset': 'Preset',
    'params.colormode': 'Color Mode',
    'params.curvemode': 'Curve Mode',
    'params.optimize': 'Optimize',
    'params.color': 'Color',
    'params.binary': 'Binary',
    'params.spline': 'Spline',
    'params.polygon': 'Polygon',
    'params.pixel': 'Pixel',
    'params.none': 'None',
    'params.no_optimize': 'None',
    'params.basic': 'Basic',
    'params.comprehensive': 'Comprehensive',
    'params.aggressive': 'Aggressive',
    'control.convert': 'Convert',
    'control.converting': 'Converting...',
    'control.download': 'Download',
    'control.external_editor': 'External Editor',
    'control.share': 'Share',
    'control.add_to_queue': 'Add to Queue',
    'queue.title': 'File Queue',
    'queue.empty': 'No files',
    'queue.pending_files': '{count} files pending',
    'queue.completed_files': '{count} files completed',
    'queue.drag_hint': 'No files, drag images to the canvas to add',
    'queue.filename': 'Filename',
    'queue.status': 'Status',
    'queue.progress': 'Progress',
    'queue.action': 'Action',
    'queue.clear_completed': 'Clear Completed',
    'queue.start_all': 'Start All',
    'recommend.title': 'Smart Recommend',
    'recommend.apply': 'Apply',
    'recommend.dismiss': 'Dismiss',
    'recommend.confidence': 'confidence',
    'advanced.title': 'Advanced',
    'toast.convert_success': 'Conversion complete!',
    'toast.convert_error': 'Conversion failed: {error}',
    'toast.no_file': 'Please select or upload an image first',
    'toast.files_added': 'Added {count} files',
    'toast.settings_coming': 'Settings panel coming soon',
    'toast.env_check': 'Environment check: {result}',
    'toast.env_error': 'Environment error: {error}',
    'toast.download_started': 'Download {format} started',
  },
  'ja-JP': {
    'app.title': 'Bitmap Vector Studio',
    'app.subtitle': 'ビットマップからベクトル変換',
    'app.loading_canvas': 'キャンバス読み込み中...',
    'app.param_panel_error': 'パラメータパネルの読み込みに失敗しました',
    'topbar.search': 'プリセット、コマンド、ファイルを検索...',
    'topbar.theme_light': 'ライトテーマに切り替え',
    'topbar.theme_dark': 'ダークテーマに切り替え',
    'topbar.settings': '設定',
    'topbar.user': 'ユーザー',
    'topbar.language': '言語',
    'canvas.drop': '画像をここにドロップ',
    'canvas.upload': 'またはクリックしてアップロード',
    'canvas.original': '元画像',
    'canvas.result': 'ベクトル結果',
    'canvas.side_by_side': '並べて表示',
    'canvas.overlay': 'オーバーレイ',
    'canvas.empty': '空',
    'canvas.no_original': '元画像なし',
    'canvas.no_result': '結果なし',
    'params.preset': 'プリセット',
    'params.colormode': 'カラーモード',
    'params.curvemode': '曲線モード',
    'params.optimize': '最適化',
    'params.color': 'カラー',
    'params.binary': '白黒',
    'params.spline': 'スプライン',
    'params.polygon': 'ポリゴン',
    'params.pixel': 'ピクセル',
    'params.none': 'なし',
    'params.no_optimize': 'なし',
    'params.basic': '基本',
    'params.comprehensive': '包括的',
    'params.aggressive': '積極的',
    'control.convert': '変換開始',
    'control.converting': '変換中...',
    'control.download': 'ダウンロード',
    'control.external_editor': '外部エディタ',
    'control.share': '共有',
    'control.add_to_queue': 'キューに追加',
    'queue.title': 'ファイルキュー',
    'queue.empty': 'ファイルなし',
    'queue.pending_files': '{count} ファイル待ち',
    'queue.completed_files': '{count} ファイル完了',
    'queue.drag_hint': 'ファイルがありません。画像をキャンバスにドラッグしてください',
    'queue.filename': 'ファイル名',
    'queue.status': '状態',
    'queue.progress': '進捗',
    'queue.action': '操作',
    'queue.clear_completed': '完了をクリア',
    'queue.start_all': 'すべて開始',
    'recommend.title': 'スマート推薦',
    'recommend.apply': '適用',
    'recommend.dismiss': '無視',
    'recommend.confidence': '信頼度',
    'advanced.title': '詳細設定',
    'toast.convert_success': '変換完了！',
    'toast.convert_error': '変換失敗: {error}',
    'toast.no_file': '画像を選択またはアップロードしてください',
    'toast.files_added': '{count} ファイルを追加しました',
    'toast.settings_coming': '設定パネルは近日公開予定です',
    'toast.env_check': '環境チェック: {result}',
    'toast.env_error': '環境エラー: {error}',
    'toast.download_started': '{format} のダウンロードを開始しました',
  },
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    try {
      const stored = localStorage.getItem('bvs_locale') as Locale
      if (stored && translations[stored]) return stored
      return 'zh-CN'
    } catch {
      return 'zh-CN'
    }
  })

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
    try {
      localStorage.setItem('bvs_locale', l)
    } catch { /* ignore */ }
  }, [])

  const t = useCallback((key: string, fallback?: string) => {
    return translations[locale][key] || fallback || key
  }, [locale])

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  )
}
