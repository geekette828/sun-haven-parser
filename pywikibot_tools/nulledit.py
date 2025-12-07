import time
import pywikibot

# Config
CATEGORY = "Clothing"       # e.g. "Clothing" or "Category:Clothing" or None
TRANSCLUDES = None          # e.g. "Infobox item" or "Template:Infobox item" or None
COMMENT = "Null Edit"
DELAY = 0.5                 # seconds between edits
TEST_LIMIT = None           # e.g. 25 to test on first 25 pages

site = pywikibot.Site()

def norm_category(name: str) -> str:
    return name if name.lower().startswith("category:") else f"Category:{name}"

def norm_template(name: str) -> str:
    # Accept either "Template:Name" or bare "Name"
    return name if name.lower().startswith(("template:", "module:")) else f"Template:{name}"

# Collect pages iterator
if CATEGORY:
    cat_title = norm_category(CATEGORY)
    cat = pywikibot.Category(site, cat_title)
    # Prefer members() for broader compatibility; restrict to main namespace (0) and non-redirects.
    pages_iter = cat.members(namespaces=0, content=False)
elif TRANSCLUDES:
    tpl_title = norm_template(TRANSCLUDES)
    tpl_page = pywikibot.Page(site, tpl_title)
    pages_iter = tpl_page.getReferences(only_template_inclusion=True, namespaces=0, content=False)
else:
    pages_iter = site.allpages(namespace=0, filterredir=False)

# Optional limit
if TEST_LIMIT is not None:
    from itertools import islice
    pages_iter = islice(pages_iter, TEST_LIMIT)

# Null edit loop
count = 0
for count, page in enumerate(pages_iter, start=1):
    try:
        page.touch(comment=COMMENT)
        print(f"✅ [{count}] {page.title()}")
        time.sleep(DELAY)
    except Exception as e:
        print(f"❌ [{count}] {page.title()}: {e}")

print(f"Done. Touched {count} page(s).")
