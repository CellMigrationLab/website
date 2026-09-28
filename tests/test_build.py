"""Unit tests for the page generator (scripts/cellmig/).

    PYTHONPATH=scripts python -m unittest discover -s tests
"""

import unittest
from datetime import date
from unittest.mock import patch

from cellmig import featured, ledger
from cellmig.charts import lag_section
from cellmig.components import badges, logo_row, support_row
from cellmig.pages_papers import publication_filter_kind
from cellmig.page import Page
from cellmig.people import is_lab_member, lab_names
from cellmig.profile import month_year, recent_talks
from cellmig.text import fmt, is_external, normalize_name, plural, slugify
from cellmig.worldmap import color


def fake_ledger(pubs):
    """A Ledger over in-memory records (skips reading data/things_done/)."""
    led = object.__new__(ledger.Ledger)
    led.pubs = pubs
    led.by_doi = {p["doi"].lower(): p for p in pubs}
    led.software, led.datasets, led.affiliations = [], [], []
    led.dates = {p["doi"].lower(): p["publication_date"] for p in pubs if len(p["publication_date"]) > 4}
    return led


def pub(doi, year, status="published", title="T", **extra):
    """A publication with the fields things_done requires (and venue, which the site requires)."""
    return {"doi": doi, "year": year, "publication_date": str(year), "status": status, "title": title,
            "authors": ["A. Author"],
            "venue": "bioRxiv" if status == "preprint" else "J. Cell Sci.", "abstract": f"Abstract of {title}.", **extra}


PRE = pub("10.1101/pre", 2023, "preprint", "Pre", related_dois=["10.1/J"])
JOURNAL = pub("10.1/j", 2024, "published", "Journal", related_dois=["10.1101/pre"])


class TextTests(unittest.TestCase):
    def test_long_date(self):
        from cellmig.text import long_date
        self.assertEqual(long_date("2026-09-21T04:17:00+00:00"), "21 September 2026")

    def test_slugify_and_names(self):
        self.assertEqual(slugify("Iván Hidalgo Cenalmor"), "ivan-hidalgo-cenalmor")
        self.assertEqual(normalize_name("Joanna Pylvänäinen"), normalize_name("joanna pylvanainen"))

    def test_small_helpers(self):
        self.assertEqual(fmt(8562), "8 562")
        self.assertEqual(plural(1, "paper"), "1 paper")
        self.assertEqual(plural(2, "paper"), "2 papers")
        self.assertTrue(is_external("mailto:x@y.z"))
        self.assertTrue(is_external("#top"))
        self.assertFalse(is_external("software/"))


class PublicationSemanticsTests(unittest.TestCase):
    def test_oa_badge_requires_explicit_open_state(self):
        for state in ("gold", "diamond", "hybrid", "green", "bronze"):
            with self.subTest(state=state):
                self.assertIn("Open access", badges({"status": "published", "open_access_status": state}))
        for state in (None, "closed", "unknown"):
            with self.subTest(state=state):
                self.assertNotIn("Open access", badges({"status": "published", "open_access_status": state}))

    def test_peer_review_filter_uses_explicit_flag(self):
        self.assertEqual(publication_filter_kind({"status": "published", "peer_reviewed": True}), "peer-reviewed")
        self.assertEqual(publication_filter_kind({"status": "in_press", "peer_reviewed": True}), "peer-reviewed")
        self.assertEqual(publication_filter_kind({"status": "published", "peer_reviewed": False}), "other")
        self.assertEqual(publication_filter_kind({"status": "preprint", "peer_reviewed": False}), "preprint")


class PageTests(unittest.TestCase):
    def test_links_relative_to_file_and_to_final_url(self):
        p = Page("portfolio/cdm.md")
        self.assertEqual(p.u("software/"), "../software/")                   # href/src: from the .md file
        self.assertEqual(p.u("assets/a.jpg", final_url=True), "../../assets/a.jpg")  # srcset: from /portfolio/cdm/
        self.assertEqual(Page("index.md").u("", final_url=True), "")
        self.assertEqual(Page("index.md").u("/"), "./")

    def test_fix_links_leaves_external_and_relative_links(self):
        p = Page("research.md")
        html = '<a href="https://x.org"></a><a href="../y/"></a><img src="a.png" srcset="a.png 1x, b.png 2x">'
        self.assertEqual(p.fix_links(html),   # external kept (and opens in a new tab, #16), relative kept
                         '<a href="https://x.org" target="_blank" rel="noopener"></a><a href="../y/"></a>'
                         '<img src="a.png" srcset="../a.png 1x, ../b.png 2x">')


