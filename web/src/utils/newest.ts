/**
 * For requests that overtake each other: each call starts one and hands back `current()`, which
 * stays true only until the next one starts, so an overtaken answer can be dropped.
 */
export function newestWins() {
  let latest = 0
  return () => {
    const mine = ++latest
    return () => mine === latest
  }
}
