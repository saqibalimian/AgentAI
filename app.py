from fastapi import FastAPI, HTTPException
import requests
from typing import List
from serpapi import GoogleSearch
import json 
import os
import datetime
from bs4 import BeautifulSoup
import demoji
import sys
import traceback
import re
app = FastAPI()
from typing import List, Dict, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import streamlit as st
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
PRO_API_KEY = os.getenv("PRO_API_KEY")

CACHE_FILE = "search_cache.json"

# Load cache from file if it exists
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
else:
    cache = {}

@app.get("/google_search")
def google_search(query: str):
    try:
        params = {
            "engine": "google",
            "q": query +'" site:linkedin.com/in/',
            "api_key": SERPAPI_API_KEY
        }
        if query in cache:
            results = cache[query]
        else:
            search = GoogleSearch(params)
            results = search.get_dict()
            cache[query] = results
            # Save the cache to the file
            with open(CACHE_FILE, "w") as f:
                json.dump(cache, f)

         # Extract the organic_results list
        organic_results = results.get("organic_results", [])

        # Parse the results to extract desired fields
        extracted_data = []
        for item in organic_results:
            name = item.get("title", "")  # Assuming 'name' corresponds to 'title'
            link = item.get("link", "")
            snippet = item.get("snippet", "")
            # Extract location from the rich_snippet if it exists
            location = item.get("rich_snippet", {}).get("top", {}).get("extensions", [])[0] if item.get(
                "rich_snippet", {}).get(
                "top", {}).get("extensions") else ""

            # Append the parsed data to the list
            extracted_data.append({
                "name": name,
                "link": link,
                "location": location,
                "snippet": snippet
            })
        return extracted_data
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        raise HTTPException(status_code=500, detail=str(e) + str(repr(traceback.format_exception(exc_type, exc_value, exc_traceback))))
    

   

