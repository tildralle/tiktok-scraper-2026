# https://decodo.com/blog/scrape-tiktok#h2-why_proxies_are_necessary_for_stable_tiktok_scraping

import asyncio
import re
import json
import random
import time
import logging
import sys
import os
import glob
import numpy as np
from parsel import Selector
import jmespath
from httpx import AsyncClient
from urllib.parse import urlencode
from iteration_utilities import unique_everseen
import pickle

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

### Error Logs

logging.basicConfig(
    filename='error.log',
    filemode='w',
    level=logging.ERROR,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)

def log_error(text, clear=True):
    if clear:
        logger.handlers.clear()
    else:
        pass
    logger.exception(text)
    return

### Proxies

with open("Webshare 10 proxies.txt", "r") as f:
    proxy_list = f.readlines()
    proxy_list = [p.replace("\n", "") for p in proxy_list]

proxies = []

for proxy in proxy_list:
    address, port, user, password = proxy.split(":")
    proxies.append(f"http://{user}:{password}@{address}:{port}/")

### Scrape Profile

async def create_client(proxy):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    # Proxy configuration: replace with your credentials in this format: "protocol://username:password@host:port"
    return AsyncClient(headers=headers, proxy=proxy, timeout=30.0)

def parse_profile(response):
    """parse profile data from hidden scripts on the HTML"""
    selector = Selector(response.text)
    data = selector.xpath("//script[@id='__UNIVERSAL_DATA_FOR_REHYDRATION__']/text()").get()
    profile_data = json.loads(data)["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]  
    return profile_data

async def scrape_profile(proxy, account, save_dir, restart=False):
    """scrape tiktok profile data from its URL"""
    data_in_save_dir = glob.glob(f"{save_dir}*.json")
    accounts_already_scraped = [d.split("/")[-1].split(".")[0] for d in data_in_save_dir]
    if not restart:
        if account in accounts_already_scraped:
            print(f"{bcolors.OKCYAN}Account '{account}' already scraped{bcolors.ENDC}")
            return

    client = await create_client(proxy=proxy)
    response = await client.get(f"https://www.tiktok.com/@{account}")
    try:
        profile_data = parse_profile(response)
        with open(f"{save_dir}{account}.json", "w", encoding="utf-8") as f:     
            json.dump(profile_data, f, ensure_ascii=False, indent=4)
        print(f"{bcolors.OKGREEN}Scraping account '{account}' successful{bcolors.ENDC}")
        await client.aclose()
        return
    except:
        print(f"{bcolors.FAIL}Scraping account failed{bcolors.ENDC}")
        log_error(f"Scraping account failed")
        await client.aclose()
        return

### Scrape Post

def parse_post(response):
    """parse hidden post data from HTML"""
    selector = Selector(response.text)
    data = selector.xpath("//script[@id='__UNIVERSAL_DATA_FOR_REHYDRATION__']/text()").get()
    post_data = json.loads(data)["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]
    parsed_post_data = jmespath.search(
        """{
        id: id,
        desc: desc,
        createTime: createTime,
        video: video.{duration: duration, ratio: ratio, cover: cover, playAddr: playAddr, downloadAddr: downloadAddr, bitrate: bitrate},
        author: author.{id: id, uniqueId: uniqueId, nickname: nickname, avatarLarger: avatarLarger, signature: signature, verified: verified},
        stats: stats,
        locationCreated: locationCreated,
        diversificationLabels: diversificationLabels,
        suggestedWords: suggestedWords,
        contents: contents[].{textExtra: textExtra[].{hashtagName: hashtagName}}
        }""",
        post_data
    )
    return parsed_post_data

async def scrape_tiktok(post_url, proxy, max_comments=20):
    post_id = re.search(r'/video/(\d+)', post_url).group(1)

    try:
        client = await create_client(proxy)
    except:
        print(f"{bcolors.FAIL}Client failed.{bcolors.ENDC}")
        log_error("Client failed")
        return []

    try:
        response = await client.get(post_url)
        if response.status_code == 200:
            print(f"Status Code (Post Request): {bcolors.OKGREEN}{response.status_code}{bcolors.ENDC}")
        else:
            print(f"Status Code (Post Request): {bcolors.FAIL}{response.status_code}{bcolors.ENDC}")

        # pickle.dump(response, open("response.p", "wb"))
        
        parsed_post_data = parse_post(response)
        
        pos = list(parsed_post_data.keys()).index('id')
        items = list(parsed_post_data.items())
        items.insert(pos, ('url', post_url))
        parsed_post_data = dict(items)

        total_comments = parsed_post_data["stats"]["commentCount"]
        if total_comments == 0:
            parsed_post_data["comments"] = []
            return parsed_post_data

        text = response.text
        
        params = {"aweme_id": post_id, "cursor": 0, "count": max_comments, "current_region": "US", "aid": "1988"}
        
        for pattern in [r'"aid":(\d+)', r'"msToken":"([^"]+)"', r'"region":"([^"]+)"']:
            match = re.search(pattern, text)
            if match and 'aid' in pattern:
                params['aid'] = match.group(1)
            elif match and 'msToken' in pattern:
                params['msToken'] = match.group(1)
            elif match and 'region' in pattern:
                params['region'] = match.group(1)
        
        comments = []
        while True:
            api_url = "https://www.tiktok.com/api/comment/list/?" + urlencode(params)
            
            api_response = await client.get(api_url, headers={"accept": "application/json", "referer": post_url})

            if api_response.status_code == 200:
                print(f"Status Code (API Request): {bcolors.OKGREEN}{response.status_code}{bcolors.ENDC}")
                print(f"Cursor: {params["cursor"]}/{total_comments}")

                data = api_response.json()

                for comment in data.get('comments', []):
                    if comment.get('text'):
                        comments.append({
                            'cid': comment['cid'],
                            'comment_language': comment['comment_language'],
                            'create_time': comment['create_time'],
                            'digg_count': comment['digg_count'],
                            'reply_comment': comment['reply_comment'],
                            'reply_comment_total': comment['reply_comment_total'],
                            'reply_id': comment['reply_id'],
                            'reply_to_reply_id': comment['reply_to_reply_id'],
                            'text': comment['text'],
                            'user': {
                                'name': comment['user']['nickname'],
                                'uid': comment['user']['uid'],
                                'unique_id': comment['user']['unique_id']
                            }
                        })
                
                if params["cursor"] > total_comments:
                    parsed_post_data["comments"] = list(unique_everseen(comments))
                    break
                params["cursor"] += 20
                sys.stdout.write("\033[2A")
            else:
                print(f"Status Code (Post Request): {bcolors.FAIL}{response.status_code}{bcolors.ENDC}")
                break
        return parsed_post_data
    except:
        print(f"{bcolors.FAIL}Scraping failed{bcolors.ENDC}")
        log_error(f"Scraping failed: {post_id}")
    finally:
        await client.aclose()
    return []

async def main(post_urls, save_dir, restart=False):
    failed_posts = []
    
    data_in_save_dir = glob.glob(f"{save_dir}*.json")
    ids_already_scraped = [d.split("/")[-1].split(".")[0] for d in data_in_save_dir]
    for n, pu in enumerate(post_urls):
        post_id = pu.split("/")[-1]
        # post_url = "https://www.tiktok.com/@afdfraktionimbundestag/video/7595510676009930006" 
        proxy = random.choice(proxies)

        print('--------------------------------------------')
        print(f"Processing {n+1}/{len(post_urls)} ({bcolors.OKCYAN}{round(n/len(post_urls)*100,2)} %{bcolors.ENDC})")
        print(f"Post ID: {post_id}")
        if not restart:
            if post_id in ids_already_scraped:
                print(f"{bcolors.OKCYAN}Already scraped{bcolors.ENDC}")
                continue

        print("Proxy: ", proxy)

        result = await scrape_tiktok(pu, proxy)
        
        if result:
            with open(f"{save_dir}{result["id"]}.json", "w", encoding="utf-8") as f:     
                json.dump(result, f, ensure_ascii=False, indent=4)
            print(f"{bcolors.OKGREEN}Passed{bcolors.ENDC}")
        else:
            failed_posts.append(pu)
        
        sleep = random.choice(np.linspace(1.5,2.5,100))
        time.sleep(sleep)

    with open(f"{save_dir}failed_posts.json", 'w') as f:
        json.dump(failed_posts, f, indent=2)

if __name__ == "__main__":
    
    account = "merzcdu"
    account_only = False

    save_dir_account = f"data/profile_data/"
    if not os.path.isdir(save_dir_account):
        os.mkdir(save_dir_account)
    proxy = random.choice(proxies)
    asyncio.run(scrape_profile(proxy, account, save_dir=save_dir_account, restart=False))

    test_mode = False
    if not account_only:
        if test_mode:
            post_urls = ["https://www.tiktok.com/@insidecdu/photo/7532533692988771606"]
            save_dir_post = "data/"
        else:
            post_urls = json.load(open(f"video_links/{account}.json", "r"))

            save_dir_post = f"data/post_data/{account}/"
            if not os.path.isdir(save_dir_post):
                os.mkdir(save_dir_post)

        asyncio.run(main(post_urls, save_dir=save_dir_post, restart=False))