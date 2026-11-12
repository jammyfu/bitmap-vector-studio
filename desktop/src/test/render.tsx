import type { ReactElement } from 'react'
import { render as renderComponent, type RenderOptions } from '@testing-library/react'
import { I18nProvider } from '../i18n'

export * from '@testing-library/react'

// Match the application root rather than rendering untranslated context keys.
export function render(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return renderComponent(ui, { wrapper: I18nProvider, ...options })
}
