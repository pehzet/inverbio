import requests
from tavily import TavilyClient

# Tavily API key
TAVILY_API_KEY = "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"

# initialize Tavily client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

def tavily_search(query):
    """
    Input: query (str) – search terms
    Output: list[dict] – each dict has 'title', 'url', 'snippet'
    """
    # call Tavily search endpoint
    response = tavily_client.search(query)
    return response
    # # build structured results list
    # results = []
    # for item in response.get("results", []):
    #     results.append({
    #         "title":   item.get("title"),
    #         "url":     item.get("url"),
    #         "snippet": item.get("snippet")
    #     })
    # return results
if __name__ == "__main__":
    # Example usage
    query = "Was bedeutet bio?"
    results = tavily_search(query)
    print(results)  # Print the search results