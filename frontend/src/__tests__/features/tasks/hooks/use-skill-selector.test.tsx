// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import { useSkillSelector } from '@/features/tasks/hooks/useSkillSelector'
import type { Team } from '@/types/api'

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
})
