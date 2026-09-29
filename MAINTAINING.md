# Keeping the website up to date

What happens by itself, and what needs a person. Facts (papers, people,
grants, software, datasets) live in the
[things_done](https://github.com/guijacquemet/things_done) ledger; how they
look (pictures, texts, logos) lives here. Details of each file are in the
[README](README.md) and in [integrations/things_done](integrations/things_done/README.md).

## Automatic: nothing to do

**Publishing.** Every commit to `main` of this repository rebuilds and
publishes the site (GitHub Pages, about a minute). A pull request builds a
preview you can download from its *Checks* tab; it does not publish anything.

**Ledger → website.** things_done's *Update lab website* action validates the
ledger, copies its public part into `data/things_done/` and commits it here
("Update data from things_done"), which publishes the site. It runs:
- after every change to the ledger files the website uses (publications,
  software, datasets, grants, lab members, profile, roles, talks);
- after the ledger's own automation succeeds (below);
- every day at 04:17 UTC.

**Inside things_done, after a change to the publications:** duplicates are
removed and preprints paired with their journal versions (*Ledger Cleanup and
Preprint Links*); the preprint-to-paper lag and the co-authors' countries are
recomputed (also every Monday); the reports and CV list are regenerated.

**Citation numbers** (Lab in numbers) are refreshed from Google Scholar on the
1st of each month (*Diagnose Scholar Fetch*). Scholar sometimes blocks GitHub:
the run is then red, the site keeps the last numbers and their date, and you
can re-run it later (*Run workflow*, *refresh_cache* `true`).

**Built from the ledger at every build (no file to touch):**

| On the website | Comes from |
| --- | --- |
| Publications, with preprint/journal pairs and Open access badges | ledger publications |
| Which papers are Featured research (home page and `/featured-research/`) | papers where Guillaume is corresponding author |
| Lab in numbers: papers, preprint lag, top collaborators, map, co-author cloud | ledger publications and reports |
| Datasets page, software list, paper links to code and data | ledger registries |
| Members and alumni, roles, member counts | ledger roster (`lab_members.yaml`) |
| Group leader profile (About us), footer affiliations, current research support | ledger profile, roles, affiliations and grants |
| RSS feed, sitemap, search-engine and LLM metadata, resized images | the build |

## Manual, in things_done (facts)

| When | Do |
| --- | --- |
| **A new paper or preprint** | Run the *Fetch publications from ORCID* action and review and merge the pull request it opens (or add one DOI with `python tools/fetch_publications.py --doi …`). Then check what the import cannot know: `status` (preprint, in press), and `me.corresponding_author` for papers where you are corresponding author, since that is what makes a paper Featured research. The date, open-access status and author spellings are filled in by the import. |
| **Someone joins, changes role or leaves** | `ledger/profile/lab_members.yaml`: add them with a `role`; move the old role to `previous_roles`; set `status: alumni` when they leave. |
| **A new grant, or one starts or ends** | `ledger/registries/grants.yaml` (`status`, dates, funders, programme). A new funder or programme also needs its logo here (below). |
| **New software or dataset** | `ledger/registries/software.yaml` or `datasets.yaml`. Each needs at least one paper in `related_publication_dois` (a preprint DOI is fine: the site links the journal version once it is in the ledger); software also needs `github_repo_url` and a `summary`, the text shown on the Software page. |
| **A new affiliation, role or degree** | `ledger/profile/` or `ledger/roles/`. A new affiliation also needs its logo here (below). |
| **The same co-author under two spellings** | `ledger/profile/coauthor_names.yaml` (`keep` / `replace`), then `python tools/coauthor_names.py --apply`. |
| **A preprint not paired with its journal version** | `report/config/preprint_links_overrides.yaml`. |

## Manual, in this repository (presentation)

Some of these stop the build until they are done. The site then stays online
but does not update, and the failed run names the file to fix (below).

| When | Do | Stops the build? |
| --- | --- | --- |
| **A new corresponding-author paper** reaches the site | Add it to `data/featured.yaml` with `area: biology` or `area: methods`, a picture (`image:`) and, if it has no abstract, a `summary:`; or `hide: true` to leave it out. | Yes, without an `area` |
| **A new member** | Photo `data/photos/<id>.jpg` (their roster id without `member-`); optional links and one-liner in `data/members/<id>.yaml`. Members can send these with the *Lab member profile* issue form. | No: initials are shown until there is a photo |
| **A new software project** | Nothing, when its paper is Featured research with a picture: the tool shows that picture. Otherwise a picture or video (and `fit`, extra `links`) in `data/software.yaml`, by its ledger `id`. Its name, text and links come from the ledger. | No: without a picture it shows as a text-only tile |
| **A new funder, programme or affiliation** | Its logo and link in `data/site.yaml` (`funding`, `programmes` or `affiliations`). | Yes |
| **Any new image** (gallery, research, featured, software, pages) | An entry in `data/media.yaml` with its rights and creators. | Yes |
| **Research themes and selected papers** | `data/research.yaml`. | No |
| **Join us, About us, Licensing** | `content/join-us.md`, `about-us.md`, `licensing.md`. | No |
| **Gallery, online talks, link previews** | `data/gallery.yaml` (pictures, journal covers, and looping videos: a GIF with an MP4 twin, with a caption), `data/talks.yaml`, `data/previews.yaml`. | Yes, for a video without a caption |

## Now and then

- **Look for red runs** in the *Actions* tab of both repositories. A red
  *Update lab website* run in things_done means the website is not getting new
  data; a red *Build and publish site* run here means the site is not updating.
- **Renew the `WEBSITE_TOKEN`** before it expires. GitHub emails a reminder;
  create a new token as in [integrations/things_done](integrations/things_done/README.md#setup-once-about-5-minutes),
  replace the secret in things_done and run *Update lab website* to test it.
  Until then every sync run fails.
- **Open access:** `python tools/check_open_access.py` in things_done re-checks
  every paper against OpenAlex; a green copy added later (in a repository, say)
  turns up there. `--apply` writes the changes that need no review.

## When the build stops

The message names the file. The common ones:

| Message says | Fix |
| --- | --- |
| `data/featured.yaml: give these featured papers an area` | add `area:` for the new paper |
| `data/site.yaml funding` / `programmes` / `affiliations`: add an entry | add the logo entry for the new funder, programme or affiliation |
| `data/media.yaml: no rights entry for …` (or `add an entry … for`) | add the image's rights entry |
| `not corresponding-author papers in the ledger` | remove the entry from `data/featured.yaml` (or fix the ledger) |
| `no one with this id in the things_done roster` | a file in `data/members/` or `data/photos/` has a wrong or old id: rename or delete it |
| `re-run scripts/sync_things_done.py` | run *Update lab website* in things_done |
