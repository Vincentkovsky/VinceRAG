/// <reference types="vite/client" />
/// <reference types="vue/macros-global" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_ENABLE_STREAMING: string
  readonly VITE_ENABLE_WEB_SCRAPING: string
  readonly VITE_ENABLE_MULTIPLE_FILES: string
  readonly VITE_MAX_FILE_SIZE: string
  readonly VITE_MAX_FILES_PER_UPLOAD: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}