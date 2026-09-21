import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"
MAX_RETRIES = 3
MAX_WAIT_SECONDS = 20


def post_with_retry(api_key: str, payload: dict) -> httpx.Response:
    """Call Groq, and wait then retry when the free-tier rate limit (429) is hit."""
    for attempt in range(MAX_RETRIES + 1):
        response = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=60,
        )
        if response.status_code != 429 or attempt == MAX_RETRIES:
            return response
        wait = float(response.headers.get("retry-after", 8))
        time.sleep(min(wait, MAX_WAIT_SECONDS) + 1)
    return response


def analyze_job(resume_text: str, skills: list[str], job: dict) -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY is missing"}

    prompt = f"""You are a career coach. Compare this resume with this job.

RESUME:
{resume_text[:1800]}

CANDIDATE SKILLS: {", ".join(skills)}

JOB TITLE: {job["title"]}
COMPANY: {job["company"]}
JOB DESCRIPTION:
{job["description"][:1200]}

Reply with JSON only, using exactly these keys:
"why_fit": a string of 2 sentences explaining why the candidate fits,
"skill_gaps": a list of up to 5 skills the job wants that the resume lacks,
"resume_tips": a list of 3 short tips to tailor the resume for this job."""

    response = post_with_retry(
        api_key,
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "reasoning_effort": "low",
            "max_tokens": 1200,
        },
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "The AI reply was not valid JSON", "raw": content}