class LedgerTests(unittest.TestCase):
    def test_preprint_folded_into_journal_version(self):
        led = fake_ledger([JOURNAL, PRE])
        self.assertEqual([r["doi"] for r in led.grouped()], ["10.1/j"])
        self.assertIs(led.published_version(PRE), JOURNAL)
        self.assertIs(led.preprint_of(JOURNAL), PRE)
        self.assertEqual(led.family_dois("10.1101/PRE"), {"10.1101/pre", "10.1/j"})

    def test_standalone_preprint_is_kept(self):
        led = fake_ledger([JOURNAL, dict(PRE, standalone=True)])
        self.assertEqual(len(led.grouped()), 2)

    def test_unknown_doi_stops_the_build(self):
        with self.assertRaises(SystemExit):
            fake_ledger([JOURNAL]).require("10.9/missing", "test")

    def test_software_id_not_in_ledger_stops_the_build(self):
        led = fake_ledger([])
        led.software = [{"id": "trackmate", "title": "TrackMate"}]
        with patch.object(ledger, "load", return_value=[{"id": "trakmate", "image": "x.png"}]):
            with self.assertRaises(SystemExit):
                ledger.software_list(led)

    SOFTWARE = {"id": "a", "title": "A", "start_date": "2020-01-01", "github_repo_url": "https://github.com/x/a",
                "description": "A tool.", "summary": "A longer text.", "related_publication_dois": ["10.1101/pre"]}

    def test_software_facts_from_the_ledger_look_from_the_website(self):
        """The paper link follows a preprint to its journal version."""
        led = fake_ledger([PRE, JOURNAL])
        led.software = [self.SOFTWARE]
        with patch.object(ledger, "load", return_value=[{"id": "a", "fit": "contain"}]):
            [s] = ledger.software_list(led)
        self.assertEqual((s["title"], s["year"], s["text"], s["fit"]), ("A", 2020, "A longer text.", "contain"))
        self.assertEqual([r["doi"] for r in s["papers"]], ["10.1/j"])

    def test_software_facts_on_the_website_stop_the_build(self):
        led = fake_ledger([PRE, JOURNAL])
        led.software = [self.SOFTWARE]
        for entry in ({"id": "a", "text": "Old text"}, {"id": "a", "paper": "https://x"}, {"title": "Web only"}):
            with patch.object(ledger, "load", return_value=[entry]), self.assertRaises(SystemExit):
                ledger.software_list(led)
        led.software = [dict(self.SOFTWARE, related_publication_dois=[])]
        with patch.object(ledger, "load", return_value=[]), self.assertRaises(SystemExit):
            ledger.software_list(led)

    def test_software_takes_its_papers_featured_picture(self):
        """A tool linked to a preprint finds the picture of the featured journal version."""
        from cellmig.featured import paper_picture
        led = fake_ledger([PRE, JOURNAL])
        stories = [{"papers": ["10.1/j"], "image": "assets/images/j.png", "fit": "contain"}]
        self.assertEqual(paper_picture(["10.1101/pre"], stories, led), ("assets/images/j.png", "contain"))
        self.assertIsNone(paper_picture(["10.1101/pre"], [dict(stories[0], image=None)], led))

    def test_short_paper_references_share_one_form(self):
        from cellmig.components import paper_link, paper_ref
        rec = pub("10.1101/x", 2025, "preprint", "X", venue="bioRxiv", open_access_status="green")
        self.assertEqual(paper_link(rec), '<a href="https://doi.org/10.1101/x"><em class="cm-venue">bioRxiv</em> · 2025</a>'
                         '<span class="cm-badge cm-badge--oa" title="Open access">Open access</span>')
        self.assertIn('<span class="cm-ref__meta"><em class="cm-venue">bioRxiv</em> · 2025</span>', paper_ref(rec))
        self.assertNotIn("Preprint", paper_ref(rec))   # the venue says it; only the full citation has the badge

    def test_dataset_search_covers_its_papers(self):
        from cellmig.pages_content import _dataset
        led = fake_ledger([PRE, JOURNAL])
        html = _dataset({"title": "Cells", "description": "Movies.", "start_date": "2024", "repository_url": "https://z/1",
                         "related_publication_dois": ["10.1101/pre"]}, led)
        self.assertIn('data-search="cells movies.', html)
        self.assertIn("journal a. author j. cell sci. 2024 10.1/j", html)   # the journal version's title, authors, venue

    def test_dataset_modality_and_model_scores(self):
        from cellmig.pages_content import _dataset
        html = _dataset({"title": "M", "description": "A model.", "start_date": "2024", "repository_url": "https://z/1",
                         "imaging_modality": "brightfield", "model_metrics": {"IoU": 0.95, "F1": 0.969},
                         "related_publication_dois": ["10.1/j"]}, fake_ledger([JOURNAL]))
        self.assertIn("2024 · Brightfield · IoU 0.950, F1 0.969 · Paper:", html)

    def test_dataset_papers_follow_preprints_and_are_required(self):
        led = fake_ledger([PRE, JOURNAL])
        self.assertEqual([r["doi"] for r in led.dataset_papers({"title": "D", "related_publication_dois": ["10.1101/pre", "10.1/j"]})],
                         ["10.1/j"])
        with self.assertRaises(SystemExit):
            led.dataset_papers({"title": "D"})


