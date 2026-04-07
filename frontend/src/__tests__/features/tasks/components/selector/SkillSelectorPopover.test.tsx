// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import SkillSelectorPopover from '@/features/tasks/components/selector/SkillSelectorPopover'

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

describe('SkillSelectorPopover', () => {
  it('does not emit duplicate key warnings for same-name skills from different namespaces', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <SkillSelectorPopover
        skills={[
          {
            id: 'exchange-calendar' as unknown as number,
            name: 'exchange-calendar',
            displayName: 'Exchange Calendar A',
            namespace: 'group-a',
            description: 'first',
            is_active: true,
            is_public: false,
            user_id: 1,
          },
          {
            id: 'exchange-calendar' as unknown as number,
            name: 'exchange-calendar',
            displayName: 'Exchange Calendar B',
            namespace: 'group-b',
            description: 'second',
            is_active: true,
            is_public: false,
            user_id: 2,
          },
        ]}
        teamSkillNames={[]}
        preloadedSkillNames={[]}
        selectedSkills={[]}
        onToggleSkill={jest.fn()}
        isChatShell={false}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'common:skillSelector.skill_button_label' }))

    await waitFor(() => {
      expect(screen.getByText('Exchange Calendar A')).toBeInTheDocument()
      expect(screen.getByText('Exchange Calendar B')).toBeInTheDocument()
    })

    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('Encountered two children with the same key')
    )

    consoleErrorSpy.mockRestore()
  })

  it('does not emit duplicate key warnings for same-name skills in the same namespace from different owners', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <SkillSelectorPopover
        skills={[
          {
            id: 'exchange-calendar' as unknown as number,
            name: 'exchange-calendar',
            displayName: 'Exchange Calendar Owner A',
            namespace: 'default',
            description: 'first',
            is_active: true,
            is_public: false,
            user_id: 1,
          },
          {
            id: 'exchange-calendar' as unknown as number,
            name: 'exchange-calendar',
            displayName: 'Exchange Calendar Owner B',
            namespace: 'default',
            description: 'second',
            is_active: true,
            is_public: false,
            user_id: 2,
          },
        ]}
        teamSkillNames={[]}
        preloadedSkillNames={[]}
        selectedSkills={[]}
        onToggleSkill={jest.fn()}
        isChatShell={false}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: 'common:skillSelector.skill_button_label' }))

    await waitFor(() => {
      expect(screen.getByText('Exchange Calendar Owner A')).toBeInTheDocument()
      expect(screen.getByText('Exchange Calendar Owner B')).toBeInTheDocument()
    })

    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('Encountered two children with the same key')
    )

    consoleErrorSpy.mockRestore()
  })
})
