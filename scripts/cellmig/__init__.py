"""Page generator for cellmig.org.

scripts/build_pages.py is the entry point; the modules here are:

  config      paths, constants, loading YAML, failing loudly
  text        small string helpers (escaping, Markdown, slugs)
  page        the Page class: one generated Markdown file
  images      thumbnails, <img>/<video> markup, click-to-load videos
  icons       inline SVG icons
  ledger      things_done data (publications, software, datasets, reports)
  people      the lab roster merged with website photos and links
  featured    featured research: corresponding-author papers + pictures
  components  HTML snippets shared by several pages (citations, cards, tiles)
  charts      SVG charts (papers per year, preprint lag)
  worldmap    SVG world map of co-author countries
  pages_*     one function per generated page
  site_files  footer partial and RSS feed
"""
