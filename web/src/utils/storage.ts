// Private windows and blocked site data can throw on any access; then nothing is kept.
type Area = 'local' | 'session'

function area(kind: Area): Storage | null {
  try {
    return kind === 'local' ? globalThis.localStorage : globalThis.sessionStorage
  } catch {
    return null
  }
}

export function readStored(key: string, kind: Area = 'local'): string | null {
  try {
    return area(kind)?.getItem(key) ?? null
  } catch {
    return null
  }
}

/** Keeps `value` under `key`, or drops the key for `null`. */
export function writeStored(key: string, value: string | null, kind: Area = 'local') {
  try {
    if (value === null) area(kind)?.removeItem(key)
    else area(kind)?.setItem(key, value)
  } catch {
    // Not kept, but it still holds for this visit.
  }
}
