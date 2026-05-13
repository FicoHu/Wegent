// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import { useState, useEffect } from 'react'
import { useTranslation } from '@/hooks/useTranslation'
import { useAgentProjectContext } from '../contexts/agentProjectContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { teamApis } from '@/apis/team'
import { deviceApis } from '@/apis/devices'
import { Team, Device, AgentProjectWithTasks } from '@/types/api'

interface AgentProjectEditDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  project: AgentProjectWithTasks | null
}

export function AgentProjectEditDialog({ open, onOpenChange, project }: AgentProjectEditDialogProps) {
  const { t } = useTranslation('agent-projects')
  const { updateProject } = useAgentProjectContext()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [environmentType, setEnvironmentType] = useState('cloud_docker')
  const [teamName, setTeamName] = useState('')
  const [teamNamespace, setTeamNamespace] = useState('default')
  const [teamUserId, setTeamUserId] = useState(0)
  const [directoryPath, setDirectoryPath] = useState('')
  const [gitUrl, setGitUrl] = useState('')
  const [gitRepo, setGitRepo] = useState('')
  const [gitBranch, setGitBranch] = useState('main')
  const [deviceId, setDeviceId] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [teams, setTeams] = useState<Team[]>([])
  const [devices, setDevices] = useState<Device[]>([])

  useEffect(() => {
    if (open) {
      teamApis.getTeams({ page: 1, limit: 100 }, 'personal').then(res => setTeams(res.items || []))
      deviceApis.getAllDevices().then(res => setDevices(res.items || []))
    }
  }, [open])

  useEffect(() => {
    if (project) {
      setName(project.name)
      setDescription(project.description || '')
      setEnvironmentType(project.environment_type)
      setTeamName(project.team_ref.name)
      setTeamNamespace(project.team_ref.namespace)
      setTeamUserId(project.team_ref.user_id)
      setDirectoryPath(project.directory_path || '')
      setGitUrl(project.git_url || '')
      setGitRepo(project.git_repo || '')
      setGitBranch(project.git_branch || 'main')
      setDeviceId(project.device_id || '')
    }
  }, [project])

  const needsDevice = environmentType === 'local_device' || environmentType === 'cloud_device'

  const handleSubmit = async () => {
    if (!project || !name || !teamName) return
    setIsSubmitting(true)
    await updateProject(project.id, {
      name,
      description,
      environment_type: environmentType,
      team_ref: { name: teamName, namespace: teamNamespace, user_id: teamUserId },
      directory_path: directoryPath || undefined,
      git_url: gitUrl || undefined,
      git_repo: gitRepo || undefined,
      git_branch: gitBranch || undefined,
      device_id: needsDevice ? deviceId : undefined,
    })
    setIsSubmitting(false)
    onOpenChange(false)
  }

  const handleTeamChange = (value: string) => {
    const selected = teams.find(t => `${t.namespace}:${t.name}` === value)
    if (selected) {
      setTeamName(selected.name)
      setTeamNamespace(selected.namespace || 'default')
      setTeamUserId(selected.user_id || 0)
    }
  }

  if (!project) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('edit.title')}</DialogTitle>
          <DialogDescription>{t('edit.description')}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="edit-project-name">{t('form.name')}</Label>
            <Input
              id="edit-project-name"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={t('form.namePlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-project-description">{t('form.description')}</Label>
            <Input
              id="edit-project-description"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder={t('form.descriptionPlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-project-env">{t('form.environment')}</Label>
            <Select value={environmentType} onValueChange={setEnvironmentType}>
              <SelectTrigger id="edit-project-env">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="cloud_docker">{t('form.env.cloudDocker')}</SelectItem>
                <SelectItem value="local_device">{t('form.env.localDevice')}</SelectItem>
                <SelectItem value="cloud_device">{t('form.env.cloudDevice')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-project-team">{t('form.team')}</Label>
            <Select value={`${teamNamespace}:${teamName}`} onValueChange={handleTeamChange}>
              <SelectTrigger id="edit-project-team">
                <SelectValue placeholder={t('form.teamPlaceholder')} />
              </SelectTrigger>
              <SelectContent>
                {teams.map(team => (
                  <SelectItem key={team.id} value={`${team.namespace || 'default'}:${team.name}`}>
                    {team.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {needsDevice && (
            <div className="space-y-2">
              <Label htmlFor="edit-project-device">{t('form.device')}</Label>
              <Select value={deviceId} onValueChange={setDeviceId}>
                <SelectTrigger id="edit-project-device">
                  <SelectValue placeholder={t('form.devicePlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {devices.map(device => (
                    <SelectItem key={device.id} value={device.device_id}>
                      {device.name || device.device_id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="edit-project-dir">{t('form.directory')}</Label>
            <Input
              id="edit-project-dir"
              value={directoryPath}
              onChange={e => setDirectoryPath(e.target.value)}
              placeholder={t('form.directoryPlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-project-git-url">{t('form.gitUrl')}</Label>
            <Input
              id="edit-project-git-url"
              value={gitUrl}
              onChange={e => setGitUrl(e.target.value)}
              placeholder={t('form.gitUrlPlaceholder')}
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-2">
              <Label htmlFor="edit-project-git-repo">{t('form.gitRepo')}</Label>
              <Input
                id="edit-project-git-repo"
                value={gitRepo}
                onChange={e => setGitRepo(e.target.value)}
                placeholder={t('form.gitRepoPlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-project-git-branch">{t('form.gitBranch')}</Label>
              <Input
                id="edit-project-git-branch"
                value={gitBranch}
                onChange={e => setGitBranch(e.target.value)}
                placeholder="main"
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common:actions.cancel')}
          </Button>
          <Button variant="primary" onClick={handleSubmit} disabled={isSubmitting || !name || !teamName}>
            {isSubmitting ? t('common:actions.saving') : t('common:actions.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
