import requests, random, time
import numpy as np

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

test_url = "https://www.tiktok.com/"

with open("Webshare 10 proxies.txt", "r") as f:
    proxy_list = f.readlines()
    proxy_list = [p.replace("\n", "") for p in proxy_list]

proxies = []

for proxy in proxy_list:
    address, port, user, password = proxy.split(":")
    proxies.append(
        {
            "http": f"http://{user}:{password}@{address}:{port}/",
            "https": f"http://{user}:{password}@{address}:{port}/"
        }
    )

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
]

sleeps = np.linspace(0.5,3,1000)

failed_proxies = []
working_proxies = 0
for proxy in proxies:
    user_agent = random.choice(user_agents)
    headers = {'User-Agent': user_agent}
    sleep = random.choice(sleeps)

    print("Sleep: ", sleep)
    print("User-Agent: ", user_agent)
    print("Proxy: ", proxy)

    time.sleep(sleep)

    response = requests.get(test_url, headers=headers, proxies=proxy, timeout=10)
    if response.status_code == 200:
        working_proxies += 1
    else:
        failed_proxies.append(proxy)
    print(f"status code: {bcolors.HEADER}{bcolors.BOLD}{response.status_code}{bcolors.ENDC}")

if working_proxies == len(proxies):
    print(f"{bcolors.OKGREEN}{bcolors.BOLD}All Proxies Working!{bcolors.ENDC}")
else:
    print(f"{bcolors.FAIL}{bcolors.BOLD}Following Proxies failed:{bcolors.ENDC}")
    print(failed_proxies)