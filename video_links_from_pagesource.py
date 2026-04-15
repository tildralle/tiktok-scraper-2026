from bs4 import BeautifulSoup
import json

account = "fdpbt"

file = f'page_source/{account}.html'

# Read the HTML file
with open(file, 'r', encoding='utf-8') as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, "html.parser")

# video_soup = soup.find("div", attrs={"class": "css-5imlox-7937d88b--DivShareLayoutContentV2 emfsdl21"}) # "css-1m6t8x3-5e6d46e3--DivThreeColumnContainer e1so5acu2"

video_links = [s.get("href") for s in soup.find_all("a") if account in s.get("href")]

# bad_words = ["playlist", "photo"]
good_words = ["video"]
valid_links = []
invalid = False
for v in video_links:
    if any(b in v for b in good_words):
        valid_links.append(v)
#    if f"@{account}" not in v:
#        continue
#    valid_links.append(v)
video_links = valid_links

print(f"Posts found: {len(video_links)}")

with open(f"video_links/{account}.json", 'w') as f:
    json.dump(video_links, f, indent=2)