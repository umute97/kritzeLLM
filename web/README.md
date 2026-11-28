# web

The Vue 3 web app for uploading pages, reviewing transcriptions and chatting with the journal 🌸

Vite, Vue 3.5, TypeScript, Pinia, Vue Router and Tailwind v4. Node 26 (see `.nvmrc`).

```sh
just web-install     # npm ci
just web-dev         # http://localhost:5173, with /api sent to the API on $API_PORT
just web-test        # vitest
just web-lint        # eslint + prettier
just web-api-types   # regenerate src/api/schema.d.ts after api/openapi.json changed
```

In the compose stack (`just up`) the app runs at <http://localhost:8080>: nginx serves the built
files and passes `/api` on to the `api` service.

## What's where

| Path                  | What lives there                                                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/ui/`             | The cottage component library (`KButton`, `KPageCard`, `useToasts()` …), exported from `src/ui/index.ts`                                     |
| `src/api/`            | The typed API client: generated `schema.d.ts`, `call()` and `configureApi()`, uploads with progress, images behind the token, chat streaming |
| `src/stores/`         | Pinia stores: the token, API health, the journal shelf, pages (with a poller for busy ones), uploads, chats                                  |
| `src/views/`          | The screens: library and upload, page detail, search, chat                                                                                   |
| `src/components/`     | Screen parts: token prompt, journal dialog, upload batch, page thumbnails, search hits, and the chat's list, thread, answers and sources     |
| `src/composables/`    | Screen logic: actions and confirm dialogs that toast when they fail, form dialogs, block drafts, the unsaved-changes guard, recent searches  |
| `src/utils/`          | Plain helpers: dates and file sizes, search marks, chat citations, photo rules, browser storage                                              |
| `src/i18n/`           | vue-i18n: the English and German words, the cottage library in German, picking and switching languages                                       |
| `src/styles/main.css` | Tailwind, the palette and type as theme tokens, base styles                                                                                  |
| `Dockerfile`          | The built app on nginx (`nginx.conf`)                                                                                                        |

Tests live next to the code in `__tests__/` folders; `src/test-utils.ts` has their shared builders
and helpers.

The design reference (colours, type, every component and every screen) is
[`docs/design/README.md`](../docs/design/README.md).