class FeaturedTests(unittest.TestCase):
    def run_featured(self, pubs, entries):
        with patch.object(featured, "load", return_value=entries):
            return featured.load_featured(fake_ledger(pubs))

    def test_corresponding_author_papers_are_featured_newest_first(self):
        a = pub("10.1/a", 2024, "published", "A", corresponding=True)
        b = pub("10.1/b", 2024, "published", "B", corresponding=True, publication_date="2024-03-01")
        c = pub("10.1/c", 2025, "published", "C", corresponding=True)
        d = pub("10.1/d", 2026, "published", "D")   # not corresponding
        entries = [{"doi": "10.1/c", "image": "c.png", "area": "methods"},
                   {"doi": "10.1/a", "area": "biology"}, {"doi": "10.1/b", "area": "biology"}]
        items = self.run_featured([a, b, c, d], entries)
        # 2025 first; in 2024 the dated paper comes before the undated one
        self.assertEqual([i["title"] for i in items], ["C", "B", "A"])
        self.assertEqual(items[0]["image"], "c.png")
        self.assertIsNone(items[2]["date"])        # no made-up dates

    def test_hidden_paper_is_left_out(self):
        a = pub("10.1/a", 2024, "published", "A", corresponding=True)
        self.assertEqual(self.run_featured([a], [{"doi": "10.1/a", "hide": True}]), [])

    def test_every_featured_paper_needs_an_area(self):
        a = pub("10.1/a", 2024, "published", "A", corresponding=True)
        for entries in ([], [{"doi": "10.1/a", "area": "chemistry"}]):   # no entry; unknown area
            with self.subTest(entries=entries), self.assertRaises(SystemExit):
                self.run_featured([a], entries)

    def test_bad_entries_stop_the_build(self):
        a = pub("10.1/a", 2024, "published", "A", corresponding=True)
        b = pub("10.1/b", 2024, "published", "B")
        for entry in ({"doi": "10.1/a", "imgae": "x.png"},          # typo in a key
                      {"doi": "10.9/missing"},                      # not in the ledger
                      {"doi": "10.1/a", "also": ["10.9/missing"]},  # `also` not in the ledger
                      {"doi": "10.1/b", "image": "b.png"}):         # not corresponding-author
            with self.subTest(entry=entry), self.assertRaises(SystemExit):
                self.run_featured([a, b], [entry])


def entry(key, field="id", **extra):
    """A data/site.yaml affiliation or funding entry."""
    return {field: key, "name": key.upper(), "url": f"https://{key}.example/", "logo": f"{key}.png", **extra}


