"""Publish new links from the Awesome Weird Web README as RSS items."""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

REPOSITORY = "https://github.com/monapdx/Awesome-Weird-Web"
FEED_URL = "https://raw.githubusercontent.com/monapdx/Awesome-Weird-Web/main/feed.xml"
ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "feed.xml"
SEEN = ROOT / "scripts" / "rss-seen-urls.json"
ENTRY = re.compile(
    r"^[-+*]\s+\[([^\]]+)\]\((<?https?://(?:[^()<>\s]|\([^()\s]*\))+>?)\)"
    r"(?:\s+[-–—]\s+(.*))?\s*$"
)


def entries(markdown):
    category = None
    for line in markdown.splitlines():
        if line.startswith("## "):
            category = line[3:].strip()
        match = ENTRY.fullmatch(line)
        if category and match:
            title, url, description = match.groups()
            yield title, url.strip("<>"), description or "", category


def initialize_feed():
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Awesome Weird Web"
    ET.SubElement(channel, "link").text = REPOSITORY
    ET.SubElement(channel, "description").text = "New links from Awesome Weird Web."
    namespace = "http://www.w3.org/2005/Atom"
    ET.SubElement(channel, f"{{{namespace}}}link", {
        "href": FEED_URL, "rel": "self", "type": "application/rss+xml",
    })
    return ET.ElementTree(rss)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()

    current = list(entries((ROOT / "README.md").read_text(encoding="utf-8")))
    if not current:
        raise SystemExit("No list entries found in README.md.")

    namespace = "http://www.w3.org/2005/Atom"
    ET.register_namespace("atom", namespace)
    if args.initialize:
        if FEED.exists() or SEEN.exists():
            raise SystemExit("Feed or URL history already exists.")
        seen = {url for _, url, _, _ in current}
        tree = initialize_feed()
    else:
        seen = set(json.loads(SEEN.read_text(encoding="utf-8")))
        tree = ET.parse(FEED)
        channel = tree.getroot().find("channel")
        published = format_datetime(datetime.now(timezone.utc), usegmt=True)
        new_items = []
        for title, url, description, category in current:
            if url in seen:
                continue
            seen.add(url)
            item = ET.Element("item")
            ET.SubElement(item, "title").text = title
            ET.SubElement(item, "link").text = url
            ET.SubElement(item, "guid", isPermaLink="true").text = url
            ET.SubElement(item, "description").text = description
            ET.SubElement(item, "category").text = category
            ET.SubElement(item, "pubDate").text = published
            new_items.append(item)
        if not new_items:
            return
        first_item = next((i for i, element in enumerate(channel) if element.tag == "item"), len(channel))
        channel[first_item:first_item] = new_items

    ET.indent(tree, space="  ")
    FEED.write_bytes(ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True) + b"\n")
    SEEN.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
