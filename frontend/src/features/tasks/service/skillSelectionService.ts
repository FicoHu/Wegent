// SPDX-FileCopyrightText: 2026 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import type { UnifiedSkill } from '@/apis/skills'

export interface SkillRef {
  skill_id?: number
  name: string
  namespace: string
  is_public: boolean
}

export function toSkillRef(
  skill: Pick<UnifiedSkill, 'id' | 'name' | 'namespace' | 'is_public'>
): SkillRef {
  return {
    skill_id: skill.id,
    name: skill.name,
    namespace: skill.namespace,
    is_public: skill.is_public,
  }
}

export function getSkillRefKey(skill: SkillRef): string {
  if (typeof skill.skill_id === 'number') {
    return `id:${skill.skill_id}`
  }

  const namespace = skill.namespace || 'default'
  return `ref:${skill.name}:${namespace}:${skill.is_public ? 'public' : 'private'}`
}

export function getUnifiedSkillKey(
  skill: Pick<UnifiedSkill, 'id' | 'name' | 'namespace' | 'is_public' | 'user_id'>
): string {
  if (typeof skill.id === 'number' || (typeof skill.id === 'string' && /^\d+$/.test(skill.id))) {
    return `id:${String(skill.id)}`
  }

  const namespace = skill.namespace || 'default'
  const owner = typeof skill.user_id === 'number' ? String(skill.user_id) : 'unknown-owner'

  return `skill:${skill.name}:${namespace}:${owner}:${skill.is_public ? 'public' : 'private'}`
}

export function isSameSkillRef(left: SkillRef, right: SkillRef): boolean {
  if (typeof left.skill_id === 'number' && typeof right.skill_id === 'number') {
    return left.skill_id === right.skill_id
  }

  return (
    left.name === right.name &&
    left.namespace === right.namespace &&
    left.is_public === right.is_public
  )
}