class AffiliationTests(unittest.TestCase):
    def setUp(self):
        self.led = fake_ledger([])
        self.led.affiliations = [{"id": "aau", "organization": "Åbo Akademi", "title": "Professor"},
                                 {"id": "fci", "organization": "Finnish Cancer Institute", "title": "Research Professor"}]

    def test_merged_in_website_order(self):
        out = ledger.affiliation_list([entry("fci", relation="leader"), entry("aau", relation="parent")], self.led)
        self.assertEqual([a["name"] for a in out], ["FCI", "AAU"])
        self.assertEqual(out[0]["title"], "Research Professor")

    def test_missing_entries_stop_the_build(self):
        for presentation in ([entry("aau", relation="parent")],                                  # fci has no entry
                             [entry("aau", relation="boss"), entry("fci", relation="leader")],   # bad relation
                             [{"id": "aau", "relation": "parent"}, entry("fci", relation="leader")]):  # no name/url/logo
            with self.subTest(presentation=presentation), self.assertRaises(SystemExit):
                ledger.affiliation_list(presentation, self.led)

    def test_an_entry_that_is_no_longer_current_is_left_out(self):
        with patch("builtins.print") as warn:
            out = ledger.affiliation_list([entry("aau", relation="parent"), entry("fci", relation="leader"),
                                           entry("old", relation="member")], self.led)
        self.assertEqual([a["id"] for a in out], ["aau", "fci"])
        self.assertIn("no longer current", warn.call_args[0][0])


class FundingTests(unittest.TestCase):
    def setUp(self):
        self.led = fake_ledger([])
        self.led.grants = [
            {"title": "CoE", "funders": ["RCF"], "program": "CoE programme", "current": True},
            {"title": "Project", "funders": ["RCF"], "current": True},
            {"title": "EOSS", "funders": ["Wellcome", "CZI"], "program": "EOSS 6",
             "program_cofunders": ["Kavli"], "current": True},                        # one joint award
            {"title": "Old", "funders": ["EMBO"], "current": False}]
        self.funders = [entry(n, "funder", logo=None) for n in ("RCF", "Wellcome", "CZI")]   # text: no image files
        self.programmes = [entry("CoE programme", "program", logo=None), entry("EOSS 6", "program", logo=None)]

    def test_grouped_by_meaning(self):
        groups = ledger.support_list(self.funders, self.programmes, self.led)
        rcf, eoss = groups
        self.assertEqual([f["funder"] for f in rcf["logos"]], ["RCF"])                # RCF once,
        self.assertEqual([p["program"] for p in rcf["programmes"]], ["CoE programme"])  # CoE beneath it
        self.assertEqual([f["funder"] for f in eoss["logos"]], ["Wellcome", "CZI"])   # the joint award once,
        self.assertEqual(eoss["title"]["program"], "EOSS 6")                         # under its programme,
        self.assertEqual(eoss["cofunders"], ["Kavli"])                               # co-funder named

    def test_one_row_of_logos(self):
        """Funders, then their programmes' scheme mark and logo; programmes without a logo are not shown."""
        self.programmes[0] = {**self.programmes[0], "logo": None,
                              "scheme": {"name": "COE MARK", "url": "https://coe.example/", "logo": None}}
        html = support_row(ledger.support_list(self.funders, self.programmes, self.led))
        names = [n for n in ("RCF", "COE MARK", "CoE programme".upper(), "WELLCOME", "CZI") if n in html]
        self.assertEqual(names, ["RCF", "COE MARK", "WELLCOME", "CZI"])
        self.assertEqual([html.index(n) for n in names], sorted(html.index(n) for n in names))
        self.assertEqual(html.count("<li>"), 4)

    def test_hidden_funder_is_left_out_by_choice(self):
        self.led.grants.append({"title": "Pilot", "funders": ["Pilot"], "current": True})
        with patch("builtins.print") as warn:
            groups = ledger.support_list(self.funders + [entry("Pilot", "funder", logo=None, hide=True)],
                                         self.programmes, self.led)
        self.assertNotIn("Pilot", [f["funder"] for g in groups for f in g["logos"]])
        warn.assert_not_called()                     # hidden, not stale
        with self.assertRaises(SystemExit):          # a scheme mark needs name, url and logo
            ledger.support_list(self.funders, [{**self.programmes[0], "scheme": {"name": "x"}}, self.programmes[1]],
                                self.led)

    def test_missing_entries_stop_the_build_and_stale_ones_are_left_out(self):
        with self.assertRaises(SystemExit):            # CZI (a co-funder) has no entry
            ledger.support_list(self.funders[:2], self.programmes, self.led)
        with self.assertRaises(SystemExit):            # the EOSS programme has no entry
            ledger.support_list(self.funders, self.programmes[:1], self.led)
        with patch("builtins.print") as warn:          # EMBO funds nothing current
            groups = ledger.support_list(self.funders + [entry("EMBO", "funder")], self.programmes, self.led)
        self.assertEqual(len(groups), 2)
        self.assertIn("no longer current", warn.call_args[0][0])

    def test_joint_award_without_programme_stops_the_build(self):
        self.led.grants[2] = {**self.led.grants[2], "program": None}
        with self.assertRaises(SystemExit):
            ledger.support_list(self.funders, self.programmes[:1], self.led)

    def test_logo_row_text_only_entry(self):
        html = logo_row([{"name": "ImmuDocs", "url": "https://example.org/", "logo": None}])
        self.assertIn('<span class="cm-logos__text">ImmuDocs</span>', html)
        self.assertNotIn("<img", html)


