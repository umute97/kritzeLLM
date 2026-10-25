import { ref, toValue, watchEffect, type MaybeRefOrGetter } from 'vue'

import { useAuth } from '@/stores/auth'

// Page images sit behind the token, which an <img> can't send. So they're fetched once with the
// token and shown from an object URL. A page's images never change, so they're kept for the
// session.
const cache = new Map<string, Promise<string>>()

export function fetchImage(url: string): Promise<string> {
  let pending = cache.get(url)
  if (!pending) {
    const { token } = useAuth()
    pending = globalThis
      .fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Image ${url} answered ${response.status}`)
        return URL.createObjectURL(await response.blob())
      })
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

const extensions: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/heic': 'heic',
  'image/heif': 'heif',
  'image/webp': 'webp',
}

/** Saves an API image as a file named `baseName` plus the extension of its real type. */
export async function downloadImage(url: string, baseName: string) {
  const { token } = useAuth()
  const response = await globalThis.fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error(`Image ${url} answered ${response.status}`)
  const blob = await response.blob()
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = `${baseName}.${extensions[blob.type] ?? 'jpg'}`
  link.click()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}
