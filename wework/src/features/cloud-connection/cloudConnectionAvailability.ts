import { getRuntimeConfig } from '@/config/runtime'
import { supportsLocalExecutorAppIpc } from '@/lib/runtime-environment'

export function isCloudConnectionUiAvailable(): boolean {
  return getRuntimeConfig().runtimeMode === 'local-first' && supportsLocalExecutorAppIpc()
}
