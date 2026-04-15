// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import '@testing-library/jest-dom'
import { fireEvent, render, screen } from '@testing-library/react'

import PublicSkillList from '@/features/admin/components/PublicSkillList'
import SetupSkillStep from '@/features/admin/components/SetupSkillStep'
import {
  deletePublicSkill,
  downloadPublicSkill,
  fetchPublicSkillsList,
  getPublicSkillContent,
  importGitRepoPublicSkills,
  scanGitRepoPublicSkills,
  updatePublicSkillWithUpload,
  uploadPublicSkill,
} from '@/apis/skills'

const translations: Record<string, string> = {
  'admin:public_skills.title': 'Public Skills',
  'admin:public_skills.description': 'Manage public skills',
  'admin:public_skills.no_skills': 'No public skills found',
  'admin:public_skills.upload_skill': 'Upload Skill',
  'admin:setup_wizard.skill_step.title': 'Skills',
  'admin:setup_wizard.skill_step.description': 'Configure skills',
  'admin:setup_wizard.skill_step.no_skills': 'No skills yet',
  'admin:setup_wizard.skill_step.file_requirements': 'Upload a ZIP package',
  'admin:setup_wizard.skill_step.add_skill': 'Add Skill',
  'admin:setup_wizard.skill_step.add_skill_description': 'Add a public skill',
  'admin:setup_wizard.skill_step.upload_tab': 'Upload',
  'admin:setup_wizard.skill_step.git_import_tab': 'Import from Git',
  'admin:setup_wizard.skill_step.skill_name': 'Skill Name',
  'admin:setup_wizard.skill_step.skill_name_placeholder': 'Enter skill name',
  'admin:setup_wizard.skill_step.skill_name_hint': 'Skill name hint',
  'admin:setup_wizard.skill_step.zip_package': 'ZIP Package',
  'admin:setup_wizard.skill_step.drag_drop_hint': 'Drop your ZIP file here',
  'admin:setup_wizard.skill_step.max_file_size': 'Maximum file size: 10MB',
  'admin:common.cancel': 'Cancel',
  'common:skills.admin_only_label': 'Admin Only Visibility',
  'common:skills.admin_only_description': 'Only admins can see this skill',
}

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: (namespace?: string) => ({
    t: (key: string) => {
      const resolvedKey = key.includes(':') ? key : `${namespace}:${key}`
      return translations[resolvedKey] ?? key
    },
  }),
}))

jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}))

jest.mock('@/apis/skills', () => ({
  fetchPublicSkillsList: jest.fn(),
  uploadPublicSkill: jest.fn(),
  updatePublicSkillWithUpload: jest.fn(),
  deletePublicSkill: jest.fn(),
  downloadPublicSkill: jest.fn(),
  getPublicSkillContent: jest.fn(),
  scanGitRepoPublicSkills: jest.fn(),
  importGitRepoPublicSkills: jest.fn(),
}))

describe('admin skill visibility i18n', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(fetchPublicSkillsList as jest.Mock).mockResolvedValue([])
    ;(uploadPublicSkill as jest.Mock).mockResolvedValue({})
    ;(updatePublicSkillWithUpload as jest.Mock).mockResolvedValue({})
    ;(deletePublicSkill as jest.Mock).mockResolvedValue(undefined)
    ;(downloadPublicSkill as jest.Mock).mockResolvedValue(undefined)
    ;(getPublicSkillContent as jest.Mock).mockResolvedValue({ content: '' })
    ;(scanGitRepoPublicSkills as jest.Mock).mockResolvedValue({ skills: [] })
    ;(importGitRepoPublicSkills as jest.Mock).mockResolvedValue({
      success: [],
      skipped: [],
      failed: [],
      total_success: 0,
      total_skipped: 0,
      total_failed: 0,
    })
  })

  it('renders the admin-only copy in PublicSkillList upload dialog', async () => {
    render(<PublicSkillList />)

    expect(await screen.findByText('Upload Skill')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Upload Skill' }))

    expect(await screen.findByText('Admin Only Visibility')).toBeInTheDocument()
    expect(screen.getByText('Only admins can see this skill')).toBeInTheDocument()
  })

  it('renders the admin-only copy in SetupSkillStep upload dialog', async () => {
    render(<SetupSkillStep />)

    expect(await screen.findByText('Add Skill')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Add Skill' }))

    expect(await screen.findByText('Admin Only Visibility')).toBeInTheDocument()
    expect(screen.getByText('Only admins can see this skill')).toBeInTheDocument()
  })
})