class TalkTests(unittest.TestCase):
    def test_month_year_and_recent_talks(self):
        self.assertEqual(month_year("2026-08"), "Aug 2026")
        self.assertEqual(month_year("2026-09-18"), "Sep 2026")
        led = fake_ledger([])
        led.talks = [{"date": "2026-09-01", "title": "New", "talk_kind": "keynote"},
                     {"date": "2026-06-01", "title": "Panel", "talk_kind": "panel_participation"},
                     {"date": "2020-01-01", "title": "Old", "talk_kind": "invited_talk"}]
        self.assertEqual([t["title"] for t in recent_talks(led, date(2026, 9, 27))], ["New"])


class PeopleTests(unittest.TestCase):
    def test_middle_initial_and_other_spellings(self):
        lab = lab_names([{"name": "Joanna Pylvänäinen"}, {"name": "Ana Popović", "also_known_as": ["Ana Gračanin"]}])
        self.assertTrue(is_lab_member("Joanna W. Pylvänäinen", lab))
        self.assertTrue(is_lab_member("Ana Gracanin", lab))
        self.assertFalse(is_lab_member("Ana Smith", lab))

    def test_highlighting_is_independent_of_dates(self):
        """#14: current members and alumni are highlighted on every paper (the
        highlight takes no date, so a paper's year cannot change it);
        unrelated co-authors are not."""
        import inspect
        from cellmig.components import author_list
        self.assertEqual(list(inspect.signature(author_list).parameters), ["authors", "lab"])
        lab = lab_names([{"name": "Now Member", "status": "current"}, {"name": "Past Member", "status": "alumni"}])
        html = author_list(["Past Member", "Now Member", "Other Person"], lab)
        self.assertIn('<span class="cm-author--lab">Past Member</span>', html)
        self.assertIn('<span class="cm-author--lab">Now Member</span>', html)
        self.assertNotIn('cm-author--lab">Other Person', html)


class ChartTests(unittest.TestCase):
    def test_map_colour_steps(self):
        self.assertEqual(color(1), "#e9ddf7")
        self.assertEqual(color(5), "#b48ae3")
        self.assertEqual(color(1000), "#4f2182")

    def test_lag_section_uses_the_ledger_summary_and_handles_negative_gaps(self):
        pair = {"published_doi": "10.1/j", "published_title": "T", "preprint_date": "2020-01-01",
                "published_date": "2020-03-01", "preprint_date_precision": "day", "published_date_precision": "day"}
        pairs = [dict(pair, gap_days=60), dict(pair, gap_days=-20, published_date="2019-12-12")]
        html = lag_section(pairs, {"pairs": 2, "median_months": 1.3})
        self.assertIn("<strong>1.3</strong>", html)
        self.assertIn(">-6</text>", html)          # axis extended left for the negative gap


if __name__ == "__main__":
    unittest.main()


