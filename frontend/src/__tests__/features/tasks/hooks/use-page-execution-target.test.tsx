// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'

import { usePageExecutionTarget } from '@/features/tasks/hooks/usePageExecutionTarget'

let mockDeviceIdFromUrl: string | null = null
let mockDevices: Array<{ device_id: string; status: string; bind_shell?: string }> = []
let mockSelectedTaskDetail: { id?: number; device_id?: string | null } | null = null

jest.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: (key: string) => (key === 'deviceId' || key === 'device_id' ? mockDeviceIdFromUrl : null),
  }),
}))

jest.mock('@/contexts/DeviceContext', () => ({
  useDevices: () => ({
    devices: mockDevices,
  }),
}))

jest.mock('@/features/tasks/contexts/taskContext', () => ({
  useTaskContext: () => ({
    selectedTaskDetail: mockSelectedTaskDetail,
  }),
}))

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

function HookHarness() {
  const state = usePageExecutionTarget({ pageType: 'devices' })

  return (
    <div>
      <div data-testid="selected-device-id">{state.selectedDeviceId ?? 'null'}</div>
      <div data-testid="task-type">{state.taskType}</div>
    </div>
  )
}

describe('usePageExecutionTarget', () => {
  beforeEach(() => {
    mockDeviceIdFromUrl = null
    mockDevices = []
    mockSelectedTaskDetail = null
  })

  it('initializes device pages from the URL before devices finish loading', () => {
    mockDeviceIdFromUrl = 'device-from-url'

    render(<HookHarness />)

    expect(screen.getByTestId('selected-device-id')).toHaveTextContent('device-from-url')
    expect(screen.getByTestId('task-type')).toHaveTextContent('task')
  })
})
