// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import { useCallback, useEffect, useState } from 'react'
import { adminApis, AdminPublishedApp } from '@/apis/admin'
import { useTranslation } from '@/hooks/useTranslation'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export default function PublishedAppList() {
  const { t } = useTranslation()
  const [items, setItems] = useState<AdminPublishedApp[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await adminApis.getPublishedApps(page, 20, search.trim() || undefined)
      setItems(response.items)
      setTotal(response.total)
    } catch (error) {
      console.error('Failed to load published apps', error)
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    loadData()
  }, [loadData])

  const totalPages = Math.max(1, Math.ceil(total / 20))

  const tp = (key: string, options?: Record<string, unknown>) =>
    t(`admin:published_apps.${key}`, {
      ...options,
      defaultValue: t(`common:published_apps.${key}`, options),
    })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-text-primary">{tp('title')}</h2>
        <div className="flex items-center gap-2">
          <Input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder={tp('search_placeholder')}
            className="w-64"
            data-testid="published-apps-search-input"
          />
          <Button
            variant="outline"
            onClick={() => {
              setPage(1)
              loadData()
            }}
            data-testid="published-apps-search-button"
          >
            {tp('search')}
          </Button>
        </div>
      </div>

      <div className="rounded-md border border-border overflow-x-auto bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-text-secondary">
              <th className="px-4 py-3">{tp('columns.user_id')}</th>
              <th className="px-4 py-3">{tp('columns.app_name')}</th>
              <th className="px-4 py-3">{tp('columns.task_id')}</th>
              <th className="px-4 py-3">{tp('columns.workspace')}</th>
              <th className="px-4 py-3">{tp('columns.public_url')}</th>
              <th className="px-4 py-3">{tp('columns.published_at')}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td className="px-4 py-6 text-text-secondary" colSpan={6}>
                  {tp('loading')}
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-text-secondary" colSpan={6}>
                  {tp('empty')}
                </td>
              </tr>
            ) : (
              items.map(item => (
                <tr
                  key={`${item.user_id}-${item.workspace_id}`}
                  className="border-b border-border last:border-0"
                >
                  <td className="px-4 py-3">{item.user_id}</td>
                  <td className="px-4 py-3">{item.app_name || '-'}</td>
                  <td className="px-4 py-3">{item.task_id}</td>
                  <td className="px-4 py-3">{item.workspace_name || item.workspace_id}</td>
                  <td className="px-4 py-3">
                    {item.public_url ? (
                      <a
                        href={item.public_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        {item.public_url}
                      </a>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-4 py-3">{item.published_at || '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm text-text-secondary">
        <span>{tp('pagination.total', { total })}</span>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(prev => Math.max(1, prev - 1))}
            disabled={page <= 1}
            data-testid="published-apps-prev-button"
          >
            {tp('pagination.prev')}
          </Button>
          <span>
            {page}/{totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
            disabled={page >= totalPages}
            data-testid="published-apps-next-button"
          >
            {tp('pagination.next')}
          </Button>
        </div>
      </div>
    </div>
  )
}
