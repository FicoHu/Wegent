// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import React, { createContext, useContext, useState, useCallback, useMemo } from 'react'
import { AgentProjectWithTasks, AgentProjectTask } from '@/types/api'
import { agentProjectApis } from '@/apis/agent-projects'
import { useToast } from '@/hooks/use-toast'
import { useTranslation } from '@/hooks/useTranslation'

interface AgentProjectContextValue {
  projects: AgentProjectWithTasks[]
  isLoading: boolean
  error: string | null
  refreshProjects: () => Promise<void>
  createProject: (data: {
    name: string
    description?: string
    environment_type: string
    team_ref: { name: string; namespace: string; user_id: number }
    directory_path?: string
    git_url?: string
    git_repo?: string
    git_branch?: string
    device_id?: string
  }) => Promise<AgentProjectWithTasks | null>
  updateProject: (
    id: number,
    data: {
      name?: string
      description?: string
      environment_type?: string
      team_ref?: { name: string; namespace: string; user_id: number }
      directory_path?: string
      git_url?: string
      git_repo?: string
      git_branch?: string
      device_id?: string
    }
  ) => Promise<AgentProjectWithTasks | null>
  deleteProject: (id: number) => Promise<boolean>
  createTaskFromProject: (projectId: number, prompt: string, title?: string) => Promise<number | null>
  toggleProjectExpanded: (projectId: number) => void
  expandedProjects: Set<number>
  selectedProjectTaskId: number | null
  setSelectedProjectTaskId: (taskId: number | null) => void
  projectTaskIds: Set<number>
}

const AgentProjectContext = createContext<AgentProjectContextValue | undefined>(undefined)

export function AgentProjectProvider({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation('agent-projects')
  const { toast } = useToast()

  const [projects, setProjects] = useState<AgentProjectWithTasks[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedProjects, setExpandedProjects] = useState<Set<number>>(new Set())
  const [selectedProjectTaskId, setSelectedProjectTaskId] = useState<number | null>(null)

  const projectTaskIds = useMemo(() => {
    const ids = new Set<number>()
    projects.forEach(project => {
      project.tasks?.forEach(task => {
        ids.add(task.task_id)
      })
    })
    return ids
  }, [projects])

  const refreshProjects = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await agentProjectApis.getAgentProjects()
      setProjects(response.items)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load projects'
      setError(message)
      console.error('[AgentProjectContext] Failed to load projects:', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const createProject = useCallback(
    async (data: Parameters<AgentProjectContextValue['createProject']>[0]) => {
      try {
        const newProject = await agentProjectApis.createAgentProject(data)
        await refreshProjects()
        toast({
          title: t('toast.createSuccess'),
          description: t('toast.createSuccessDesc', { name: newProject.name }),
        })
        return newProject
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create project'
        toast({ title: t('toast.createFailed'), description: message, variant: 'destructive' })
        return null
      }
    },
    [refreshProjects, toast, t]
  )

  const updateProject = useCallback(
    async (id: number, data: Parameters<AgentProjectContextValue['updateProject']>[1]) => {
      try {
        const updated = await agentProjectApis.updateAgentProject(id, data)
        setProjects(prev => prev.map(p => (p.id === id ? updated : p)))
        toast({ title: t('toast.updateSuccess') })
        return updated
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update project'
        toast({ title: t('toast.updateFailed'), description: message, variant: 'destructive' })
        return null
      }
    },
    [toast, t]
  )

  const deleteProject = useCallback(
    async (id: number) => {
      try {
        await agentProjectApis.deleteAgentProject(id)
        setProjects(prev => prev.filter(p => p.id !== id))
        toast({ title: t('toast.deleteSuccess') })
        return true
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete project'
        toast({ title: t('toast.deleteFailed'), description: message, variant: 'destructive' })
        return false
      }
    },
    [toast, t]
  )

  const createTaskFromProject = useCallback(
    async (projectId: number, prompt: string, title?: string) => {
      try {
        const result = await agentProjectApis.createTaskFromProject(projectId, { prompt, title })
        await refreshProjects()
        return result.task_id
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create task'
        toast({ title: t('toast.createTaskFailed'), description: message, variant: 'destructive' })
        return null
      }
    },
    [refreshProjects, toast, t]
  )

  const toggleProjectExpanded = useCallback((projectId: number) => {
    setExpandedProjects(prev => {
      const next = new Set(prev)
      if (next.has(projectId)) {
        next.delete(projectId)
      } else {
        next.add(projectId)
      }
      return next
    })
  }, [])

  const value: AgentProjectContextValue = {
    projects,
    isLoading,
    error,
    refreshProjects,
    createProject,
    updateProject,
    deleteProject,
    createTaskFromProject,
    toggleProjectExpanded,
    expandedProjects,
    selectedProjectTaskId,
    setSelectedProjectTaskId,
    projectTaskIds,
  }

  return <AgentProjectContext.Provider value={value}>{children}</AgentProjectContext.Provider>
}

export function useAgentProjectContext() {
  const context = useContext(AgentProjectContext)
  if (context === undefined) {
    throw new Error('useAgentProjectContext must be used within an AgentProjectProvider')
  }
  return context
}