class AuditRegressionTests(unittest.TestCase):
    """Behaviours fixed after the September 2026 audit."""

    def test_author_list_counts_the_hidden_names(self):
        from cellmig.components import AUTHOR_LIMIT, author_list
        names = [f"A{i}" for i in range(AUTHOR_LIMIT + 3)]
        out = author_list(names, set())
        self.assertIn("+3 more", out)                     # AUTHOR_LIMIT - 1 first ones and the last are shown
        self.assertEqual(out.count(","), AUTHOR_LIMIT)    # AUTHOR_LIMIT names + the "more" marker

    def test_unknown_dataset_type_stops_the_build(self):
        from cellmig.pages_content import _dataset_type
        self.assertEqual(_dataset_type({"title": "D", "dataset_type": "image"}), "Image data")
        with self.assertRaises(SystemExit):
            _dataset_type({"title": "D", "dataset_type": "video"})

    def test_grouped_is_newest_first_within_a_year(self):
        older, newer, undated = pub("10.1/o", 2026, title="A older"), pub("10.1/n", 2026, title="B newer"), pub("10.1/u", 2026, title="0 undated")
        month = pub("10.1/m", 2026, title="C month")
        led = fake_ledger([undated, older, month, newer])
        led.dates = {"10.1/o": "2026-02-01", "10.1/n": "2026-09-01", "10.1/m": "2026-05"}
        self.assertEqual([r["doi"] for r in led.grouped()], ["10.1/n", "10.1/m", "10.1/o", "10.1/u"])

    def test_thumbnails_are_remade_when_the_image_code_changes(self):
        """CI restores older thumbnail caches: the digest must cover the code (quality, resampling)."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from cellmig import images
        with TemporaryDirectory() as tmp, patch.object(images, "DOCS", Path(tmp)), \
                patch.object(images, "DIGESTS", Path(tmp) / "digests"):
            src, out = Path(tmp) / "a.png", Path(tmp) / "t" / "a.webp"
            src.write_bytes(b"image")
            out.parent.mkdir()
            out.write_bytes(b"thumb")
            images._made(out, src, "webp 400")
            self.assertFalse(images._stale(out, src, "webp 400"))
            self.assertTrue(images._stale(out, src, "webp 800"))
            with patch.object(images, "CODE", "other"):
                self.assertTrue(images._stale(out, src, "webp 400"))

    def test_title_slug_is_cut_at_a_word(self):
        slug = featured._title_slug("word " * 40)
        self.assertLessEqual(len(slug), featured.SLUG_LENGTH)
        self.assertFalse(slug.endswith("-"))

    def test_members_are_joined_by_their_things_done_id(self):
        """A corrected spelling of a name keeps the person's files and page anchor."""
        from cellmig import people
        roster = {"records": [{"id": "member-ivan-hidalgo-cenalmor", "name": "Iván Hidalgo-Cenalmor",
                               "role": "PhD student", "group": "phd", "status": "current"}]}
        with patch.object(people, "load", side_effect=lambda p: roster if p.name == "lab_members.yaml" else {}), \
                patch.object(people, "_publish_photo", return_value=None), patch.object(people, "_check_no_orphans"):
            self.assertEqual(people.load_members()[0]["slug"], "ivan-hidalgo-cenalmor")
            roster["records"][0].pop("id")
            with self.assertRaises(SystemExit):   # no id: stop, never fall back to the name
                people.load_members()

    def test_one_current_group_leader_with_an_email(self):
        from cellmig.people import leader
        pi = {"group": "pi", "status": "current", "slug": "g", "email": "g@x.fi"}
        self.assertIs(leader([pi, {"group": "phd", "status": "current"}]), pi)
        with self.assertRaises(SystemExit):
            leader([{**pi, "email": None}])
        with self.assertRaises(SystemExit):
            leader([{**pi, "status": "alumni"}])


class PublicCopyTests(unittest.TestCase):
    def test_internal_pipeline_names_stop_the_build(self):
        """#17: how the site is built is not shown to visitors."""
        from cellmig.page import check_public
        check_public("docs/x.md", "Citations and h-index from Google Scholar.")
        for text in ("Generated from our things_done ledger.", "From our Things Done activity ledger."):
            with self.subTest(text=text), self.assertRaises(SystemExit):
                check_public("docs/x.md", text)


