# Cell Migration Lab website

Source of the Cell Migration Lab website, **https://cellmig.org** (preview:
https://cellmigrationlab.github.io/website/).

The site is built with [Zensical](https://zensical.org) (like the
[doctoral programme pages](https://github.com/AAUGS-DP-Biosciences-and-Drug-Research/Home))
from Markdown and YAML files. Every push to `main` rebuilds the site and
publishes it with GitHub Pages; pull requests get a downloadable preview.

**Papers, software and datasets update themselves** from the
[things_done](https://github.com/guijacquemet/things_done) ledger — see
[integrations/things_done](integrations/things_done/README.md).

## What to edit

Most pages are generated from the files in `data/`. Open the file on GitHub,
click the pencil, edit, commit. Every page on the website also has an edit
button (top right) that opens the right file.

| Page | Edit |
| --- | --- |
| Home (tagline, intro, images, logos, footer, contact) | `data/site.yaml` |
| Funding logos (home page) | which ones: things_done `ledger/registries/grants.yaml` (funders of active/awarded grants not yet ended); logo and link per ledger direct funder (`funders[].name`; co-funded grants have several) in `data/site.yaml` `funding`, `logo: null` for a text-only entry — the build stops if the two disagree |
| News (and the RSS feed) | automatic, from things_done: papers, preprints, keynotes, events, funding, positions and software since 2024 (`scripts/cellmig/news.py`) |
| Join us (recruitment) | `content/join-us.md` |
| Group leader profile (About us) | automatic, from things_done (`ledger/profile/`, `ledger/roles/`) |
| Affiliations (home page and footer) | which ones: things_done `ledger/profile/affiliations.yaml` (current = no end date, or one not yet passed); logo and link per ledger `id` in `data/site.yaml` `affiliations` — the build stops if the two disagree |
| Research | `data/research.yaml` |
| Featured research (8 newest on the home page, all on `/featured-research/`, one page each under `/portfolio/`) | automatic: every paper where Guillaume is corresponding author in things_done, and only those; pictures and page addresses in `data/featured.yaml` (`hide: true` to leave one out) |
| Publications, latest papers | automatic, from things_done |
| Lab in numbers (papers, citations, people, preprint lag, collaborators, map, co-author cloud) | automatic, from things_done |
| Software | automatic list from things_done; colours, pictures, texts in `data/software.yaml` |
| Datasets | automatic, from things_done; links at the top in `data/site.yaml` (`resources`) |
| Lab members and alumni (who, roles) | things_done `ledger/profile/lab_members.yaml`; photos in `data/photos/`, links in `data/members/<name>.yaml`, team photos in `data/team.yaml` |
| Gallery | `data/gallery.yaml` |
| Online talks | `data/talks.yaml` |
| About us | `content/about-us.md` |
| What a pasted link shows (title, sentence, picture) for every page | `data/previews.yaml` |
| Colours, fonts, layout | `docs/assets/stylesheets/cellmig.css` |

### Lab members

**Who is in the lab and their roles come from things_done**
(`ledger/profile/lab_members.yaml`): add a person there with their `role`
(and earlier roles in `previous_roles`), and set `status: alumni` when they
leave. Current members show their current role; alumni show all their
roles. No dates are shown. The website only adds the look:

- Photo: `data/photos/<name>.jpg` (file name = the person's name as in the
  roster, in lower case without accents and with hyphens, e.g. `ivan-hidalgo-cenalmor.jpg`),
  or `photo:` in `data/members/<name>.yaml` pointing to an image under `docs/`
  (one or the other, not both). Photos are cropped to a square automatically;
  without a photo the initials are shown.
- Optional `data/members/<name>.yaml` with links and a one-liner:

```yaml
orcid: 0000-0000-0000-0000     # also: email, github, bluesky, scholar, website
bio: Filopodia and cancer cell invasion
photo_position: center         # crop the photo from the centre instead of the top
now: Postdoc at …              # alumni: where they are now
```

Only the keys above are allowed, and every file in `data/members/` and
`data/photos/` must match someone in the roster: a typo or a leftover file
stops the build with a message instead of being silently ignored (after a
name change in the roster, rename the files too).

Members can send a photo and links with the **Lab member profile** issue form
linked at the bottom of the members page.

### Pictures

Pictures can go anywhere under `docs/` (e.g. `docs/assets/images/`); refer to
them by their path from `docs/`, e.g. `image: assets/images/new-figure.jpg`.
Large originals are fine: the build makes resized WebP copies. A `.gif` is
shown as a looping video when an `.mp4` of the same name exists in
`docs/assets/media/gif/` (much smaller than the GIF).

The files in `docs/wp-content/uploads/` come from the old WordPress site and
keep their old addresses, so existing links to them keep working.

## Build locally

```bash
pip install -r requirements.txt
python scripts/build_pages.py   # generates the pages from data/
zensical serve                  # http://localhost:8000, reloads on changes
# the publish workflow then runs: zensical build && python scripts/write_sitemap.py
```

Generated pages (listed in `.gitignore`) are rebuilt every time; do not edit
them, edit `data/` instead.

Tests (also run by the publish workflow):

```bash
PYTHONPATH=scripts python -m unittest discover -s tests
```

## Hosting and the cellmig.org domain

1. **Turn on GitHub Pages:** repository Settings → Pages → Source: **GitHub
   Actions**. The site is then live at https://cellmigrationlab.github.io/website/.
2. **Point cellmig.org here** (when the new site is ready):
   - in `mkdocs.yml`, set `site_url: https://cellmig.org/` (canonical links,
     sitemap and robots.txt follow);
   - Settings → Pages → Custom domain: `cellmig.org`; after the check, tick
     *Enforce HTTPS*;
   - verify the domain for the organisation (Organisation settings → Pages)
     to prevent takeovers;
   - DNS at WordPress.com (the registrar): replace the two `A` records of
     `cellmig.org` with GitHub's `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`, and set `www` → `CNAME
     cellmigrationlab.github.io`. **Keep the `MX` records** (Google
     Workspace email).
3. Old addresses keep working: every WordPress page (`/lab-members/`,
   `/software/`, `/portfolio/<name>/`, images under `/wp-content/uploads/`,
   the RSS feed at `/feed/`) exists at the same path. Removed pages (the old
   news posts, archives) redirect (see `redirects` in `mkdocs.yml`).

## How it fits together

```
data/*.yaml ──┐
data/things_done/*.yaml ◀── things_done (automatic)
              ├─ scripts/build_pages.py ─▶ docs/*.md ─┐
content/*.md (hand-written pages) ────────────────────┼─ zensical build ─▶ site/ ─▶ GitHub Pages
overrides/ (layout), docs/assets/ (CSS, JS, fonts) ───┘
```

- `scripts/build_pages.py` — turns `data/` into pages, makes thumbnails, the
  RSS feed and the footer. The code lives in `scripts/cellmig/`, one module
  per concern (see its `__init__.py` for a map; one module per page family).
  There are no silent fallbacks: a missing file, a DOI that is not in the
  ledger, an unknown key or colour, or a picture that does not exist stops
  the build with a message naming the file to fix.
- `scripts/write_sitemap.py` — after `zensical build`, writes `site/sitemap.xml`
  (every page, including the featured-paper pages that are not in the menu)
  and `site/robots.txt` pointing to it, both from `site_url` in `mkdocs.yml`.
- For search engines and LLMs the build also writes, from the same data:
  schema.org JSON-LD (the lab and its leader on every page; each featured
  paper as a ScholarlyArticle; publications, software, datasets and people
  as lists), Google Scholar `citation_*` tags on paper pages, and
  `/llms.txt` + `/llms-full.txt` (the whole site as Markdown).
- `tests/` — unit tests for the generator.
- `scripts/sync_things_done.py` — copies the public part of the ledger into
  `data/things_done/` (run by things_done after each update).
- `overrides/` — page layout (header, footer, home page).
- `.github/workflows/publish.yml` — build and deploy.

## Credits

Fonts: [Inter](https://github.com/rsms/inter) and
[Bodoni Moda](https://github.com/indestructible-type/Bodoni), SIL Open Font
License, self-hosted (no requests to Google). Images © Cell Migration Lab
unless stated otherwise.
