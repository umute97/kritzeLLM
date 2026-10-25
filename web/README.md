# web

The Vue 3 web app for uploading pages, reviewing transcriptions and chatting with the journal 🌸

Vite, Vue 3.5, TypeScript and Tailwind v4. Node 24 (see `.nvmrc`).

```sh
just web-install   # npm ci
just web-dev       # http://localhost:5173
just web-test      # vitest
just web-lint      # eslint + prettier
```

## What's where

| Path                  | What lives there                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| `src/ui/`             | The cottage component library (`KButton`, `KPageCard`, `useToasts()` …), exported from `src/ui/index.ts` |
| `src/ui/__tests__/`   | Component tests (Vitest + Vue Test Utils)                                                                |
| `src/styles/main.css` | Tailwind, the palette and type as theme tokens, base styles                                              |

The design reference (colours, type, every component and every screen) is
[`docs/design/README.md`](../docs/design/README.md).
