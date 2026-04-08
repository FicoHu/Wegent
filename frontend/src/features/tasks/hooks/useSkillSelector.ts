// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { fetchUnifiedSkillsList, UnifiedSkill } from '@/apis/skills'
import { fetchTeamSkills, TeamSkillsResponse } from '@/apis/team'
import type { TaskDetail, Team } from '@/types/api'
import { isChatShell } from '../service/messageService'
import { isSameSkillRef, SkillRef, toSkillRef } from '../service/skillSelectionService'

interface UseSkillSelectorOptions {
  /** Selected team for the current chat */
  team: Team | null
  /** Selected task detail for history-task skill restoration */
  taskDetail?: TaskDetail | null
  /** Whether skills feature is enabled */
  enabled?: boolean
}

interface UseSkillSelectorReturn {
  /** All available skills (from unified API) */
  availableSkills: UnifiedSkill[]
  /** Team's configured skill names */
  teamSkillNames: string[]
  /** Team's preloaded skill names (auto-injected, to filter out for Chat Shell) */
  preloadedSkillNames: string[]
  /** Team's configured skills with precise refs */
  teamSkills: SkillRef[]
  /** Team's preloaded skills with precise refs */
  preloadedSkills: SkillRef[]
  /** Currently selected skill names */
  selectedSkillNames: string[]
  /** Currently selected skills with full info (name, namespace, is_public) */
  selectedSkills: SkillRef[]
  /** Add a skill to selection */
  addSkill: (skill: SkillRef) => void
  /** Remove a skill from selection */
  removeSkill: (skill: SkillRef) => void
  /** Toggle a skill (add if not selected, remove if selected) */
  toggleSkill: (skill: SkillRef) => void
  /** Reset all selected skills */
  resetSkills: () => void
  /** Whether the current team is a Chat Shell type */
  isChatShellType: boolean
  /** Loading state */
  isLoading: boolean
  /** Error state */
  error: Error | null
}

/**
 * Hook for managing skill selection in chat interface.
 *
 * Fetches available skills from the unified API and team-specific skills,
 * and manages the selection state for user-chosen skills.
 *
 * The hook handles different Shell types:
 * - Chat Shell: Uses preload_skill_names (prompts injected into system message)
 * - Other Shells (ClaudeCode, Agno): Uses additional_skill_names (downloaded to executor)
 */
