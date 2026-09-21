from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from app.job_sources import fetch_all_jobs
from app.llm_analyzer import analyze_job
from app.matcher import pick_top_jobs, rank_jobs
from app.profile_extractor import build_profile
from app.resume_parser import extract_resume_text
from fastapi.staticfiles import StaticFiles


app = FastAPI(title="CareerForge AI")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}





@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed")

    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    save_path.write_bytes(content)

    text = extract_resume_text(save_path)

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Could not read any text from this file. It may be a scanned image.",
        )

    profile = build_profile(text)

    return {
        "filename": file.filename,
        "text_length": len(text),
        "profile": profile,
    }
@app.get("/test-jobs")
def test_jobs(query: str = "python developer"):
    jobs = fetch_all_jobs(query)
    sources = {}
    for job in jobs:
        sources[job["source"]] = sources.get(job["source"], 0) + 1
    return {"total_unique": len(jobs), "by_source": sources}

@app.post("/match-jobs")
async def match_jobs(
    file: UploadFile = File(...),
    experience: float = Form(0),
    country: str = Form("in"),
    job_title: str = Form(""),
):
    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed")

    save_path = UPLOAD_DIR / file.filename
    save_path.write_bytes(await file.read())

    text = extract_resume_text(save_path)
    if not text:
        raise HTTPException(status_code=422, detail="Could not read any text from this file.")

    profile = build_profile(text)
    skills = profile["skills"]
    if not skills:
        raise HTTPException(status_code=422, detail="No known skills found in this resume.")

    query = job_title.strip() or f"{skills[0]} developer"
    jobs = fetch_all_jobs(query, country)
    ranked = rank_jobs(jobs, skills, text, experience)

    top_jobs = []
    for index, j in enumerate(pick_top_jobs(ranked)):
        analysis = None
        if index < 5:
            try:
                analysis = analyze_job(text, skills, j)
            except httpx.HTTPError:
                analysis = {"error": "AI analysis failed for this job"}

        top_jobs.append(
            {
                "title": j["title"],
                "company": j["company"],
                "location": j["location"],
                "source": j["source"],
                "matched_skills": j["matched_skills"],
                "skill_score": j["skill_score"],
                "title_score": j["title_score"],
                "similarity_score": j["similarity_score"],
                "match_score": j["match_score"],
                "required_years": j["required_years"],
                "url": j["url"],
                "analysis": analysis,
            }
        )

    return {
        "profile": profile,
        "search_query": query,
        "total_jobs": len(jobs),
        "top_jobs": top_jobs,
    }


@app.get("/test-llm")
def test_llm():
    job = {
        "title": "Python Developer",
        "company": "Demo Corp",
        "description": "Build REST APIs with Django and MySQL. Docker and Git required. AWS is a plus.",
    }
    resume = "Computer Science graduate. Projects in Python, SQL and Java. Uses Git and Docker."
    return analyze_job(resume, ["python", "sql", "java", "git", "docker"], job)


app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

