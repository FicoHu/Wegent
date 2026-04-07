// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { useSkillSelector } from '@/features/tasks/hooks/useSkillSelector'
import type { TaskDetail, Team } from '@/types/api'

const mockFetchUnifiedSkillsList = jest.fn()
const mockFetchTeamSkills = jest.fn()

jest.mock('@/apis/skills', () => ({
  fetchUnifiedSkillsList: (...args: unknown[]) => mockFetchUnifiedSkillsList(...args),
}))

jest.mock('@/apis/team', () => ({
  fetchTeamSkills: (...args: unknown[]) => mockFetchTeamSkills(...args),
}))

jest.mock('@/features/tasks/service/messageService', () => ({
  isChatShell: () => false,
}))

function createTeam(overrides: Partial<Team> = {}): Team {
  return {
    id: 1,
    name: 'team',
    description: '',
    bots: [],
    workflow: {},
    is_active: true,
    user_id: 0,
    created_at: '2026-04-07T00:00:00Z',
    updated_at: '2026-04-07T00:00:00Z',
    ...overrides,
  }
}

function HookHarness() {
  const state = useSkillSelector({ team: createTeam() })

  return (
    <div>
      <button
        data-testid="select-alpha"
        onClick={() =>
          state.toggleSkill({
            skill_id: 101,
            name: 'recday_new',
            namespace: 'skill-alpha',
            is_public: false,
          })
        }
      >
        select alpha
      </button>
      <button
        data-testid="select-beta"
        onClick={() =>
          state.toggleSkill({
            skill_id: 202,
            name: 'recday_new',
            namespace: 'skill-beta',
            is_public: false,
          })
        }
      >
        select beta
      </button>
      <div data-testid="selected-skills">{JSON.stringify(state.selectedSkills)}</div>
    </div>
  )
}

function createTaskDetail(overrides: Partial<TaskDetail> = {}): TaskDetail {
  return {
    id: 42,
    title: 'task',
    git_url: '',
    git_repo: '',
    git_repo_id: 0,
    git_domain: '',
    branch_name: '',
    prompt: 'prompt',
    status: 'COMPLETED',
    task_type: 'chat',
    progress: 100,
    batch: 0,
    result: {},
    error_message: '',
    created_at: '2026-04-07T00:00:00Z',
    updated_at: '2026-04-07T00:00:00Z',
    user: {
      id: 1,
      user_name: 'tester',
      email: 'tester@example.com',
      is_active: true,
      created_at: '2026-04-07T00:00:00Z',
      updated_at: '2026-04-07T00:00:00Z',
      git_info: [],
    },
    team: createTeam(),
    ...overrides,
  }
}

function HistoryTaskHarness({ taskDetail }: { taskDetail: TaskDetail }) {
  const state = useSkillSelector({ team: createTeam(), taskDetail })

  return <div data-testid="selected-skills">{JSON.stringify(state.selectedSkills)}</div>
}

function TeamSkillHarness() {
  const state = useSkillSelector({ team: createTeam() })

  return (
    <div>
      <button
        data-testid="toggle-team-skill"
        onClick={() =>
          state.toggleSkill({
            skill_id: 101,
            name: 'recday_new',
            namespace: 'skill-alpha',
            is_public: false,
          })
        }
      >
        toggle team skill
      </button>
      <button
        data-testid="select-user-skill"
        onClick={() =>
          state.toggleSkill({
            skill_id: 202,
            name: 'recday_extra',
            namespace: 'skill-beta',
            is_public: false,
          })
        }
      >
        select user skill
      </button>
      <button data-testid="reset-skills" onClick={() => state.resetSkills()}>
        reset skills
      </button>
      <div data-testid="selected-skills">{JSON.stringify(state.selectedSkills)}</div>
    </div>
  )
}

describe('useSkillSelector', () => {
  beforeEach(() => {
    mockFetchUnifiedSkillsList.mockResolvedValue([
      {
        id: 101,
        name: 'recday_new',
        namespace: 'skill-alpha',
        description: 'alpha',
        is_active: true,
        is_public: false,
        user_id: 1,
      },
      {
        id: 202,
        name: 'recday_new',
        namespace: 'skill-beta',
        description: 'beta',
        is_active: true,
        is_public: false,
        user_id: 1,
      },
    ])
    mockFetchTeamSkills.mockResolvedValue({
      team_id: 1,
      team_namespace: 'default',
      skills: [],
      preload_skills: [],
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('replaces the existing same-name selection with the newly chosen variant', async () => {
    render(<HookHarness />)

    await waitFor(() => {
      expect(mockFetchUnifiedSkillsList).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByTestId('select-alpha'))
    fireEvent.click(screen.getByTestId('select-beta'))

    await waitFor(() => {
      expect(screen.getByTestId('selected-skills')).toHaveTextContent('"skill_id":202')
      expect(screen.getByTestId('selected-skills')).not.toHaveTextContent('"skill_id":101')
    })
  })

  it('restores selected skills from task detail refs for history tasks', async () => {
    render(
      <HistoryTaskHarness
        taskDetail={createTaskDetail({
          requested_skill_refs: [
            {
              skill_id: 202,
              name: 'recday_new',
              namespace: 'skill-beta',
              is_public: false,
            },
          ],
        })}
      />
    )

    await waitFor(() => {
      expect(mockFetchUnifiedSkillsList).toHaveBeenCalled()
    })

    await waitFor(() => {
      expect(screen.getByTestId('selected-skills')).toHaveTextContent('"skill_id":202')
      expect(screen.getByTestId('selected-skills')).toHaveTextContent('"namespace":"skill-beta"')
    })
  })

  it('keeps team skills selected and does not clear them through toggle or reset', async () => {
    mockFetchUnifiedSkillsList.mockResolvedValue([
      {
        id: 101,
        name: 'recday_new',
        namespace: 'skill-alpha',
        description: 'alpha',
        is_active: true,
        is_public: false,
        user_id: 1,
      },
      {
        id: 202,
        name: 'recday_extra',
        namespace: 'skill-beta',
        description: 'beta',
        is_active: true,
        is_public: false,
        user_id: 1,
      },
    ])
    mockFetchTeamSkills.mockResolvedValue({
      team_id: 1,
      team_namespace: 'default',
      skills: [],
      preload_skills: [],
      skill_refs: [
        {
          skill_id: 101,
          name: 'recday_new',
          namespace: 'skill-alpha',
          is_public: false,
        },
      ],
    })

    render(<TeamSkillHarness />)

    await waitFor(() => {
      expect(screen.getByTestId('selected-skills')).toHaveTextContent('"skill_id":101')
    })

    fireEvent.click(screen.getByTestId('toggle-team-skill'))

    await waitFor(() => {
      expect(screen.getByTestId('selected-skills')).toHaveTextContent('"skill_id":101')
    })

    fireEvent.click(screen.getByTestId('select-user-skill'))

    await waitFor(() => {
      expect(screen.getByTestId('selected-skills')).toHaveTextContent('"skill_id":202')
    })

    fireEvent.click(screen.getByTestId('reset-skills'))

    await waitFor(() => {
      expect(screen.getByTestId('selected-skills')).toHaveTextContent('"skill_id":101')
      expect(screen.getByTestId('selected-skills')).not.toHaveTextContent('"skill_id":202')
    })
  })
})
