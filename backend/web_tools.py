import requests
from bs4 import BeautifulSoup
import wikipedia
from duckduckgo_search import DDGS

from net_security import UnsafeUrlError, check_url_is_safe

MAX_REDIRECTS = 3

def search_web(query: str, results_limit: int = 3):
    """
    Search DuckDuckGo for general web results.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=results_limit))
            return [
                {"title": r['title'], "link": r['href'], "snippet": r['body']}
                for r in results
            ]
    except Exception as e:
        print(f"[!] DuckDuckGo Search Error: {e}")
        return []

def fetch_web_content(url: str):
    """
    Fetches and extracts clean text context from a specific URL.

    The URL here is effectively LLM-chosen (the model emits [FETCH: url]
    based on search results/page content it read, which an attacker can
    influence) - so every hop, including redirects, is checked against
    net_security before we connect. See net_security.py for what's blocked
    and why (CWE-918 SSRF).
    """
    try:
        check_url_is_safe(url)
    except UnsafeUrlError as e:
        return f"Error fetching {url}: blocked by SSRF guard ({e})"

    headers = {"User-Agent": "REM AI Researcher v1.0"}
    current_url = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            response = requests.get(current_url, headers=headers, timeout=8, allow_redirects=False)

            if response.is_redirect:
                next_url = response.headers.get("Location")
                if not next_url:
                    return f"Error fetching {url}: redirect with no Location header"
                try:
                    check_url_is_safe(next_url)
                except UnsafeUrlError as e:
                    return f"Error fetching {url}: redirect target blocked by SSRF guard ({e})"
                current_url = next_url
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            text = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text[:3000] # Return first 3000 chars as research context

        return f"Error fetching {url}: too many redirects"
    except Exception as e:
        return f"Error fetching {url}: {e}"

def search_and_extract(query: str):
    """
    Main entry point for single-shot search (legacy support).
    """
    # ... legacy logic or new unified search
    results = search_web(query, 1)
    if results:
        content = fetch_web_content(results[0]['link'])
        return {
            "source": results[0]['title'],
            "context": f"Search Result: {content}..."
        }
    return None
