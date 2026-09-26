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
open-access status, links between preprints and journal versions, and the
software/dataset descriptions and links. Supervision, roles, notes and
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

## Choosing what appears where

| On the website | Comes from | Edit |
| --- | --- | --- |
| Publications page, "Latest papers" on the home page | `ledger/publications/*.yaml` | things_done |
| Citations on featured research pages | ledger, by DOI | `data/featured/*.yaml` lists the DOIs |
| Software page: which projects, names, years, GitHub, paper DOI | `ledger/registries/software.yaml` | things_done |
| Software page: colours, pictures, longer text | `data/software.yaml` | this repository |
| Datasets page | `ledger/registries/datasets.yaml` | things_done |

Adding `related_publication_dois` to software and datasets in the ledger links
them to their paper: the paper's featured research page then lists the code
and data automatically.

To refresh by hand from a local checkout:
`python scripts/sync_things_done.py --ledger ../things_done`