class PreprintLinkTests(unittest.TestCase):
    def test_published_paper_links_its_preprint_without_looking_like_one(self):
        """#15: a journal paper with a preprint gets an action link, never the Preprint badge."""
        from cellmig.components import PREPRINT_LINK, citation
        led = fake_ledger([PRE, JOURNAL])
        html = citation(JOURNAL, set(), led)
        self.assertIn(f'<a href="https://doi.org/10.1101/pre">{PREPRINT_LINK}</a>', html)
        self.assertNotIn("cm-badge--preprint", html)
        self.assertNotIn(">Preprint<", html)
        self.assertIn("cm-badge--preprint", citation({**PRE, "related_dois": []}, set(), fake_ledger([PRE])))


class NewTabTests(unittest.TestCase):
    """#16: outbound web links open in a new tab; nothing else does."""

    def test_which_links(self):
        from cellmig.config import SITE_URL
        from cellmig.text import opens_new_tab
        from urllib.parse import urlsplit
        site = urlsplit(SITE_URL)
        for url in ("https://doi.org/10.1/x", "https://cellmig.org.example.org/", "https://notcellmig.org/",
                    f"https://{site.hostname}.example.org{site.path}", f"https://{site.hostname}/other-project/"):
            with self.subTest(url=url):
                self.assertTrue(opens_new_tab(url))
        for url in (f"{SITE_URL}news/", SITE_URL.rstrip("/"),
                    "https://cellmig.org/software/", "http://www.cellmig.org", "HTTPS://CELLMIG.ORG/x",
                    "software/", "#top", "mailto:a@b.fi", "../index.html"):
            with self.subTest(url=url):
                self.assertFalse(opens_new_tab(url))

    def test_html_and_markdown_rewriting(self):
        from cellmig.page import new_tab_links, new_tab_markdown
        self.assertEqual(new_tab_links('<a href="https://x.org/">x</a> <a href="news/">n</a> <a href="#y">y</a>'),
                         '<a href="https://x.org/" target="_blank" rel="noopener">x</a> <a href="news/">n</a> <a href="#y">y</a>')
        self.assertEqual(new_tab_links('<a href="https://x.org/" rel="me">x</a>'),
                         '<a href="https://x.org/" rel="me noopener" target="_blank">x</a>')
        self.assertEqual(new_tab_links('<a href="https://x.org/" target="_self">x</a>'),
                         '<a href="https://x.org/" target="_self">x</a>')                 # explicit target kept
        self.assertEqual(new_tab_markdown("[a](https://x.org/) [b](join-us.md) ![p](https://x.org/p.png) "
                                          "[c](https://y.org/){ .cm-button } [m](mailto:a@b.fi)"),
                         '[a](https://x.org/){ target="_blank" rel="noopener" } [b](join-us.md) '
                         '![p](https://x.org/p.png) [c](https://y.org/){ .cm-button target="_blank" rel="noopener" } '
                         '[m](mailto:a@b.fi)')


class LogoSizeTests(unittest.TestCase):
    def test_equal_area_and_no_distortion(self):
        """#20: wide and square logos get similar areas, within the slot, proportions kept."""
        from cellmig.components import LOGO_MAX_H, LOGO_MAX_W, logo_size
        for native in ((641, 174), (300, 300), (1200, 100), (100, 400)):
            with self.subTest(native=native):
                w, h = logo_size(*native)
                self.assertLessEqual(w, LOGO_MAX_W)
                self.assertLessEqual(h, LOGO_MAX_H)
                self.assertAlmostEqual(w / h, native[0] / native[1], delta=0.06 * native[0] / native[1])
        wide, square = logo_size(641, 174), logo_size(300, 300)
        self.assertLess(abs(wide[0] * wide[1] - square[0] * square[1]) / (square[0] * square[1]), 0.25)
        self.assertGreater(logo_size(300, 300, 1.2)[0], square[0])   # `scale` override


