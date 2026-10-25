import { useAuth } from '@/stores/auth'
import { useHealth } from '@/stores/health'

import { API_BASE } from './client'
import { ApiError, offlineProblem, toProblem } from './errors'
import type { UploadResult } from './types'

/**
 * Uploads one photo to a journal. This uses XMLHttpRequest rather than fetch, because only XHR
 * reports upload progress.
 */
export function uploadPage(
  journalId: string,
  file: File,
  onProgress: (sent: number, total: number) => void,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/journals/${encodeURIComponent(journalId)}/pages`)
    xhr.responseType = 'json'
    const { token } = useAuth()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded, event.total)
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as UploadResult)
        return
      }
      if (xhr.status === 401) useAuth().reject()
      const response = new Response(null, { status: xhr.status, statusText: xhr.statusText })
      reject(new ApiError(toProblem(xhr.response, response)))
    }
    xhr.onerror = () => {
      useHealth().markOffline()
      reject(new ApiError(offlineProblem))
    }

    const form = new FormData()
    form.append('files', file, file.name)
    xhr.send(form)
  })
}
