// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import '@testing-library/jest-dom'
import { act, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'

import { CodePageDesktop } from '@/app/(tasks)/code/CodePageDesktop'

type MockChatAreaProps = Record<string, unknown>

let mockChatAreaProps: MockChatAreaProps | null = null
let mockSelectedDeviceId: string | null = null
let mockDevices = [
  {
    id: 1,
    device_id: 'device-1',
    name: 'macOS-OpenClaw',
    status: 'online',
    slot_used: 0,
    slot_max: 4,
    bind_shell: 'openclaw',
  },
]
let mockSearchTaskId: string | null = '84'
let mockSelectedTaskDetail: Record<string, unknown> | null = {
  id: 84,
  title: 'Task 84',
  status: 'RUNNING',
}

jest.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: (key: string) => (key === 'taskId' ? mockSearchTaskId : null),
  }),
}))

jest.mock('@/features/tasks/service/teamService', () => ({
  teamService: {
    useTeams: () => ({
      teams: [],
      isTeamsLoading: false,
      refreshTeams: jest.fn().mockResolvedValue([]),
    }),
  },
}))

jest.mock('@/features/layout/TopNavigation', () => ({
  __esModule: true,
  default: ({ children }: { children?: ReactNode }) => (
    <div>
      <div>top-navigation</div>
      <div>{children}</div>
    </div>
  ),
}))

jest.mock('@/features/tasks/components/sidebar', () => ({
  TaskSidebar: () => <div>task-sidebar</div>,
  ResizableSidebar: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  CollapsedSidebarButtons: () => <div>collapsed-sidebar-buttons</div>,
  SearchDialog: () => <div>search-dialog</div>,
}))

jest.mock('@/features/layout/WorkbenchToggle', () => ({
  __esModule: true,
  default: () => <div>workbench-toggle</div>,
}))

jest.mock('@/features/tasks/components/input', () => ({
  OpenMenu: () => <div>open-menu</div>,
}))

jest.mock('@/features/layout/GithubStarButton', () => ({
  GithubStarButton: () => <div>github-star</div>,
}))
jest.mock('@/features/common/UserContext', () => ({
  useUser: () => ({ user: null }),
}))

jest.mock('@/contexts/TeamContext', () => ({
  useTeamContext: () => ({
    teams: [],
    isTeamsLoading: false,
    refreshTeams: jest.fn().mockResolvedValue([]),
    addTeam: jest.fn(),
  }),
}))

jest.mock('@/features/tasks/contexts/taskContext', () => ({
  useTaskContext: () => ({
    selectedTaskDetail: mockSelectedTaskDetail,
    setSelectedTask: jest.fn(),
    refreshTasks: jest.fn(),
    refreshSelectedTaskDetail: jest.fn(),
  }),
}))

jest.mock('@/contexts/DeviceContext', () => ({
  useDevices: () => ({
    selectedDeviceId: mockSelectedDeviceId,
    devices: mockDevices,
  }),
}))

jest.mock('@/features/tasks/contexts/chatStreamContext', () => ({
  useChatStreamContext: () => ({
    clearAllStreams: jest.fn(),
  }),
}))

jest.mock('@/features/tasks/hooks/useTaskStateMachine', () => ({
  useTaskStateMachine: () => ({
    state: null,
  }),
}))

jest.mock('@/utils/openLinks', () => ({
  calculateOpenLinks: () => [],
}))

jest.mock('@/features/tasks/hooks/useSearchShortcut', () => ({
  useSearchShortcut: () => ({
    shortcutDisplayText: 'Ctrl+K',
  }),
}))

jest.mock('@/features/tasks/components', () => ({
  Workbench: () => <div>workbench</div>,
}))

jest.mock('@/features/tasks/components/chat', () => ({
  ChatArea: (props: MockChatAreaProps) => {
    mockChatAreaProps = props
    return <div>chat-area</div>
  },
}))

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

jest.mock('@/features/tasks/components/remote-workspace', () => ({
  RemoteWorkspaceEntry: ({ taskId }: { taskId?: number | null }) => (
    <div data-testid="remote-workspace-entry">{String(taskId)}</div>
  ),
}))

describe('CodePageDesktop remote workspace integration', () => {
  beforeEach(() => {
    mockChatAreaProps = null
    mockSelectedDeviceId = null
    mockSearchTaskId = '84'
    mockDevices = [
      {
        id: 1,
        device_id: 'device-1',
        name: 'macOS-OpenClaw',
        status: 'online',
        slot_used: 0,
        slot_max: 4,
        bind_shell: 'openclaw',
      },
    ]
    mockSelectedTaskDetail = { id: 84, title: 'Task 84', status: 'RUNNING' }
  })

  test('code desktop renders remote workspace entry in top nav when task selected', () => {
    render(<CodePageDesktop />)

    expect(screen.getByTestId('remote-workspace-entry')).toHaveTextContent('84')
  })

  test('code desktop defaults to public mode even when device context has a stale selection', () => {
    mockSelectedDeviceId = 'device-1'
    mockSearchTaskId = null
    mockSelectedTaskDetail = null

    render(<CodePageDesktop />)

    expect(mockChatAreaProps).toMatchObject({
      taskType: 'code',
      showRepositorySelector: true,
      hideSelectors: false,
    })
  })

  test('code desktop matches device-page behavior for existing OpenClaw tasks', async () => {
    mockSelectedTaskDetail = {
      id: 84,
      title: 'Task 84',
      status: 'RUNNING',
      device_id: 'device-1',
    }

    render(<CodePageDesktop />)

    await waitFor(() => {
      expect(mockChatAreaProps).toMatchObject({
        taskType: 'task',
        showRepositorySelector: false,
        hideSelectors: true,
      })
    })
  })

  test('code desktop hides repository selector after selecting a device in-page', async () => {
    mockSearchTaskId = null
    mockSelectedTaskDetail = null
    mockDevices = [
      {
        id: 1,
        device_id: 'device-1',
        name: 'macOS-Device',
        status: 'online',
        slot_used: 0,
        slot_max: 4,
        bind_shell: 'claudecode',
      },
    ]

    render(<CodePageDesktop />)

    expect(mockChatAreaProps).toMatchObject({
      taskType: 'code',
      showRepositorySelector: true,
      hideSelectors: false,
    })

    await act(async () => {
      ;(mockChatAreaProps?.onSelectedDeviceIdChange as (deviceId: string | null) => void)?.(
        'device-1'
      )
    })

    await waitFor(() => {
      expect(mockChatAreaProps).toMatchObject({
        taskType: 'task',
        showRepositorySelector: false,
        hideSelectors: false,
      })
    })
  })
})
