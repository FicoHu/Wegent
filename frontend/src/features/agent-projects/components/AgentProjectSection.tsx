// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import {
  ChevronDown,
  ChevronRight,
  FolderPlus,
  MoreHorizontal,
  Pencil,
  Trash2,
  FolderOpen,
  Folder,
  Plus,
} from 'lucide-react'
import { useTranslation } from '@/hooks/useTranslation'
import { useAgentProjectContext } from '../contexts/agentProjectContext'
import { AgentProjectCreateDialog } from './AgentProjectCreateDialog'
import { AgentProjectEditDialog } from './AgentProjectEditDialog'
import { AgentProjectWithTasks, AgentProjectTask, Task } from '@/types/api'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { paths } from '@/config/paths'
import { useChatStreamContext } from '@/features/tasks/contexts/chatStreamContext'
import { useTaskContext } from '@/features/tasks/contexts/taskContext'

interface AgentProjectSectionProps {
  onTaskSelect?: () => void
}

export function AgentProjectSection({ onTaskSelect }: AgentProjectSectionProps) {
  const { t } = useTranslation('agent-projects')
  const router = useRouter()
  const {
    projects,
    isLoading,
    expandedProjects,
    toggleProjectExpanded,
    selectedProjectTaskId,
    setSelectedProjectTaskId,
    createTaskFromProject,
  } = useAgentProjectContext()
  const { clearAllStreams } = useChatStreamContext()
  const { setSelectedTask } = useTaskContext()

  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedProject, setSelectedProject] = useState<AgentProjectWithTasks | null>(null)
  const [sectionCollapsed, setSectionCollapsed] = useState(false)

  const handleEditProject = (project: AgentProjectWithTasks) => {
    setSelectedProject(project)
    setEditDialogOpen(true)
  }

  const handleDeleteProject = (project: AgentProjectWithTasks) => {
    setSelectedProject(project)
    setDeleteDialogOpen(true)
  }

  const handleTaskClick = useCallback(
    (projectTask: AgentProjectTask) => {
      clearAllStreams()
      setSelectedProjectTaskId(projectTask.task_id)
      setSelectedTask({
        id: projectTask.task_id,
        title: projectTask.task_title || '',
        status: projectTask.task_status,
        is_group_chat: false,
      } as Task)

      const params = new URLSearchParams()
      params.set('taskId', String(projectTask.task_id))
      router.push(`${paths.chat.getHref()}?${params.toString()}`)
      onTaskSelect?.()
    },
    [clearAllStreams, setSelectedProjectTaskId, setSelectedTask, router, onTaskSelect]
  )

  const handleNewTaskInProject = useCallback(
    async (projectId: number) => {
      const taskId = await createTaskFromProject(projectId, 'Hello', 'New Task')
      if (taskId) {
        clearAllStreams()
        setSelectedProjectTaskId(taskId)
        setSelectedTask({
          id: taskId,
          title: 'New Task',
          status: 'PENDING',
          is_group_chat: false,
        } as Task)

        const params = new URLSearchParams()
        params.set('taskId', String(taskId))
        router.push(`${paths.chat.getHref()}?${params.toString()}`)
        onTaskSelect?.()
      }
    },
    [createTaskFromProject, clearAllStreams, setSelectedProjectTaskId, setSelectedTask, router, onTaskSelect]
  )

  return (
    <div className="mb-2">
      <div className="flex items-center justify-between px-1 py-1.5 group">
        <button
          onClick={() => setSectionCollapsed(!sectionCollapsed)}
          className="flex items-center gap-1 text-xs font-medium text-text-muted hover:text-text-primary transition-colors"
        >
          {sectionCollapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
          <span>{t('section.title')}</span>
          <span className="text-text-muted ml-1">({projects.length})</span>
        </button>
        <Button
          variant="ghost"
          size="sm"
          className="p-0.5 text-text-muted hover:text-text-primary transition-colors rounded"
          onClick={() => setCreateDialogOpen(true)}
          title={t('create.title')}
        >
          <FolderPlus className="w-3.5 h-3.5" />
        </Button>
      </div>

      {!sectionCollapsed && (
        <div className="space-y-0.5">
          {isLoading ? (
            <div className="px-4 py-2 text-xs text-text-muted">{t('common:loading')}</div>
          ) : projects.length === 0 ? (
            <div className="px-4 py-2 text-xs text-text-muted">{t('section.empty')}</div>
          ) : (
            projects.map(project => (
              <AgentProjectItem
                key={project.id}
                project={project}
                isExpanded={expandedProjects.has(project.id)}
                onToggleExpand={() => toggleProjectExpanded(project.id)}
                onEdit={() => handleEditProject(project)}
                onDelete={() => handleDeleteProject(project)}
                onTaskClick={handleTaskClick}
                onNewTask={() => handleNewTaskInProject(project.id)}
                selectedProjectTaskId={selectedProjectTaskId}
              />
            ))
          )}
        </div>
      )}

      <AgentProjectCreateDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} />
      <AgentProjectEditDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        project={selectedProject}
      />
      {selectedProject && (
        <AgentProjectDeleteDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          project={selectedProject}
        />
      )}
    </div>
  )
}

