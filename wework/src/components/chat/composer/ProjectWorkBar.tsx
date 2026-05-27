import { ChevronDown, FolderPlus } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ProjectWithTasks } from '@/types/api'
import { useOutsideClick } from './useOutsideClick'

interface ProjectWorkBarProps {
  projects: ProjectWithTasks[]
  currentProjectId?: number
  onSelectProject: (projectId: number) => void
}

export function ProjectWorkBar({ projects, currentProjectId, onSelectProject }: ProjectWorkBarProps) {
  const { t } = useTranslation('common')
  const containerRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const closeMenu = useCallback(() => setOpen(false), [])

  useOutsideClick(containerRef, open, closeMenu)

  const handleSelectProject = (projectId: number) => {
    onSelectProject(projectId)
    setOpen(false)
  }

  return (
    <div className="flex min-h-[56px] items-center px-6">
      <div ref={containerRef} className="relative">
        {open && (
          <div
            data-testid="project-work-menu"
            className="absolute bottom-[52px] left-0 z-40 max-h-72 w-80 overflow-y-auto rounded-2xl border border-border bg-base p-2 shadow-[0_16px_44px_rgba(0,0,0,0.16)]"
          >
            <div className="px-4 pb-2 pt-1 text-sm font-semibold text-text-muted">
              {t('workbench.projects', '项目')}
            </div>
            {projects.length === 0 ? (
              <div className="px-4 py-3 text-sm text-text-muted">
                {t('workbench.no_projects', '暂无项目')}
              </div>
            ) : (
              <div className="space-y-1">
                {projects.map(project => (
                  <button
                    key={project.id}
                    type="button"
                    data-testid={`project-option-${project.id}`}
                    onClick={() => handleSelectProject(project.id)}
                    className={`flex min-h-11 w-full items-center gap-3 rounded-xl px-4 py-2 text-left text-sm font-medium hover:bg-muted ${
                      project.id === currentProjectId ? 'text-text-primary' : 'text-text-secondary'
                    }`}
                  >
                    <FolderPlus className="h-4 w-4 shrink-0 text-text-secondary" />
                    <span className="min-w-0 flex-1 truncate">{project.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        <button
          type="button"
          data-testid="project-work-button"
          onClick={() => setOpen(current => !current)}
          className="flex h-11 min-w-[44px] items-center gap-2 rounded-full px-1 text-sm font-medium text-text-secondary hover:bg-muted"
          aria-expanded={open}
          aria-label={t('workbench.enter_project_work', '进入项目工作')}
        >
          <FolderPlus className="h-5 w-5" />
          <span>{t('workbench.enter_project_work', '进入项目工作')}</span>
          <ChevronDown className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
