# Design Reference

Loaded by the dev-skills skill **when a project with a UI (web, desktop,
Android, Home Assistant panel) is designed, gets a new screen, or has no
`DESIGN.md` yet, when the user asks for a design audit** (`SKILL.md` §10,
standard 6), **and at Gate 2's visual pass** for the tell list. Section
numbers point at `SKILL.md`.

---

## DESIGN.md

Every UI project keeps a `DESIGN.md` at the repo root in the
[Google Labs DESIGN.md format](https://github.com/google-labs-code/design.md)
(`docs/spec.md`): YAML tokens up top, then prose sections in the spec's order.
Read the spec when writing one; it is alpha, so don't work from memory. Keep
the file under ~200 lines, and write rules as element + property + value
("table rows 36px, no zebra"), never adjectives ("modern", "clean").

It must decide:

- **Identity** in one line (Overview), taken from the product: who uses it,
  where, and what it handles. Not from a template or a named brand.
- **Shape before colour**: corner radius, density/spacing and type scale
  carry more of an app's look than its palette.
- **Colour tokens**: accent, surfaces, status (chosen to fit the palette, not
  a framework's defaults), and on-colour tokens for filled states
  (`on-accent`, `on-danger`).
- **Type roles**: which family for body, headings, numbers/code, and why.
- **Elevation**: how depth is shown (borders, tone, shadow, or none).
- **Components with their states** as variants (`button-danger`,
  `button-danger-hover`), so contrast is checked where it usually fails.
- **Do's and Don'ts**: the Never list, starting from the tells below that
  this project didn't choose.

**Themes:** the spec has none. Give each extra theme its own colour tokens
(`surface-dark`) and component variants (`button-danger-hover-dark`), so the
linter checks every pair in every theme.

**Lint**, with the version pinned, whenever `DESIGN.md` or the token files change:

```bash
npx -y @google/design.md@0.4.0 lint DESIGN.md
```

Its `contrast-ratio` warning (WCAG AA, 4.5:1) is a finding at Gate 2, not
noise. `export` writes Tailwind or CSS tokens from the file; `diff` shows
token changes between two versions.

**New project:** write it while the project is designed, before the first
screen. Offer two or
three directions in one question, each a line of identity plus its shape,
type and accent. The user picks.

## Generic tells: a detection list, not a ban list

Banning a tell moves a model to the next default, so this list spots a
default nobody chose. A tell `DESIGN.md` chose on purpose is fine.
Swapping one tell for its second-order twin is not a fix.

- **First-order:** Tailwind/Bootstrap default hexes for status or accent;
  purple/indigo-to-blue gradients, gradient text; Inter, Roboto or a system
  stack nobody chose; `rounded-2xl` cards and pill buttons everywhere; large
  soft or coloured shadows, glassmorphism, aurora blobs; emoji as icons or
  nav markers; a centred hero with a badge above the H1; three identical
  icon-topped cards; stat-tile rows; cards with a coloured left border;
  presets named "Blue / Red / Green".
- **Second-order** (what a model reaches for once told to avoid the first):
  Space Grotesk, Instrument Serif or Geist; cream with terracotta, near-black
  with acid green; all-caps monospace labels; 01/02/03 numbering; one italic
  serif accent word in a heading; fake window dots.

## While building

- Tokens only: no hex, raw colour or one-off shadow/radius in components.
- A pattern `DESIGN.md` doesn't cover: add it there in the same change and
  name it at commit approval. No separate question.
- Companion apps (a desktop or mobile client of the same product) take their
  tokens from the same `DESIGN.md`. A token change lands in all of them in one
  commit, or the gap goes on the handoff.
- **Screenshot loop** after a visual change: screenshot the touched screen,
  list how it differs from `DESIGN.md`, fix the biggest difference, and
  repeat. Stop after three rounds; gains level off after that.

## Audit: an existing app

Runs when the user asks, or once per UI project with no `DESIGN.md`: offer it
at the first UI change and record the answer on the `Standards:` row. A
decline is on the record and isn't offered again.

1. **Derive `DESIGN.md` from the code** as it is today: the tokens, fonts,
   radii and shadows in use. Lint it.
2. **Scan** styles, templates and UI code: palette values that match a
   framework's defaults, `linear-`/`radial-gradient`, `backdrop-filter`,
   `box-shadow` blur over ~4px, radii above the chosen maximum, font stacks,
   emoji in markup, and raw colours outside the token file. Then look for the
   layout tells above, which no grep finds.
3. **Contrast:** lint with every state and theme declared, as above. Report
   anything under 4.5:1 (3:1 for large text and UI borders).
4. **Screenshots:** the visual pass (`GATE_REFERENCE.md`, Gate 2) before and
   after, shown as side-by-side sheets.
5. **Report** a table (tell, where, replacement), then fix in two commits:
   `DESIGN.md` plus tokens first, components second. Anything only checkable
   on another OS goes on the handoff. **When the audit leads to a redesign,
   the table is evidence, not the plan:** offer two or three directions from
   the product's own identity, as for a new project, and mock one before
   fixing tells. The same UI with its tells removed is still generic.

A third-party scanner (e.g. a design-audit skill) can be offered as a second
opinion, never required and never vendored into the project.