interface AgentProjectItemProps {
  project: AgentProjectWithTasks
  isExpanded: boolean
  onToggleExpand: () => void
  onEdit: () => void
  onDelete: () => void
  onTaskClick: (task: AgentProjectTask) => void
  onNewTask: () => void
  selectedProjectTaskId: number | null
}

function AgentProjectItem({
  project,
  isExpanded,
  onToggleExpand,
  onEdit,
  onDelete,
  onTaskClick,
  onNewTask,
  selectedProjectTaskId,
}: AgentProjectItemProps) {
  const { t } = useTranslation('agent-projects')
  const taskCount = project.tasks?.length || 0

  return (
    <div className="group">
      <div
        className={cn(
          'flex items-center gap-1 px-2 py-1.5 rounded-md cursor-pointer',
          'hover:bg-surface transition-colors'
        )}
      >
        <button
          onClick={onToggleExpand}
          className="flex items-center justify-center w-5 h-5 text-text-secondary hover:text-text-primary"
        >
          {isExpanded ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </button>

        <div
          className="flex items-center justify-center w-5 h-5"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {isExpanded ? <FolderOpen className="w-4 h-4" /> : <Folder className="w-4 h-4" />}
        </div>

        <span className="flex-1 text-sm text-text-primary truncate" onClick={onToggleExpand}>
          {project.name}
        </span>

        <span className="text-xs text-text-muted mr-1">{taskCount}</span>

        <Button
          variant="ghost"
          size="sm"
          className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={e => {
            e.stopPropagation()
            onNewTask()
          }}
          title={t('createTask.title')}
        >
          <Plus className="w-3.5 h-3.5" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreHorizontal className="w-3.5 h-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-32">
            <DropdownMenuItem onClick={onEdit}>
              <Pencil className="w-3.5 h-3.5 mr-2" />
              {t('actions.edit')}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onDelete} className="text-destructive">
              <Trash2 className="w-3.5 h-3.5 mr-2" />
              {t('actions.delete')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {isExpanded && taskCount > 0 && (
        <div className="ml-6 space-y-0.5">
          {project.tasks?.map(projectTask => {
            const isSelected = selectedProjectTaskId === projectTask.task_id
            return (
              <div
                key={projectTask.task_id}
                onClick={() => onTaskClick(projectTask)}
                className={cn(
                  'group/task flex items-center gap-2 px-2 py-1 rounded-md cursor-pointer',
                  'text-sm transition-colors',
                  isSelected
                    ? 'bg-primary/10 text-text-primary'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface'
                )}
              >
                <span className="flex-1 truncate">
                  {projectTask.task_title || `Task #${projectTask.task_id}`}
                </span>
              </div>
            )
          })}
        </div>
      )}

      {isExpanded && taskCount === 0 && (
        <div className="ml-6 px-2 py-1 text-xs text-text-muted">{t('section.noTasks')}</div>
      )}
    </div>
  )
}

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

function AgentProjectDeleteDialog({
  open,
  onOpenChange,
  project,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: AgentProjectWithTasks
}) {
  const { t } = useTranslation('agent-projects')
  const { deleteProject } = useAgentProjectContext()
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDelete = async () => {
    setIsDeleting(true)
    await deleteProject(project.id)
    setIsDeleting(false)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('delete.title')}</DialogTitle>
          <DialogDescription>
            {t('delete.description', { name: project.name })}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isDeleting}>
            {t('common:actions.cancel')}
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
            {isDeleting ? t('common:actions.deleting') : t('common:actions.delete')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
