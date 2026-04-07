// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useDevices } from '@/contexts/DeviceContext'
import { useTaskContext } from '@/features/tasks/contexts/taskContext'
import { useTranslation } from '@/hooks/useTranslation'
import { isOpenClawDevice } from '@/features/devices/utils/device-status'
import { getPreferredExecutionDevice } from '@/features/devices/utils/execution-target'
import type { TaskType } from '@/types/api'

type PageExecutionTargetMode = 'public' | 'device'
type PageType = 'chat' | 'code' | 'devices'

interface UsePageExecutionTargetOptions {
  pageType: PageType
}

interface PageExecutionTargetState {
  executionMode: PageExecutionTargetMode
  selectedDeviceId: string | null
  setSelectedDeviceId: (deviceId: string | null) => void
  taskType: TaskType
  disabledReason?: string
  hideSelectors: boolean
}

export function usePageExecutionTarget({
  pageType,
}: UsePageExecutionTargetOptions): PageExecutionTargetState {
  const { t } = useTranslation()
  const searchParams = useSearchParams()
  const { devices } = useDevices()
  const { selectedTaskDetail } = useTaskContext()
  const [selectedDeviceId, setSelectedDeviceIdState] = useState<string | null>(null)
  const lastTaskIdRef = useRef<number | null | undefined>(undefined)

  const setSelectedDeviceId = useCallback((deviceId: string | null) => {
    setSelectedDeviceIdState(deviceId)
  }, [])

  useEffect(() => {
    const currentTaskId = selectedTaskDetail?.id ?? null
    if (lastTaskIdRef.current === currentTaskId) {
      return
    }

    lastTaskIdRef.current = currentTaskId

    if (selectedTaskDetail) {
      setSelectedDeviceIdState(selectedTaskDetail.device_id ?? null)
      return
    }

    if (pageType !== 'devices') {
      setSelectedDeviceIdState(null)
    }
  }, [pageType, selectedTaskDetail])

  useEffect(() => {
    if (pageType !== 'devices' || selectedTaskDetail) {
      return
    }

    const deviceIdFromUrl = searchParams.get('deviceId') || searchParams.get('device_id')
    if (deviceIdFromUrl) {
      if (devices.length === 0) {
        return
      }

      const matchedDevice = devices.find(device => device.device_id === deviceIdFromUrl)
      if (matchedDevice) {
        setSelectedDeviceIdState(deviceIdFromUrl)
      }
      return
    }

    if (selectedDeviceId) {
      return
    }

    const preferredDevice = getPreferredExecutionDevice(devices)
    if (preferredDevice) {
      setSelectedDeviceIdState(preferredDevice.device_id)
    }
  }, [devices, pageType, searchParams, selectedDeviceId, selectedTaskDetail])

  const selectedDevice = useMemo(
    () => devices.find(device => device.device_id === selectedDeviceId) ?? null,
    [devices, selectedDeviceId]
  )

  const executionMode: PageExecutionTargetMode = selectedDeviceId ? 'device' : 'public'
  const taskType: TaskType =
    executionMode === 'device' || pageType === 'devices' ? 'task' : pageType

  const disabledReason =
    selectedDeviceId && (!selectedDevice || selectedDevice.status === 'offline')
      ? t('devices:device_offline_cannot_send')
      : undefined

  return {
    executionMode,
    selectedDeviceId,
    setSelectedDeviceId,
    taskType,
    disabledReason,
    hideSelectors: Boolean(selectedDevice && isOpenClawDevice(selectedDevice)),
  }
}

export default usePageExecutionTarget
