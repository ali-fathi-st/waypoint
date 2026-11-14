# 4. Design system

The look is calm and information-dense: one accent color, thin borders
instead of shadows, a single typeface, and color used only when it means
something.

## Tokens (css/tokens.css)

Every value lives in one file as a CSS variable. Use the variables, never raw
values, and the whole site stays consistent.

### Colors

| Variable | Value | Use |
| --- | --- | --- |
| `--color-bg` | `#f6f7f9` | Page background |
| `--color-surface` | `#ffffff` | Panels, inputs, sidebar |
| `--color-surface-2` | `#f1f3f5` | Hovers, subtle fills, loading placeholders |
| `--color-border` | `#e1e4e8` | Panel and table lines |
| `--color-border-strong` | `#c9ced6` | Input borders |
| `--color-ink` | `#18202b` | Main text |
| `--color-ink-2` | `#4a5563` | Secondary text |
| `--color-ink-3` | `#66707c` | Hints, labels, timestamps |
| `--color-accent` | `#1d6b57` | Spruce green: main buttons, active states, score bars |
| `--color-danger` | `#b42318` | Errors, destructive buttons |
| `--color-warning` | `#8a5a00` | Overdue follow-ups, drafts needing review |
| `--color-info` | `#2457b3` | "New" and "Applied" badges |

Each status color has a `-soft` background version (e.g. `--color-danger-soft`).
All text colors meet WCAG AA contrast on white.

**Try it:** change `--color-accent` to `#2457b3` and refresh. Every button,
active tab, score bar and the chart turn blue.

### Type

One family, **Geist**, stored in `assets/fonts/` so nothing loads from other
sites. The body text is 14px (`--text-base`) for density.

| Variable | Size | Used for |
| --- | --- | --- |
| `--text-xs` | 12px | Labels, hints, badges |
| `--text-sm` | 13px | Secondary lines, meta |
| `--text-base` | 14px | Body text |
| `--text-md` | 16px | Dialog titles |
| `--text-lg` / `--text-xl` | 20 / 24px | Page titles (phone / desktop) |
| `--text-2xl` | 36px | The big match score |

### Spacing and shape

Spacing steps are 4px apart: `--space-1` (4px) through `--space-8` (32px).
Corners get rounder as things get bigger: badges 4px, buttons and inputs
6px, panels and dialogs 8px. Shadows appear only on things that float
(menus, dialogs, toasts).

## Components (css/components.css)

Copy these snippets into any page.

### Buttons

```html
<button type="button" class="btn btn--primary">Save profile</button>   <!-- the main action -->
<button type="button" class="btn">Cancel</button>                       <!-- normal -->
<button type="button" class="btn btn--ghost">Discard</button>           <!-- low emphasis -->
<button type="button" class="btn btn--danger">Delete all data</button>  <!-- destructive -->
<button type="button" class="btn btn--sm">Add skill</button>            <!-- compact -->
<button type="button" class="btn btn--ghost btn--icon" aria-label="Close">...</button>
```

One primary button per area. Write labels as actions ("Save notes", not
"Submit"), and keep the same words in the confirmation ("Notes saved").

### Form field

```html
<div class="field">
  <label for="email">Email <span class="required">*</span></label>
  <input class="input" id="email" type="email" aria-describedby="email-hint email-error" />
  <p class="field__hint" id="email-hint">We only use it for reminders.</p>
  <p class="field__error" id="email-error" hidden></p>
</div>
```

Show an error by filling `field__error`, removing `hidden`, and adding
`aria-invalid="true"` to the input (the border turns red). Put fields in
`<div class="form-grid form-grid--2">` for two columns on wider screens.

Other controls: `select.select`, `textarea.textarea`,
`input.input--search` (with magnifier), `input.switch` (toggle),
`label.check` (checkbox or radio with its label).

### Panel

```html
<section class="panel">
  <div class="panel__header">
    <div>
      <h2>Notes</h2>
      <p>Private to you.</p>
    </div>
    <button type="button" class="btn btn--sm">Add</button>
  </div>
  <div class="panel__body">...</div>
</section>
```

Panels are the only "cards". Group related things in one panel rather than
many small boxes.

### Badges

From JavaScript (`js/ui/badges.js`): `applicationBadge("interview")`,
`jobBadge("shortlisted")`, `documentBadge("draft")`. In HTML:
`<span class="badge badge--warning">Draft</span>`. Tones: (default grey),
`--accent`, `--info`, `--warning`, `--danger`, `--outline`.

### Tables

```html
<div class="table-wrap">
  <table class="table table--stack">...</table>
</div>
```

`table--stack` turns each row into a stacked card on phones. Mark cells with
`stack-lead` (left column), `stack-main` (the title), `stack-end` (buttons),
`stack-full` (detail lines) or `stack-hide` (not shown on phones).

### Loading, empty, error

From `js/ui/states.js`:

```js
render(el, loadingRows(5));
render(el, emptyState({ title: "No applications yet", description: "Open a job and choose Start application.", action: someButton }));
render(el, errorState(error, load)); // includes a "Try again" button
```

**Rule:** no list is ever just blank. Empty states say *why* it's empty and
*what to do*. Error messages say what failed and how to fix it.

### Dialogs

Use the native `<dialog class="dialog">` (see the "Record as applied" dialog in
`application.html`). For a quick "Are you sure?":

```js
const ok = await confirmAction({
  title: "Withdraw?",
  message: "This closes the application.",
  confirmLabel: "Withdraw",
  danger: true,
});
```

Add `requireText: "DELETE"` for things that can't be undone.

### Toasts

```js
toast.success("Notes saved");
toast.error("Couldn't save notes", describeError(e));
```

## Writing style

- Plain words a non-technical person understands: "Record as applied", not
  "Confirm submission event".
- Sentence case everywhere ("Save profile", not "Save Profile").
- Buttons say what happens. Confirmations repeat the same words.
- Errors say what happened and what to do. They don't apologize.
- Never say an application was sent or seen unless that's confirmed.

## Responsive layout

| Width | Layout |
| --- | --- |
| Under 640px (phones) | Single column, top bar with menu button, tables become stacked rows, secondary filters behind "More filters" |
| 640–1023px (tablets) | Two-column forms, still the top bar |
| 1024px and up | Fixed sidebar, side columns on detail pages |

No page scrolls sideways at any width. Only the applications board scrolls
sideways, inside its own box.

Next: [05 GitHub Pages](05-github-pages.md)
