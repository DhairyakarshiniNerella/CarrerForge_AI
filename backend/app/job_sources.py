import httpx
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()


ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch_arbeitnow() -> list[dict]:
    response = httpx.get(ARBEITNOW_URL, timeout=15)
    response.raise_for_status()
    data = response.json().get("data", [])

    jobs = []
    for item in data:
        jobs.append(
            {
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", ""),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
                "source": "Arbeitnow",
            }
        )
    return jobs
def clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def fetch_adzuna(query: str, country: str = "in", limit: int = 30) -> list[dict]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "results_per_page": limit,
    }
    response = httpx.get(url, params=params, timeout=15)
    response.raise_for_status()

    jobs = []
    for item in response.json().get("results", []):
        jobs.append(
            {
                "title": item.get("title", ""),
                "company": item.get("company", {}).get("display_name", ""),
                "location": item.get("location", {}).get("display_name", ""),
                "description": clean_html(item.get("description", "")),
                "url": item.get("redirect_url", ""),
                "source": "Adzuna",
            }
        )
    return jobs

def fetch_jooble(query: str, location: str = "India", limit: int = 30) -> list[dict]:
    api_key = os.getenv("JOOBLE_API_KEY")
    if not api_key:
        return []

    url = f"https://jooble.org/api/{api_key}"
    payload = {"keywords": query, "location": location}
    response = httpx.post(url, json=payload, timeout=15)
    response.raise_for_status()

    jobs = []
    for item in response.json().get("jobs", [])[:limit]:
        jobs.append(
            {
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "location": item.get("location", ""),
                "description": clean_html(item.get("snippet", "")),
                "url": item.get("link", ""),
                "source": "Jooble",
            }
        )
    return jobs

def normalize_key(job: dict) -> str:
    parts = [job["title"], job["company"], job["location"]]
    return "|".join(re.sub(r"[^a-z0-9]", "", p.lower()) for p in parts)


COUNTRIES = {
    "in": "India",
    "us": "United States",
    "gb": "United Kingdom",
    "ca": "Canada",
    "au": "Australia",
    "de": "Germany",
}


def fetch_all_jobs(query: str, country: str = "in") -> list[dict]:
    country_name = COUNTRIES.get(country, "India")

    all_jobs = fetch_adzuna(query, country=country) + fetch_jooble(query, location=country_name)
    if country == "de":
        all_jobs += fetch_arbeitnow()

    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = normalize_key(job)
        if key in seen:
            continue
        seen.add(key)
        unique_jobs.append(job)
    return unique_jobs

