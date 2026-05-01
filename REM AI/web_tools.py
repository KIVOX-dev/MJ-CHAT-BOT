import requests
from bs4 import BeautifulSoup
import wikipedia
from duckduckgo_search import DDGS

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
    """
    try:
        headers = {"User-Agent": "REM AI Researcher v1.0"}
        response = requests.get(url, headers=headers, timeout=8)
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