export function useSkillSelector({
  team,
  taskDetail = null,
  enabled = true,
}: UseSkillSelectorOptions): UseSkillSelectorReturn {
  // State for available skills from unified API
  const [availableSkills, setAvailableSkills] = useState<UnifiedSkill[]>([])
  // State for team-specific skills (from backend)
  const [teamSkillsData, setTeamSkillsData] = useState<TeamSkillsResponse | null>(null)
  // User-selected skills
  const [selectedSkills, setSelectedSkills] = useState<SkillRef[]>([])
  // Loading and error states
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  // Determine if current team is Chat Shell type
  const isChatShellType = useMemo(() => isChatShell(team), [team])

  // Team's configured skill names (from team skills API)
  const teamSkillNames = useMemo(() => {
    return Array.from(
      new Set(
        (teamSkillsData?.skill_refs ?? teamSkillsData?.skills ?? []).map(skill =>
          typeof skill === 'string' ? skill : skill.name
        )
      )
    )
  }, [teamSkillsData])

  // Team's preloaded skill names (auto-injected into system prompt)
  const preloadedSkillNames = useMemo(() => {
    return Array.from(
      new Set(
        (teamSkillsData?.preload_skill_refs ?? teamSkillsData?.preload_skills ?? []).map(skill =>
          typeof skill === 'string' ? skill : skill.name
        )
      )
    )
  }, [teamSkillsData])

  const teamSkills = useMemo<SkillRef[]>(() => {
    if (teamSkillsData?.skill_refs?.length) {
      return teamSkillsData.skill_refs
    }

    return (teamSkillsData?.skills ?? [])
      .map(name => availableSkills.find(skill => skill.name === name))
      .filter((skill): skill is UnifiedSkill => !!skill)
      .map(skill => toSkillRef(skill))
  }, [availableSkills, teamSkillsData])

  const preloadedSkills = useMemo<SkillRef[]>(() => {
    if (teamSkillsData?.preload_skill_refs?.length) {
      return teamSkillsData.preload_skill_refs
    }

    return (teamSkillsData?.preload_skills ?? [])
      .map(name => availableSkills.find(skill => skill.name === name))
      .filter((skill): skill is UnifiedSkill => !!skill)
      .map(skill => toSkillRef(skill))
  }, [availableSkills, teamSkillsData])

  const restoredTaskSkills = useMemo<SkillRef[]>(() => {
    if (!taskDetail) {
      return []
    }

    if (taskDetail.requested_skill_refs?.length) {
      return taskDetail.requested_skill_refs.map(skill => ({
        skill_id: skill.skill_id,
        name: skill.name,
        namespace: skill.namespace,
        is_public: skill.is_public,
      }))
    }

    if (!taskDetail.additional_skill_names?.length) {
      return []
    }

    return taskDetail.additional_skill_names
      .map(name => availableSkills.find(skill => skill.name === name))
      .filter((skill): skill is UnifiedSkill => !!skill)
      .map(skill => toSkillRef(skill))
  }, [availableSkills, taskDetail])

  // Fetch available skills when enabled
  useEffect(() => {
    if (!enabled) {
      setAvailableSkills([])
      return
    }

    const fetchSkills = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const skills = await fetchUnifiedSkillsList({ scope: 'all' })
        setAvailableSkills(skills)
      } catch (err) {
        console.error('[useSkillSelector] Failed to fetch skills:', err)
        setError(err instanceof Error ? err : new Error('Failed to fetch skills'))
      } finally {
        setIsLoading(false)
      }
    }

    fetchSkills()
  }, [enabled])

  // Fetch team-specific skills when team ID changes
  useEffect(() => {
    if (!enabled || !team?.id) {
      setTeamSkillsData(null)
      return
    }

    const fetchTeamSkillsData = async () => {
      try {
        const skills = await fetchTeamSkills(team.id)
        setTeamSkillsData(skills)
      } catch (err) {
        console.warn('[useSkillSelector] Failed to fetch team skills:', err)
        // Don't set error for team skills - it's optional
      }
    }

    fetchTeamSkillsData()
  }, [enabled, team?.id])

  // Reset selected skills when team changes
  useEffect(() => {
    if (taskDetail?.id) {
      return
    }
    setSelectedSkills([])
  }, [team?.id, taskDetail?.id])

  // Restore selected skills when viewing an existing task from history.
  useEffect(() => {
    if (!taskDetail?.id) {
      return
    }

    setSelectedSkills(restoredTaskSkills)
  }, [restoredTaskSkills, taskDetail?.id])

  // Skill management callbacks
  const addSkill = useCallback((skill: SkillRef) => {
    setSelectedSkills(prev => {
      if (prev.some(selected => isSameSkillRef(selected, skill))) {
        return prev
      }

      // Only allow one selected variant per skill name.
      return [...prev.filter(selected => selected.name !== skill.name), skill]
    })
  }, [])

  const removeSkill = useCallback((skill: SkillRef) => {
    setSelectedSkills(prev => prev.filter(selected => !isSameSkillRef(selected, skill)))
  }, [])

  const toggleSkill = useCallback((skill: SkillRef) => {
    setSelectedSkills(prev => {
      if (prev.some(selected => isSameSkillRef(selected, skill))) {
        return prev.filter(selected => !isSameSkillRef(selected, skill))
      }

      return [...prev.filter(selected => selected.name !== skill.name), skill]
    })
  }, [])

  const resetSkills = useCallback(() => {
    setSelectedSkills([])
  }, [])

  const normalizedSelectedSkills = useMemo<SkillRef[]>(() => {
    const availableSkillMap = new Map(availableSkills.map(skill => [skill.id, skill]))

    return selectedSkills.map(skill => {
      if (typeof skill.skill_id === 'number') {
        const availableSkill = availableSkillMap.get(skill.skill_id)
        if (availableSkill) {
          return toSkillRef(availableSkill)
        }
      }

      return skill
    })
  }, [availableSkills, selectedSkills])

  const selectedSkillNames = useMemo(
    () => normalizedSelectedSkills.map(skill => skill.name),
    [normalizedSelectedSkills]
  )

  return {
    availableSkills,
    teamSkillNames,
    preloadedSkillNames,
    teamSkills,
    preloadedSkills,
    selectedSkillNames,
    selectedSkills: normalizedSelectedSkills,
    addSkill,
    removeSkill,
    toggleSkill,
    resetSkills,
    isChatShellType,
    isLoading,
    error,
  }
}
export type { UseSkillSelectorReturn, SkillRef }
