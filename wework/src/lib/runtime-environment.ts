import { isTauri as isTauriApiRuntime } from '@tauri-apps/api/core'

function hasTauriGlobal(): boolean {
  return typeof window !== 'undefined' && ('__TAURI_INTERNALS__' in window || '__TAURI__' in window)
}

export function isTauriRuntime(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  return isTauriApiRuntime() || hasTauriGlobal()
}

function isWindowsRuntime(): boolean {
  if (typeof navigator === 'undefined') {
    return false
  }

  const platform = navigator.platform || ''
  const userAgent = navigator.userAgent || ''
  return platform.startsWith('Win') || /Windows/i.test(userAgent)
}

export function supportsLocalExecutorAppIpc(): boolean {
  return isTauriRuntime() && !isWindowsRuntime()
}
