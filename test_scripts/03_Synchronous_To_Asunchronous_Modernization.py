"""
TEST CASE 3: SYNCHRONOUS TO ASYNCHRONOUS MODERNIZATION
Challenge: This script uses outdated, synchronous blocking standard libraries 
(urllib.request) and blocking sleep (time.sleep) inside a loop, which scales 
horribly for network operations.
Expected AI Behavior: The AI should refactor the synchronous blocking code into 
modern Python `async`/`await` paradigms, utilizing `asyncio.sleep` and a modern 
asynchronous HTTP client (like `aiohttp` or `httpx`), executing the requests concurrently.
"""

# legacy_network.py
import urllib.request
import time

def fetch_urls(url_list):
    results = []
    for url in url_list:
        try:
            # Synchronous blocking call
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                html = response.read().decode('utf-8')
                results.append(len(html))
        except Exception as e:
            results.append(-1)
        
        # Artificial blocking delay
        time.sleep(1)
        
    return results