class WorldMapTests(unittest.TestCase):
    def test_view_box_hugs_the_drawn_countries(self):
        """#18: the viewBox is the drawn geometry plus a margin, not the full canvas."""
        import re
        from cellmig.worldmap import PAD, W, Bounds, world_map
        b = Bounds()
        for x, y in ((10, 20), (110, 70)):
            b.add(x, y)
        self.assertEqual(b.view_box(), f"{10 - PAD} {20 - PAD} {100 + 2 * PAD} {50 + 2 * PAD}")
        box = [float(v) for v in re.search(r'viewBox="([^"]+)"', world_map({"FI": 3, "SG": 1})).group(1).split()]
        self.assertLessEqual(box[2], W)          # no wider than the projection
        self.assertLess(box[3], box[2] / 2)      # Antarctica left out: much wider than tall


class GalleryTests(unittest.TestCase):
    def test_rows_of_equal_height_from_the_aspect_ratio(self):
        """Flex basis and growth are both proportional to width/height, so a row's pictures share one height."""
        from cellmig import pages_content
        with patch.object(pages_content, "image_size", return_value=(800, 400)):
            self.assertEqual(pages_content._justified("x.jpg"), f"flex: 200.0 1 {2 * pages_content.GALLERY_ROW:.2f}rem")
        with patch.object(pages_content, "image_size", return_value=None), self.assertRaises(SystemExit):
            pages_content._justified("x.svg")


class CloudTests(unittest.TestCase):
    def test_compact_size_range_keeps_the_encoding(self):
        """#19: the largest name stays modest, sizes still grow with joint papers."""
        from cellmig.pages_numbers import CLOUD_MAX, CLOUD_MIN, cloud_size
        self.assertLessEqual(CLOUD_MAX, 1.6)
        self.assertEqual(cloud_size(28, 28), CLOUD_MAX)
        self.assertLess(cloud_size(3, 28), cloud_size(10, 28))
        self.assertGreaterEqual(cloud_size(1, 28), CLOUD_MIN)

    def test_every_coauthor_is_in_the_cloud(self):
        from cellmig.pages_numbers import _cloud
        people = [{"name": f"Ann Author{i}", "papers": 1 + i % 3} for i in range(120)]
        html = _cloud(people, set())
        self.assertEqual(html.count("<span class=\"\" "), 120)
        self.assertIn("120 people have co-authored papers with us. The 80 who share more than one paper", html)
        self.assertIn("Show the 40 co-authors with one joint paper", html)


class ResearchThemeTests(unittest.TestCase):
    def test_selected_papers(self):
        """#24: preprints can be selected; a preprint and its journal version listed
        together stop the build; the journal version is shown. Papers carry the Open
        access badge, not a Preprint one (the venue says bioRxiv)."""
        from cellmig.pages_content import _theme
        led = fake_ledger([PRE, JOURNAL, pub("10.1101/solo", 2026, "preprint", "Solo preprint",
                                                     open_access_status="green")])
        html = _theme({"title": "T", "papers": ["10.1101/pre", "10.1101/solo"]}, led)
        self.assertIn("doi.org/10.1/j", html)                     # the preprint's journal version
        self.assertNotIn("cm-badge--preprint", html)
        self.assertEqual(html.count("cm-badge--oa"), 1)            # the journal version has no OA status here
        with self.assertRaises(SystemExit):
            _theme({"title": "T", "papers": ["10.1101/pre", "10.1/j"]}, led)


class VisualSystemTests(unittest.TestCase):
    def test_tiles_cycle_the_surfaces_and_fit_is_explicit(self):
        """Tiles take white, lavender, light and purple in turn; the picture side
        alternates; `fit: contain` is set in the data, not guessed from file names."""
        from cellmig.components import tile
        self.assertEqual([tile(i, "<img>", "t").split('"')[1] for i in range(5)],
                         ["cm-tile cm-tile--white", "cm-tile cm-tile--lavender cm-tile--right", "cm-tile cm-tile--light",
                          "cm-tile cm-tile--purple cm-tile--right", "cm-tile cm-tile--white"])
        self.assertIn("cm-tile--white cm-tile--right", tile(0, "<img>", "t", picture_right_first=True))
        self.assertIn("cm-fit-contain", tile(0, "<img>", "t", fit="contain"))
        with self.assertRaises(SystemExit):
            tile(0, "<img>", "t", fit="stretch")

    def test_data_files_set_no_tile_colour(self):
        from cellmig.pages_content import _no_colour
        with self.assertRaises(SystemExit):
            _no_colour({"title": "T", "color": "dark"}, "data/research.yaml")
