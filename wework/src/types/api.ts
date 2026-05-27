export interface User {
  id: number
  user_name: string
  email: string
}

export interface Team {
  id: number
  name: string
  displayName?: string | null
  is_active: boolean
  default_for_modes?: string[]
  recommended_mode?: 'chat' | 'code' | 'both'
  agent_type?: string | null
}

export interface ProjectConfig {
  mode?: 'workspace' | string
  path?: string
  device_id?: string
}

export interface ProjectTask {
  id: number
  task_id: number
  title?: string
  created_at?: string
  updated_at?: string
  task_type?: string
}

export interface ProjectWithTasks {
  id: number
  name: string
  description?: string | null
  color?: string | null
  config?: ProjectConfig | null
  tasks?: ProjectTask[]
}

export interface ProjectListResponse {
  items: ProjectWithTasks[]
}

export interface Task {
  id: number
  title: string
  status: string
  task_type?: 'chat' | 'code' | 'task' | 'knowledge' | 'video' | 'image'
  team_id?: number
  created_at: string
  updated_at?: string
  is_group_chat?: boolean
  model_id?: string | null
  requested_skills?: SkillRef[]
}

export interface TaskListResponse {
  total: number
  items: Task[]
}

export interface TaskContextData {
  id: number
  context_type: 'attachment' | 'knowledge_base'
  name: string
  status: string
}

export interface Subtask {
  id: number
  role: string
  prompt?: string
  result?: unknown
  status: string
  created_at: string
  updated_at?: string
  contexts?: TaskContextData[]
  sender_user_name?: string
}

export interface TaskDetail extends Task {
  subtasks?: Subtask[]
}

export interface CreateProjectConversationRequest {
  prompt: string
  title?: string
  new_session?: boolean
}

export interface CreateProjectConversationResponse {
  task_id: number
  project_id: number
  task: unknown
}

export interface ChatSendPayload {
  task_id?: number
  team_id: number
  message: string
  title?: string
  task_type?: 'chat' | 'code' | 'task' | 'knowledge' | 'video' | 'image'
  project_id?: number
  model_id?: string
  force_override_bot_model?: boolean
  force_override_bot_model_type?: ModelType
  attachment_ids?: number[]
  additional_skills?: SkillRef[]
}

export interface ChatSendAck {
  success: boolean
  task_id?: number
  error?: string
}

export interface ChatStartPayload {
  task_id: number
  subtask_id: number
  bot_name?: string
  shell_type?: string
  message_id?: number
}

export interface ChatChunkPayload {
  task_id?: number
  subtask_id: number
  content: string
  offset: number
}

export interface ChatDonePayload {
  task_id?: number
  subtask_id: number
  offset: number
  result: Record<string, unknown> & { value?: string; error?: string }
  message_id?: number
}

export interface ChatErrorPayload {
  task_id?: number
  subtask_id: number
  error: string
  message_id?: number
}

export interface TaskJoinResponse {
  streaming?: {
    subtask_id: number
    offset: number
    cached_content: string
  }
  subtasks?: Array<Record<string, unknown>>
  error?: string
}

export type ModelType = 'public' | 'user' | 'group'

export interface UnifiedModel {
  name: string
  type: ModelType
  displayName?: string | null
  provider?: string | null
  modelId?: string | null
  namespace?: string
  config?: Record<string, unknown>
  isActive?: boolean
}

export interface UnifiedModelListResponse {
  data: UnifiedModel[]
}

export interface UnifiedSkill {
  id: number
  name: string
  namespace: string
  description: string
  displayName?: string
  version?: string
  author?: string
  tags?: string[]
  bindShells?: string[]
  visible?: boolean
  is_active: boolean
  is_public: boolean
  user_id: number
  created_at?: string
  updated_at?: string
}

export interface SkillRef {
  name: string
  namespace: string
  is_public: boolean
}

export type AttachmentStatus = 'uploading' | 'parsing' | 'ready' | 'failed'

export interface Attachment {
  id: number
  filename: string
  file_size: number
  mime_type: string
  status: AttachmentStatus
  text_length?: number | null
  error_message?: string | null
  error_code?: string | null
  subtask_id?: number | null
  file_extension: string
  created_at: string
}

export interface AttachmentUploadProgress {
  file: File
  progress: number
}

export interface MultiAttachmentUploadState {
  attachments: Attachment[]
  uploadingFiles: Map<string, AttachmentUploadProgress>
  errors: Map<string, string>
}
