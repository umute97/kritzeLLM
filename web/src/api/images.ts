import { ref, toValue, watchEffect, type MaybeRefOrGetter } from 'vue'

import { extensionFor } from '@/utils/photos'

import { authHeaders } from './client'

async function fetchBlob(url: string): Promise<Blob> {
  const response = await globalThis.fetch(url, { headers: authHeaders() })
  if (!response.ok) throw new Error(`Image ${url} answered ${response.status}`)
  return response.blob()
}

// Page images sit behind the token, which an <img> can't send. So they're fetched once with the
// token and shown from an object URL. A page's images never change, so they're kept for the
// session.
const cache = new Map<string, Promise<string>>()

function fetchImage(url: string): Promise<string> {
  let pending = cache.get(url)
  if (!pending) {
    pending = fetchBlob(url).then((blob) => URL.createObjectURL(blob))
    pending.catch(() => cache.delete(url))
    cache.set(url, pending)
  }
  return pending
}

/** A ready-to-use `src` for an API image URL, or undefined while it loads (or if it failed). */
export function useAuthedImage(url: MaybeRefOrGetter<string | undefined>) {
  const src = ref<string>()
  watchEffect(async (onCleanup) => {
    const current = toValue(url)
    let cancelled = false
    onCleanup(() => (cancelled = true))
    src.value = undefined
    if (!current) return
    try {
      const objectUrl = await fetchImage(current)
      if (!cancelled) src.value = objectUrl
    } catch {
      // A missing image leaves the lined-paper placeholder.
    }
  })
  return src
}

/** Saves an API image as a file named `baseName` plus the extension of its real type. */
export async function downloadImage(url: string, baseName: string) {
  const blob = await fetchBlob(url)
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = `${baseName}.${extensionFor(blob.type)}`
  link.click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
