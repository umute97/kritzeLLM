// What the API takes (see `PageUpload` in the contract), with each type's file extension.
const TYPES: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/heic': 'heic',
  'image/heif': 'heif',
  'image/webp': 'webp',
}
const EXTENSIONS = new RegExp(`\\.(jpeg|${Object.values(TYPES).join('|')})$`, 'i')

export const MAX_BYTES = 25 * 1024 * 1024
export const MAX_FILES = 100

/** For a file picker. HEIC goes by name too, since some browsers can't name its type. */
export const PHOTO_ACCEPT = [...Object.keys(TYPES), '.heic', '.heif'].join(',')

export function looksLikePhoto(file: File): boolean {
  return Object.hasOwn(TYPES, file.type) || (file.type === '' && EXTENSIONS.test(file.name))
}

export function extensionFor(type: string): string {
  return Object.hasOwn(TYPES, type) ? TYPES[type]! : 'jpg'
}
