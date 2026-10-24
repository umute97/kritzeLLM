# kritzeLLM design: cottage edition 🌸

A cosy, cottagecore look for the web app: lined paper, a pencil, a few doodles, and calm colours
from the *Cottagecore Meadow Warmth* palette. Every screen is built from the component library in
[`web/src/ui/`](../../web/src/ui/). This page is the reference for what those pieces are, how
they're used, and how the screens fit together, including the ones whose backend isn't built yet.

## Colours

| Token | Hex | What it's for |
|---|---|---|
| `sand` (Pogo Sands) | `#EDE5D2` | The page ground |
| `herb` (Green Herb) | `#A7C186` | **The accent**: main buttons, the current tab, picked things |
| `orchid` (Petite Orchid) | `#D6938A` | Count badges, "indexing", source highlights |
| `lemon` (Luscious Lemon) | `#EFC06E` | "Transcribing", warnings, the chat helper's avatar |
| `clay` (Deathclaw Brown) | `#B46A55` | Doodles, dashed frames, a journal cover |
| `ink` | `#3D2B22` | All text, all outlines, the pressed-button shadow |
| `bark` | `#8A4A3A` | Links, small accent text, errors, danger buttons |
| `muted` | `#6E5A4C` | Secondary text (5:1 on sand) |
| `cream` / `paper` | `#FBF7EE` / `#FFFDF8` | Cards / fields and paper |
| `line` / `edge` | `#D9CCB0` / `#9A8467` | Quiet borders / field borders (3:1) |

Rules:

- Text is always `ink`, `muted` or `bark`. `clay` is too light for body text (3.3:1 on sand), so
  it's only for doodles, frames and large shapes.
- Filled controls use a soft ground with `ink` text. The one exception is `bark`, which takes
  `cream` text (errors, danger buttons, the "Failed" chip).
- Colour only hints. Every status also says it in words, and picked chips get a tick.
- The palette lives in `@theme` in [`web/src/styles/main.css`](../../web/src/styles/main.css),
  so it's available as Tailwind classes (`bg-herb`, `text-bark`, `border-edge` …). The accent is
  `--color-accent`, so swapping Herb for Orchid or Lemon is a one-line change.

## Type

- **Fraunces** (soft) for headings: `font-display`, weight 600, with `'SOFT' 100`.
- **Nunito** for everything you read: `font-sans`, 16px body, 1.55 line height.
- **Indie Flower** for handwritten asides: `font-hand`. Use it for notes, empty states, the
  greeting, page thumbnails and the "letter" chat style. Never use it for anything you must read
  to get something done.

All three are installed from npm (`@fontsource`), so the app never calls Google Fonts.

## Shape and feel

- Radii: `rounded-card` (18px) for cards and banners, `rounded-field` (9px) for fields and small
  cards. Buttons, chips and the search bar are fully round.
- Shadows are flat offsets, never blurs. Main buttons sit on a 3px ink shadow, lift on hover and
  sink when pressed. Page cards cast a soft clay shadow and tilt a little (`tiltFor(index)`).
- Lined paper (`paper-lines`, with `--line` setting the spacing) stands in for a page.
- Doodles (`KDoodle`: daisy, sprig, heart, sparkle, squiggle) are sprinkled lightly: one per empty
  state or dialog, never everywhere.
- The logo is a pencil drawing a squiggle (`KLogo`), because *kritzeln* means "to scribble".
- Focus is a 3px `bark` outline. Every target is at least 44px. Motion stops when the system asks
  for less motion.

## Components

Everything is exported from [`web/src/ui/index.ts`](../../web/src/ui/index.ts) with a `K` prefix.

| Group | Components | Notes |
|---|---|---|
| Buttons | `KButton`, `KIconButton` | `main` (one per view), `second`, `quiet`, `danger` (confirm dialogs only); `sm` inside cards and toasts; `loading`, `disabled`; `as` renders a link or `RouterLink` |
| Fields | `KTextField`, `KTextArea`, `KSelect`, `KSearchField`, `KCheckbox`, `KSwitch`, `KFieldShell` | A label above, help or an error below. Errors set `aria-invalid` and `aria-describedby`. The token field can be `revealable` |
| Chips | `KChip`, `KStatusChip`, `KBlockKindTag`, `KFlag`, `KBadge` | Page status: Uploaded, Transcribing, Indexing, Ready, Failed. Job status: Waiting, Working, Done, Failed. Flags: not quite sure, already here, edited by you, saved |
| Pickers | `KFilterChips`, `KSegmented` | Single choice, `aria-pressed` |
| Feedback | `KToast` + `KToastStack` + `useToasts()`, `KBanner` | See below |
| Overlays | `KDialog`, `KMenu`, `KTooltip` | Native `<dialog>`; the menu has arrow keys and Escape, with danger items alone at the bottom |
| Navigation | `KTopNav`, `KNavLink`, `KBreadcrumb`, `KPageStepper`, `KShelfPager`, `KLoadMore` | On phones the nav links fold behind a menu button |
| Progress | `KProgressBar`, `KSpinner` (ring, daisy), `KTypingDots`, `KSkeleton`, `KEmptyState` | A bar when we know how long, a daisy when we don't |
| Journals and pages | `KJournalCover`, `KAddTile`, `KPageCard`, `KDropzone`, `KUploadRow`, `KBlockCard` | See the screens below |
| Search and chat | `KSearchResult`, `KScoreBars`, `KHighlight`, `KMessage`, `KToolActivity`, `KCitationChip`, `KSourceCard`, `KComposer` | Built ahead of their screens |

