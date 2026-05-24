/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DISPATCH_API_URL: string;
  readonly VITE_PODCAST_AUTH_USERNAME?: string;
  readonly VITE_PODCAST_AUTH_PASSWORD?: string;
  readonly VITE_PODCAST_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
