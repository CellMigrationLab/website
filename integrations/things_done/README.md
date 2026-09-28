# How things_done feeds the website

[things_done](https://github.com/guijacquemet/things_done) is the single source
of truth for papers, software, datasets and the lab's numbers. It computes
everything (preprint pairs, preprint-to-publication lag, co-author network and
countries, citation metrics) and commits the results; the website only copies
them. There is one place to maintain.

```
things_done (private)                                   CellMigrationLab/website (public)
ledger/publications/*.yaml             ──┐
  (and display_overrides.yaml)           │
ledger/registries/{software,datasets}  ──┤
ledger/profile/lab_members.yaml        ──┤
ledger/profile/affiliations.yaml       ──┤
ledger/profile/{person,education}.yaml ──┤
ledger/roles/*.yaml                    ──┤
ledger/activities/*/talks.yaml         ──┤
ledger/registries/grants.yaml          ──┤  (no amounts)
report/generated/publications/           │  update_website.yml runs
  preprint_publication_crosswalk.json  ──┼─ scripts/sync_things_done.py ─▶ data/things_done/*.yaml ─▶ site
  preprint_lag.json                    ──┤  (copy only, public fields)
  coauthor_network.json                ──┤
  coauthor_countries.json              ──┤
.cache/scholar_metrics.json            ──┘
```

Only public fields are copied: title, authors, venue, year, DOI, abstract,
peer review and open-access status, preprint/journal pairs, whether Guillaume
is corresponding author, software/dataset descriptions, co-author names,
joint-paper counts and countries, the public lab roster (names, roles in the
lab, current or alumni), Guillaume's current affiliations, roles and
education, talks, and grant titles, funder names, programmes and dates
(never amounts). Records marked `confidentiality: internal` or `confidential`
are never copied; supervision records, teaching, notes and
conflict-of-interest data are never read. Every input file is required: if one is missing the sync fails (and the
workflow run turns red) instead of quietly leaving part of the site stale. The website never gets access to the private repository: the token
below only lets things_done *write* to this repository.

## Setup (once, about 5 minutes)

The workflow is `.github/workflows/update_website.yml` in things_done. It fails
(red run, with an error pointing here) until the token exists, so a missing
token cannot leave the website silently stale.

1. **Create a token.** GitHub → your avatar → Settings → Developer settings →
   Personal access tokens → Fine-grained tokens → *Generate new token*.
   Resource owner **CellMigrationLab** (the organisation may need to allow
   fine-grained tokens), repository access *Only select repositories* →
   **CellMigrationLab/website**, permission **Contents: Read and write**.
2. **Store it in things_done.** Settings → Secrets and variables → Actions →
   *New repository secret*: `WEBSITE_TOKEN`.
3. **Test it.** things_done → Actions → *Update lab website* → *Run workflow*.

It then runs after every change to the ledger files the website uses
(publications, software, datasets, grants, profile, roles, talks), the
generated reports and the Scholar metrics, after the ledger's own automation
succeeds, and once a day. It validates the ledger before copying anything.

## Where each thing on the website comes from

| On the website | things_done source |
| --- | --- |
| Publications | `ledger/publications/`, paired by the crosswalk report; `display_overrides.yaml` `force_preprint_bucket` keeps a preprint listed on its own |
| Featured research (which papers, text) | publications with `me.corresponding_author: true`; pictures are in this repo's `data/featured.yaml` |
| Software (which projects, years, links) | `ledger/registries/software.yaml`; pictures/videos/long text in `data/software.yaml` here |
| Datasets | `ledger/registries/datasets.yaml` |
| Lab in numbers: papers, preprints | publications |
| Lab in numbers: citations, h-index | `.cache/scholar_metrics.json` (Diagnose Scholar Fetch action) |
| Lab in numbers: preprint-to-paper lag | `preprint_lag.json` (Analyze Preprint-to-Publication Lag action); the median shown is its `summary` |
| Lab in numbers: top collaborators, co-author cloud | `coauthor_network.json` |
| Lab in numbers: co-author map | `coauthor_countries.json` (Export Co-author Countries action) |
| Lab members, alumni and their roles, member counts | `ledger/profile/lab_members.yaml` (photos and links stay in this repo) |
| Current research support (home page) | funders and programmes (`program`, `program_cofunders`) of current grants in `ledger/registries/grants.yaml` (no amounts are copied) |
| Group leader profile (About us) | `ledger/profile/person.yaml`, `education.yaml`, current records of `ledger/roles/*.yaml` |
| Recent talks (llms-full.txt) | `ledger/activities/*/talks.yaml` |
| Affiliations (footer, structured data) | current records of `ledger/profile/affiliations.yaml` (logos and links in `data/site.yaml` here, by `id`) |

## Worth adding to the ledger

| Add | Effect on the website |
| --- | --- |
| `related_publication_dois` on software and datasets | the paper's page lists its code and data |
| `report/config/preprint_links_overrides.yaml` entries for missed pairs | the paper appears once, and the lag covers it |
| `video_url` on talks (future) | the Talks page could be generated from the ledger |
| the full issue date of each publication (`fetch_publications.py` already reads CSL `issued`, but keeps only the year) | featured papers ordered exactly within a year, and dated in the RSS feed (today only papers with a preprint have a known date) |

To refresh by hand from local checkouts:
`python scripts/sync_things_done.py --ledger ../things_done`