### Toasts and banners

- **Toasts** are for things that just happened. Success and info leave after 5 seconds (hover or
  focus holds them). Warnings, errors and progress stay until dismissed. At most three show; older
  ones fold away. They sit bottom right on wide screens and top, full width, on phones.
- An API problem (`application/problem+json`) becomes an error toast with its `title` and
  `detail`. The status and path sit behind "Show details".
- **Banners** are for trouble that sticks around until it's fixed:
  - the API can't be reached ("The cottage door is shut", with a retry)
  - the token was refused (a 401, which asks for the token again)
  - a page failed to transcribe (shows the page's `error`, plus Re-transcribe)
  - a form came back with a 422 (one line per error, each linking to its field)

## Screens

The nav has **Pages · Search · Chat**, a pencil logo and a handwritten "hi there". A screen joins
the nav when its backend exists.

### Token prompt

- A small "Knock knock" card asks for `API_TOKEN` (from `.env`), with a peek button and "Remember
  this token on this device".
- It shows on first visit and again after any 401.

### Pages: library and upload (#14)

- **Header:** "Your journals" and a *New journal* button, which opens a dialog with a name and an
  optional description.
- **Shelf:** journal covers, 4 at a time, with `KShelfPager` arrows. `GET /journals` pages with a
  cursor and has no total, so the shelf shows "Journals 1–4" and the next arrow rests when
  `nextCursor` is null. Picking a cover opens that journal.
- **Upload:**
  - The dropzone takes JPEG, PNG, HEIC/HEIF or WebP, up to 25 MB each and 100 per upload
    (`POST /journals/{id}/pages`). Anything else is rejected right there.
  - Next to it, a batch card lists one `KUploadRow` per file. Each row follows its page's job
    (`GET /jobs/{id}`): sending, waiting, transcribing, indexing, ready.
  - Duplicates (`duplicate: true`) show "Already here", linked to the existing page. Failures say
    why.
- **Page grid:**
  - Pinned `KPageCard`s with the thumbnail, number, date and status.
  - Filter chips: All, Ready, Still reading, Needs a hand (the `status` filter on `GET /pages`).
  - `KLoadMore` shows "Showing 8 of 48 pages", using the journal's `pageCount`.
  - Failed cards get a *Try again*.
- **Empty states:** no journals yet, no pages yet, nothing matches the filter.

### Page detail (#15)

- The photo on one side and the editable `KBlockCard`s on the other. On phones a
  Photo / Text / Both switch picks what to show.
- Blocks have **no position on the photo**: locations were dropped in #11. Hovering or focusing a
  block only highlights it in the list.
- Editing a block shows "changed, not saved" with Undo and Save (`PATCH /blocks/{id}`).
  Cmd/Ctrl+Enter saves, Escape undoes. Unsure blocks get "Looks right".
- Header: breadcrumb, page number and status, *Re-transcribe* (`POST /pages/{id}/transcribe`),
  a page actions menu, and *Delete page* with a confirm dialog.
- A failed page shows a banner with its error. `KPageStepper` moves to the neighbouring pages.

### Search (#17, #18): designed, waiting for the API

- A large `KSearchField`, then filters for journal and dates (`journalId`, `dateFrom`, `dateTo`).
- Results are `KSearchResult`s: thumbnail, page, journal, date, block kind, and the quote with the
  match marked. Each opens Page detail with the block highlighted.
- A *Show scores* switch is the debug view (#18). It adds `KScoreBars` (Words, Meaning, Blended)
  and a Blended / Words / Meaning sort, which maps to `mode=hybrid|keyword|vector`.
- A side column shows recent searches and a tip that search finds ideas, not just words.
- With no results: "No pages mention “otters”", plus *Search all journals*.

### Chat (#19–#21): designed, waiting for the API

- Three columns that stack on phones: conversations (with *New chat*), the thread, and Sources.
- **Thread:**
  - Your messages are accent bubbles on the right. Answers are `KMessage` bubbles, or a "letter"
    on lined paper.
  - While streaming there's a caret. `KTypingDots` and `KToolActivity` lines ("looking through
    your journal for …", "reading page 14…") come from the `toolCall` events and fold into
    "searched twice, read 4 pages" when the answer ends.
  - A broken stream keeps what arrived and offers *Ask again*.
- **Citations:** `KCitationChip`s ("p. 12") inside the answer. Clicking one picks its
  `KSourceCard` in Sources (quote marked, *Open the page*), which opens Page detail with that
  block highlighted.
- **Writing box:** `KComposer`. Enter sends, Shift+Enter adds a line, and Send turns into Stop
  while an answer streams.
- A fresh chat shows "Ask your journal anything" with three starter questions.

## Where the design came from

The screens and components were laid out on a design canvas and exported as a PDF. The export
isn't in the repo (it's large and only images); keep a local copy at `docs/design/*.pdf`, which
git ignores.
