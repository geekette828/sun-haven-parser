import sys
import os
import pywikibot
import mwparserfromhell
from pywikibot.pagegenerators import PreloadingGenerator
import config.constants as constants

# Pywikibot initialization (path & settings)
sys.path.append(constants.ADDITIONAL_PATHS["PWB"])
pywikibot.config.throttle    = constants.PWB_SETTINGS["throttle"]
pywikibot.config.max_retries = constants.PWB_SETTINGS["max_retries"]
pywikibot.config.retry_wait  = constants.PWB_SETTINGS["retry_wait"]
pywikibot.config.user_agent  = constants.PWB_SETTINGS["user_agent"]


def get_site(
    code: str = "en",
    family: str = "sunhaven"
) -> pywikibot.Site:
    """
    Return a configured Site object with PWB settings applied.
    """
    return pywikibot.Site(code, family)


def get_pages_with_template(
    template_name: str,
    namespace: int | list[int] | None = None
) -> list[str]:
    """
    Return a list of titles of pages that transclude Template:template_name.

    Args:
        template_name (str): Name of the template (without "Template:" prefix).
        namespace (int or list of ints, optional): Namespace number(s) to restrict.

    Returns:
        List of page titles.
    """
    site = get_site()
    tpl = pywikibot.Page(site, f"Template:{template_name}")
    if isinstance(namespace, int):
        ns = [namespace]
    else:
        ns = namespace or []
    pages = tpl.embeddedin(namespaces=ns)
    return [p.title() for p in pages]


def fetch_pages(
    titles: list[str],
    batch_size: int = 50
) -> dict[str, str]:
    """
    Given a list of page titles, return a dict mapping title -> wikitext.
    Uses PreloadingGenerator for efficient bulk fetch.
    """
    site = get_site()
    page_objs = (pywikibot.Page(site, t) for t in titles)
    # Pass batch_size as positional parameter to avoid keyword errors
    pg = PreloadingGenerator(page_objs, batch_size)
    return {page.title(): page.text for page in pg}


def parse_template_params(
    wikitext: str,
    template_name: str
) -> dict[str, str]:
    """
    Given raw page wikitext and a template name,
    find the first occurrence of {{template_name|...}} and return its params.
    """
    code = mwparserfromhell.parse(wikitext)
    for tpl in code.filter_templates():
        if tpl.name.matches(template_name):
            return {p.name.strip(): p.value.strip() for p in tpl.params}
    return {}


def load_items_by_template(
    template_name: str,
    namespace: int | list[int] | None = None
) -> dict[str, dict[str, str]]:
    """
    High-level helper to load items by template:
    1. Get all pages with the template
    2. Fetch their wikitext
    3. Parse out the template parameters
    Returns: { page_title: { param_name: param_value, … }, … }
    """
    titles = get_pages_with_template(template_name, namespace)
    wikitexts = fetch_pages(titles)
    return {
        title: parse_template_params(text, template_name)
        for title, text in wikitexts.items()
    }
