// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import React from 'react'
import { useTranslation } from '@/hooks/useTranslation'
import { X, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import type { UnifiedSkill } from '@/apis/skills'
import { getSkillRefKey, SkillRef } from '../../service/skillSelectionService'

interface SelectedSkillBadgesProps {
  /** All available skills (for looking up display names) */
  skills: UnifiedSkill[]
  /** Selected skills */
  selectedSkills: SkillRef[]
  /** Callback when a skill should be removed */
  onRemove: (skill: SkillRef) => void
  /** Whether this is a Chat Shell (determines hint text) */
  isChatShell?: boolean
  /** Max skills to show before collapsing (default: 3) */
  maxVisible?: number
}

/**
 * SelectedSkillBadges Component
 *
 * Displays selected skills as removable badges above the chat input.
 * Shows a hint about what the skills will do based on shell type.
 */
export default function SelectedSkillBadges({
  skills,
  selectedSkills,
  onRemove,
  isChatShell = false,
  maxVisible = 3,
}: SelectedSkillBadgesProps) {
  const { t } = useTranslation()

  if (selectedSkills.length === 0) {
    return null
  }

  const skillMap = new Map(skills.map(skill => [skill.id, skill]))

  // Get display name for a skill
  const getDisplayName = (skill: SkillRef): string => {
    const matchedSkill =
      typeof skill.skill_id === 'number' ? skillMap.get(skill.skill_id) : undefined
    return matchedSkill?.displayName || skill.name
  }

  // Get description for a skill
  const getDescription = (skill: SkillRef): string | undefined => {
    const matchedSkill =
      typeof skill.skill_id === 'number' ? skillMap.get(skill.skill_id) : undefined
    return matchedSkill?.description
  }

  // Visible and hidden skills
  const visibleSkills = selectedSkills.slice(0, maxVisible)
  const hiddenSkills = selectedSkills.slice(maxVisible)
  const hiddenCount = hiddenSkills.length

  // Hint text based on shell type
  const hintText = isChatShell
    ? t('common:skillSelector.preload_hint')
    : t('common:skillSelector.download_hint')

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-3 py-2 border-b border-border bg-surface/50">
      <TooltipProvider>
        {/* Skill icon with hint */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center text-text-muted">
              <Zap className="h-3.5 w-3.5" />
            </div>
          </TooltipTrigger>
          <TooltipContent side="top">
            <p className="text-xs">{hintText}</p>
          </TooltipContent>
        </Tooltip>

        {/* Visible skill badges */}
        {visibleSkills.map(skill => (
          <Tooltip key={getSkillRefKey(skill)}>
            <TooltipTrigger asChild>
              <Badge
                variant="secondary"
                className="flex items-center gap-1 pl-2 pr-1 py-0.5 text-xs cursor-default hover:bg-muted"
              >
                <span className="max-w-[100px] truncate">{getDisplayName(skill)}</span>
                <button
                  type="button"
                  onClick={e => {
                    e.stopPropagation()
                    onRemove(skill)
                  }}
                  className="ml-0.5 rounded-full p-0.5 hover:bg-background/80 transition-colors"
                  aria-label={t('common:skillSelector.remove_skill')}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            </TooltipTrigger>
            {getDescription(skill) && (
              <TooltipContent side="top" className="max-w-[250px]">
                <p className="text-xs">{getDescription(skill)}</p>
              </TooltipContent>
            )}
          </Tooltip>
        ))}

        {/* Hidden skills count badge */}
        {hiddenCount > 0 && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Badge variant="info" className="text-xs cursor-default">
                +{hiddenCount}
              </Badge>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-[200px]">
              <div className="text-xs">
                {hiddenSkills.map(skill => (
                  <div key={getSkillRefKey(skill)} className="truncate">
                    {getDisplayName(skill)}
                  </div>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        )}
      </TooltipProvider>
    </div>
  )
}
