# Connecting things_done to the website

Papers, software and datasets on the website come from the
[things_done](https://github.com/guijacquemet/things_done) ledger. Every time
the ledger changes, things_done pushes the public part of it to this
repository (`data/things_done/`) and the website rebuilds itself.

```
things_done (private)                    CellMigrationLab/website (public)
ledger/publications/*.yaml  ─┐
ledger/registries/software   ├─ update-website.yml ─▶ data/things_done/*.yaml ─▶ publish.yml ─▶ cellmig.org
ledger/registries/datasets  ─┘   (runs scripts/sync_things_done.py)
```

Only public fields are copied: title, authors, venue, year, DOI, abstract,
open-access status, links between preprints and journal versions, whether
Guillaume is corresponding author, and the software/dataset descriptions and links. Supervision, roles, notes and
everything else in the ledger is never read. The website never gets access to
the private repository: the token below only allows things_done to *write* to
this website repository.

## Setup (once, about 5 minutes)

1. **Create a token.** GitHub → your avatar → Settings → Developer settings →
   Personal access tokens → Fine-grained tokens → *Generate new token*.
   - Resource owner: **CellMigrationLab** (the organisation may need to allow
     fine-grained tokens: Organisation settings → Personal access tokens).
   - Repository access: *Only select repositories* → **CellMigrationLab/website**.
   - Permissions: **Contents: Read and write**. Nothing else.
   - Expiration: up to one year (GitHub emails you before it expires).
2. **Store it in things_done.** things_done → Settings → Secrets and variables →
   Actions → *New repository secret*: name `WEBSITE_TOKEN`, value = the token.
3. **Add the workflow.** Copy [`update-website.yml`](update-website.yml) to
   `.github/workflows/update-website.yml` in things_done and commit it.
4. **Test it.** things_done → Actions → *Update lab website* → *Run workflow*.
   A commit "Update publications, software and datasets from things_done"
   appears here when something changed; the site is rebuilt a minute later.

## When does the website update?

- on every push to things_done that changes publications, software or datasets
  (including merged ORCID pull requests),
- after the ledger's own cleanup workflow (its commits do not trigger other
  workflows),
- once a day as a safety net,
- or by hand (*Run workflow*).

## What the website does with the ledger

- **Publications** and **Latest papers**: every record; preprints are folded into
  their journal version when `related_dois` links them.
- **Featured research** (home page, `/featured-research/` and `/portfolio/…`
  pages): every record where `me.corresponding_author` is true (on the paper
  or its preprint). Title, authors, journal and abstract come from the record;
  pictures come from `data/featured.yaml` in the website repository.
- **Preprints and journal versions** are paired using `related_dois` and the
  ledger's own crosswalk report (confident matches only), so each paper appears
  once.
- **From preprint to paper**: the lag between each linked preprint and its
  journal version. The sync looks up exact dates from the DOIs once and caches
  them in `data/things_done/dates.yaml`; an `issued_date: YYYY-MM-DD` on a
  record takes precedence.
- **Collaborators**: co-authors with three or more joint papers, with their
  institution and country from OpenAlex (cached in
  `data/things_done/authors.yaml`). Lab members are excluded.

## Worth adding to the ledger

| Add | Effect on the website |
| --- | --- |
| `me.corresponding_author: true` (already recorded) | the paper appears in Featured research, with its own page |
| `related_dois` between every preprint and its journal version | the website already uses the crosswalk report; explicit links make pairing certain |
| `related_publication_dois` on software and datasets | the paper's page lists its code and data |
| `issued_date` (optional) | exact dates without an online lookup |

## Choosing what appears where

| On the website | Comes from | Edit |
| --- | --- | --- |
| Publications page, "Latest papers" on the home page | `ledger/publications/*.yaml` | things_done |
| Featured research: which papers, titles, abstracts | ledger (`me.corresponding_author`) | things_done |
| Featured research: pictures | `data/featured.yaml` | this repository |
| Software page: which projects, names, years, GitHub, paper DOI | `ledger/registries/software.yaml` | things_done |
| Software page: colours, pictures, longer text | `data/software.yaml` | this repository |
| Datasets page | `ledger/registries/datasets.yaml` | things_done |

Adding `related_publication_dois` to software and datasets in the ledger links
them to their paper: the paper's featured research page then lists the code
and data automatically.

To refresh by hand from a local checkout:
`python scripts/sync_things_done.py --ledger ../things_done`
