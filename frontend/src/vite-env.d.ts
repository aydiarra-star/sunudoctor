/// <reference types="vite/client" />
declare const __HASH_ROUTER__: boolean;

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
