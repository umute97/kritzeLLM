// Stroke icons on a 24×24 grid, drawn in currentColor. `width` overrides the stroke width.
export const icons = {
  upload: { d: 'M12 16V4M6 10l6-6 6 6M4 20h16' },
  drop: { d: 'M12 4v12M6 10l6 6 6-6M4 20h16' },
  plus: { d: 'M12 5v14M5 12h14' },
  close: { d: 'M6 6l12 12M18 6L6 18' },
  check: { d: 'M5 12l5 5 9-10', width: 2.6 },
  dots: { d: 'M5 12h.01M12 12h.01M19 12h.01', width: 4 },
  menu: { d: 'M4 7h16M4 12h16M4 17h16' },
  'chevron-left': { d: 'M15 18l-6-6 6-6' },
  'chevron-right': { d: 'M9 18l6-6-6-6' },
  'chevron-down': { d: 'M6 9l6 6 6-6' },
  'arrow-up': { d: 'M12 19V5M5 12l7-7 7 7' },
  'arrow-right': { d: 'M5 12h14M13 6l6 6-6 6' },
  download: { d: 'M12 4v12M6 10l6 6 6-6M4 20h16' },
  trash: { d: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13' },
  refresh: { d: 'M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7' },
  reconnect: { d: 'M4 14a8 8 0 0 1 14-6M20 10a8 8 0 0 1-14 6M18 4v4h-4M6 20v-4h4' },
  search: { d: 'M15.5 15.5L20 20M17 11a6 6 0 1 1-12 0 6 6 0 0 1 12 0z' },
  book: { d: 'M3 5h6a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H3zM21 5h-6a3 3 0 0 0-3 3v12a2 2 0 0 1 2-2h7z' },
  eye: {
    d: 'M3 12c0-2 4-7 9-7s9 5 9 7-4 7-9 7-9-5-9-7zM14.5 12a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z',
  },
  'eye-off': {
    d: 'M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.1A10 10 0 0 1 12 5c5 0 9 5 9 7a8 8 0 0 1-2.2 3.3M6.6 6.6C4.4 8 3 10.4 3 12c0 2 4 7 9 7a9 9 0 0 0 4.4-1.2',
  },
  key: { d: 'M11 12l9-9M17 6l3 3M15 8l2 2M12 15a4 4 0 1 1-8 0 4 4 0 0 1 8 0z' },
  'door-shut': { d: 'M3 11l9-7 9 7M5 10v10h14V10M3 3l18 18' },
  'file-x': { d: 'M6 3h9l4 4v14H6zM14 3v5h5M9.5 13.5l5 5M14.5 13.5l-5 5' },
  alert: { d: 'M12 6.5v7M12 17.5h.01', width: 3 },
  'alert-circle': { d: 'M12 7.5v5M12 16.5h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z', width: 2.4 },
  info: { d: 'M12 11v6M12 7.5h.01', width: 2.6 },
  question: { d: 'M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 18h.01', width: 2.4 },
  settings: {
    d: 'M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
  },
} as const

export type IconName = keyof typeof icons
