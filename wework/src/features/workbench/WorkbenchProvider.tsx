import { useCallback, useEffect, useMemo, useReducer } from 'react'
import type { ReactNode } from 'react'
import { createHttpClient } from '@/api/http'
import { createModelApi } from '@/api/models'
import { createProjectApi } from '@/api/projects'
import { createSkillApi } from '@/api/skills'
import { createTaskApi } from '@/api/tasks'
import { createTeamApi } from '@/api/teams'
import { getRuntimeConfig } from '@/config/runtime'
import { createChatStream } from '@/stream/chatStream'
import { createSocketClient } from '@/stream/socketClient'
import type {
  Attachment,
  ChatSendPayload,
  SkillRef,
  Subtask,
  Task,
  UnifiedModel,
  UnifiedSkill,
  User,
} from '@/types/api'
import type { WorkbenchMessage, WorkbenchState } from '@/types/workbench'
import { useWorkbenchAttachments } from './useWorkbenchAttachments'
import { useWorkbenchModels } from './useWorkbenchModels'
import { useWorkbenchSkills } from './useWorkbenchSkills'
import { messageReducer } from './messageReducer'
import {
  initialWorkbenchState,
  workbenchReducer,
} from './workbenchReducer'
import { WorkbenchContext } from './useWorkbench'

export interface WorkbenchServices {
  teamApi: ReturnType<typeof createTeamApi>
  modelApi: ReturnType<typeof createModelApi>
  skillApi: ReturnType<typeof createSkillApi>
  projectApi: ReturnType<typeof createProjectApi>
  taskApi: ReturnType<typeof createTaskApi>
  chatStream: ReturnType<typeof createChatStream>
}

export interface WorkbenchContextValue {
  state: WorkbenchState
  messages: WorkbenchMessage[]
  projectChat: {
    models: UnifiedModel[]
    skills: UnifiedSkill[]
    selectedModel: UnifiedModel | null
    selectedSkills: SkillRef[]
    attachments: Attachment[]
    uploadingFiles: Map<string, { file: File; progress: number }>
    errors: Map<string, string>
    isOptionsLocked: boolean
    isAttachmentReadyToSend: boolean
    setSelectedModel: (model: UnifiedModel | null) => void
    setSelectedSkills: (skills: SkillRef[]) => void
    toggleSkill: (skill: SkillRef) => void
    handleFileSelect: (files: File | File[]) => Promise<void>
    addExistingAttachment: (attachment: Attachment) => void
    removeAttachment: (attachmentId: number) => Promise<void>
    resetAttachments: () => void
  }
  selectProject: (projectId: number) => void
  openTask: (taskId: number) => Promise<void>
  setInput: (input: string) => void
  sendCurrentInput: () => Promise<void>
}

interface WorkbenchProviderProps {
  children: ReactNode
  user: User
  services?: WorkbenchServices
}

function createDefaultServices(): WorkbenchServices {
  const { apiBaseUrl } = getRuntimeConfig()
  const client = createHttpClient({ baseUrl: apiBaseUrl })
  const socket = createSocketClient()

  return {
    teamApi: createTeamApi(client),
    modelApi: createModelApi(client),
    skillApi: createSkillApi(client),
    projectApi: createProjectApi(client),
    taskApi: createTaskApi(client),
    chatStream: createChatStream(socket),
  }
}

function subtaskToMessage(subtask: Subtask): WorkbenchMessage {
  const result = subtask.result as { value?: string } | undefined
  return {
    id: `subtask-${subtask.id}`,
    subtaskId: subtask.id,
    role: subtask.role === 'user' ? 'user' : 'assistant',
    content: subtask.prompt || result?.value || '',
    status: subtask.status === 'FAILED' ? 'failed' : 'done',
    createdAt: subtask.created_at,
  }
}

