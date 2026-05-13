// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import { apiClient } from './client'
import {
  AgentProject,
  AgentProjectListResponse,
  AgentProjectWithTasks,
  SuccessMessage,
} from '../types/api'

export interface TeamRef {
  name: string
  namespace: string
  user_id: number
}

export interface CreateAgentProjectRequest {
  name: string
  description?: string
  environment_type: string
  team_ref: TeamRef
  directory_path?: string
  git_url?: string
  git_repo?: string
  git_branch?: string
  device_id?: string
}

export interface UpdateAgentProjectRequest {
  name?: string
  description?: string
  environment_type?: string
  team_ref?: TeamRef
  directory_path?: string
  git_url?: string
  git_repo?: string
  git_branch?: string
  device_id?: string
}

export interface CreateTaskFromProjectRequest {
  prompt: string
  title?: string
}

export const agentProjectApis = {
  getAgentProjects: async (): Promise<AgentProjectListResponse> => {
    return apiClient.get('/v1/agent-projects')
  },

  getAgentProject: async (projectId: number): Promise<AgentProjectWithTasks> => {
    return apiClient.get(`/v1/agent-projects/${projectId}`)
  },

  createAgentProject: async (
    data: CreateAgentProjectRequest
  ): Promise<AgentProjectWithTasks> => {
    return apiClient.post('/v1/agent-projects', data)
  },

  updateAgentProject: async (
    projectId: number,
    data: UpdateAgentProjectRequest
  ): Promise<AgentProjectWithTasks> => {
    return apiClient.put(`/v1/agent-projects/${projectId}`, data)
  },

  deleteAgentProject: async (projectId: number): Promise<SuccessMessage> => {
    return apiClient.delete(`/v1/agent-projects/${projectId}`)
  },

  createTaskFromProject: async (
    projectId: number,
    data: CreateTaskFromProjectRequest
  ): Promise<{ task_id: number }> => {
    return apiClient.post(`/v1/agent-projects/${projectId}/tasks`, data)
  },
}
