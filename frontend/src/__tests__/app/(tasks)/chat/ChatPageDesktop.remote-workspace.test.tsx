// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'

import { ChatPageDesktop } from '@/app/(tasks)/chat/ChatPageDesktop'

type MockChatAreaProps = Record<string, unknown>

let mockChatAreaProps: MockChatAreaProps | null = null
let mockSelectedDeviceId: string | null = null
let mockDevices = [
  {
    id: 1,
    device_id: 'device-1',
    name: 'macOS-Device',
    status: 'online',
    slot_used: 0,
    slot_max: 4,
    bind_shell: 'openclaw',
  },
]
let mockSelectedTaskDetail: Record<string, unknown> | null = {
  id: 42,
  title: 'Task 42',
  team: {
    agent_type: 'chat',
    bots: [],
  },
}

// Mock window.matchMedia for useIsDesktop hook
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query: string) => ({
    matches: query === '(min-width: 1024px)', // Simulate desktop screen
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

jest.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: () => null,
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

jest.mock('@/contexts/DeviceContext', () => ({
  useDevices: () => ({
    selectedDeviceId: mockSelectedDeviceId,
    devices: mockDevices,
  }),
}))

jest.mock('@/features/tasks/contexts/taskContext', () => ({
  useTaskContext: () => ({
    refreshTasks: jest.fn(),
    selectedTaskDetail: mockSelectedTaskDetail,
    setSelectedTask: jest.fn(),
    refreshSelectedTaskDetail: jest.fn(),
  }),
}))

jest.mock('@/features/tasks/contexts/chatStreamContext', () => ({
  useChatStreamContext: () => ({
    clearAllStreams: jest.fn(),
  }),
}))

jest.mock('@/features/tasks/hooks/useSearchShortcut', () => ({
  useSearchShortcut: () => ({
    shortcutDisplayText: 'Ctrl+K',
  }),
}))

jest.mock('@/features/tasks/components/chat', () => ({
  ChatArea: (props: MockChatAreaProps) => {
    mockChatAreaProps = props
    return <div>chat-area</div>
  },
}))

jest.mock('@/features/tasks/components/group-chat', () => ({
  CreateGroupChatDialog: () => <div>create-group-chat-dialog</div>,
}))

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

jest.mock('@/features/tasks/components/remote-workspace', () => ({
  RemoteWorkspaceEntry: ({
    taskId,
    forceDisabled,
  }: {
    taskId?: number | null
    forceDisabled?: boolean
  }) => (
    <div data-testid="remote-workspace-entry">{`${String(taskId)}:${String(!!forceDisabled)}`}</div>
  ),
}))

describe('ChatPageDesktop remote workspace integration', () => {
  beforeEach(() => {
    mockChatAreaProps = null
    mockSelectedDeviceId = null
    mockDevices = [
      {
        id: 1,
        device_id: 'device-1',
        name: 'macOS-Device',
        status: 'online',
        slot_used: 0,
        slot_max: 4,
        bind_shell: 'openclaw',
      },
    ]
    mockSelectedTaskDetail = {
      id: 42,
      title: 'Task 42',
      team: {
        agent_type: 'chat',
        bots: [],
      },
    }
  })

  test('chat desktop renders remote workspace entry in top nav when task selected', () => {
    render(<ChatPageDesktop />)

    expect(screen.getByTestId('remote-workspace-entry')).toHaveTextContent('42:false')
  })

  test('chat desktop defaults to public mode even when device context has a stale selection', () => {
    mockSelectedDeviceId = 'device-1'
    mockSelectedTaskDetail = null

    render(<ChatPageDesktop />)

    expect(mockChatAreaProps).toMatchObject({
      taskType: 'chat',
      showRepositorySelector: false,
      hideSelectors: false,
    })
  })

  test('chat desktop switches to device mode for an existing OpenClaw task', async () => {
    mockSelectedTaskDetail = {
      id: 42,
      title: 'Task 42',
      device_id: 'device-1',
      team: {
        agent_type: 'claudecode',
        bots: [],
      },
    }

    render(<ChatPageDesktop />)

    await waitFor(() => {
      expect(mockChatAreaProps).toMatchObject({
        taskType: 'task',
        showRepositorySelector: false,
        hideSelectors: true,
      })
    })
  })
})