export function WorkbenchProvider({
  children,
  user,
  services,
}: WorkbenchProviderProps) {
  const resolvedServices = useMemo(
    () => services ?? createDefaultServices(),
    [services]
  )
  const [state, dispatch] = useReducer(
    workbenchReducer,
    initialWorkbenchState
  )
  const [messages, dispatchMessages] = useReducer(messageReducer, [])
  const isOptionsLocked = Boolean(state.currentTask)
  const modelSelection = useWorkbenchModels({
    api: resolvedServices.modelApi,
    locked: isOptionsLocked,
  })
  const skillSelection = useWorkbenchSkills({
    api: resolvedServices.skillApi,
    teamId: state.defaultTeam?.id,
    locked: isOptionsLocked,
  })
  const attachmentSelection = useWorkbenchAttachments()

  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      try {
        const [defaultTeam, projects, recentTasks] = await Promise.all([
          resolvedServices.teamApi.getDefaultWorkbenchTeam(),
          resolvedServices.projectApi.listProjects(),
          resolvedServices.taskApi.listRecentTasks({ limit: 20 }),
        ])

        if (!cancelled) {
          dispatch({
            type: 'bootstrapped',
            user,
            defaultTeam,
            projects: projects.items,
            recentTasks: recentTasks.items,
          })
        }
      } catch (error) {
        if (!cancelled) {
          dispatch({
            type: 'bootstrap_failed',
            error: error instanceof Error ? error.message : '初始化失败',
          })
        }
      }
    }

    bootstrap()
    return () => {
      cancelled = true
    }
  }, [resolvedServices, user])

  useEffect(() => {
    return resolvedServices.chatStream.subscribe({
      onChatStart: payload =>
        dispatchMessages({
          type: 'assistant_started',
          taskId: payload.task_id,
          subtaskId: payload.subtask_id,
        }),
      onChatChunk: payload =>
        dispatchMessages({
          type: 'assistant_chunk',
          subtaskId: payload.subtask_id,
          content: payload.content,
        }),
      onChatDone: payload =>
        dispatchMessages({
          type: 'assistant_done',
          subtaskId: payload.subtask_id,
          content:
            typeof payload.result.value === 'string'
              ? payload.result.value
              : undefined,
        }),
      onChatError: payload =>
        dispatchMessages({
          type: 'assistant_error',
          subtaskId: payload.subtask_id,
          error: payload.error,
        }),
    })
  }, [resolvedServices])

  const selectProject = useCallback(
    (projectId: number) => {
      const project = state.projects.find(item => item.id === projectId)
      if (project) dispatch({ type: 'project_selected', project })
    },
    [state.projects]
  )

  const openTask = useCallback(
    async (taskId: number) => {
      const detail = await resolvedServices.taskApi.getTaskDetail(taskId)
      dispatch({ type: 'task_opened', task: detail as Task })
      dispatchMessages({
        type: 'reset',
        messages: (detail.subtasks ?? []).map(subtaskToMessage),
      })
      await resolvedServices.chatStream.joinTask(taskId)
    },
    [resolvedServices]
  )

  const setInput = useCallback((input: string) => {
    dispatch({ type: 'input_changed', input })
  }, [])

  const sendCurrentInput = useCallback(async () => {
    const trimmedMessage = state.input.trim()
    const hasAttachments = attachmentSelection.attachments.length > 0
    if ((!trimmedMessage && !hasAttachments) || !state.defaultTeam) return
    const message = trimmedMessage || '请参考附件'

    dispatch({ type: 'sending_started' })
    dispatch({ type: 'input_changed', input: '' })
    dispatchMessages({
      type: 'user_added',
      message: {
        id: `local-${Date.now()}`,
        taskId: state.currentTask?.id,
        role: 'user',
        content: message,
        status: 'done',
        createdAt: new Date().toISOString(),
      },
    })

    const payload: ChatSendPayload = {
      task_id: state.currentTask?.id,
      team_id: state.defaultTeam.id,
      project_id: state.currentTask ? undefined : state.currentProject?.id,
      task_type: 'code',
      message,
    }

    if (!isOptionsLocked && modelSelection.selectedModel) {
      payload.model_id = modelSelection.selectedModel.name
      payload.force_override_bot_model = true
      payload.force_override_bot_model_type = modelSelection.selectedModel.type
    }

    if (!isOptionsLocked && skillSelection.selectedSkills.length > 0) {
      payload.additional_skills = skillSelection.selectedSkills
    }

    if (attachmentSelection.attachments.length > 0) {
      payload.attachment_ids = attachmentSelection.attachments.map(attachment => attachment.id)
    }

    const ack = await resolvedServices.chatStream.sendMessage(payload)
    dispatch({ type: 'sending_finished' })

    if (!ack.success) {
      dispatch({ type: 'error_set', error: ack.error ?? '发送失败' })
      return
    }

    attachmentSelection.resetAttachments()

    if (!state.currentTask && ack.task_id) {
      dispatch({
        type: 'task_opened',
        task: {
          id: ack.task_id,
          title: message.substring(0, 100),
          status: 'RUNNING',
          task_type: 'code',
          team_id: state.defaultTeam.id,
          created_at: new Date().toISOString(),
        },
      })
    }
  }, [
    attachmentSelection,
    isOptionsLocked,
    modelSelection.selectedModel,
    resolvedServices,
    skillSelection.selectedSkills,
    state.currentProject?.id,
    state.currentTask,
    state.defaultTeam,
    state.input,
  ])

  const value: WorkbenchContextValue = {
    state,
    messages,
    projectChat: {
      models: modelSelection.models,
      skills: skillSelection.skills,
      selectedModel: modelSelection.selectedModel,
      selectedSkills: skillSelection.selectedSkills,
      attachments: attachmentSelection.attachments,
      uploadingFiles: attachmentSelection.uploadingFiles,
      errors: attachmentSelection.errors,
      isOptionsLocked,
      isAttachmentReadyToSend: attachmentSelection.isAttachmentReadyToSend,
      setSelectedModel: modelSelection.setSelectedModel,
      setSelectedSkills: skillSelection.setSelectedSkills,
      toggleSkill: skillSelection.toggleSkill,
      handleFileSelect: attachmentSelection.handleFileSelect,
      addExistingAttachment: attachmentSelection.addExistingAttachment,
      removeAttachment: attachmentSelection.removeAttachment,
      resetAttachments: attachmentSelection.resetAttachments,
    },
    selectProject,
    openTask,
    setInput,
    sendCurrentInput,
  }

  return (
    <WorkbenchContext.Provider value={value}>
      {children}
    </WorkbenchContext.Provider>
  )
}
