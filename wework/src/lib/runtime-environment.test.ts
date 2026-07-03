import { afterEach, describe, expect, test } from 'vitest'
import { isTauriRuntime, supportsLocalExecutorAppIpc } from './runtime-environment'

function setGlobalIsTauri(value: boolean) {
  Object.defineProperty(globalThis, 'isTauri', {
    configurable: true,
    value,
  })
}

function setTauriInternals() {
  Object.defineProperty(window, '__TAURI_INTERNALS__', {
    configurable: true,
    value: {},
  })
}

function clearTauriRuntime() {
  delete (globalThis as typeof globalThis & { isTauri?: boolean }).isTauri
  delete (window as typeof window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__
  delete (window as typeof window & { __TAURI__?: unknown }).__TAURI__
}

function setNavigatorValue<K extends keyof Navigator>(key: K, value: Navigator[K]) {
  Object.defineProperty(window.navigator, key, {
    configurable: true,
    value,
  })
}

describe('isTauriRuntime', () => {
  afterEach(() => {
    clearTauriRuntime()
  })

  test('uses the Tauri v2 runtime marker', () => {
    setGlobalIsTauri(true)

    expect(isTauriRuntime()).toBe(true)
  })

  test('keeps supporting the legacy Tauri global', () => {
    setTauriInternals()

    expect(isTauriRuntime()).toBe(true)
  })

  test('returns false in a regular browser runtime', () => {
    expect(isTauriRuntime()).toBe(false)
  })
})

describe('supportsLocalExecutorAppIpc', () => {
  afterEach(() => {
    clearTauriRuntime()
  })

  test('returns false for Windows Tauri runtime', () => {
    setTauriInternals()
    setNavigatorValue('platform', 'Win32')
    setNavigatorValue('userAgent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

    expect(supportsLocalExecutorAppIpc()).toBe(false)
  })

  test('returns true for Unix-like Tauri runtime', () => {
    setTauriInternals()
    setNavigatorValue('platform', 'MacIntel')
    setNavigatorValue('userAgent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')

    expect(supportsLocalExecutorAppIpc()).toBe(true)
  })

  test('returns false outside Tauri runtime', () => {
    setNavigatorValue('platform', 'MacIntel')
    setNavigatorValue('userAgent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')

    expect(supportsLocalExecutorAppIpc()).toBe(false)
  })
})
