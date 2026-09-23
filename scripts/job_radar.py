#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / "config/profile.json").read_text())
SOURCES = json.loads((ROOT / "config/sources.json").read_text())
JOBS_PATH = ROOT / "data/jobs.json"
SEEN_PATH = ROOT / "data/seen.json"

UA = "ai-career-agent/0.1 (+https://github.com/moodyadi/ai-career-agent)"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def clean_html(value):
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def greenhouse(src):
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{urllib.parse.quote(src['board'])}/jobs?content=true")
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"greenhouse:{src['board']}:{j.get('id')}",
            "source": "greenhouse",
            "company": src["company"],
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "description": clean_html(j.get("content", "")),
            "posted_at": j.get("updated_at", "")
        })
    return out

def lever(src):
    # Lever's public postings endpoint.
    data = get_json(f"https://api.lever.co/v0/postings/{urllib.parse.quote(src['company'])}?mode=json")
    out = []
    for j in data if isinstance(data, list) else []:
        cats = j.get("categories") or {}
        desc = j.get("descriptionPlain") or clean_html(j.get("description", ""))
        out.append({
            "id": f"lever:{src['company']}:{j.get('id')}",
            "source": "lever",
            "company": src.get("company_name", src["company"]),
            "title": j.get("text", ""),
            "location": cats.get("location", ""),
            "url": j.get("hostedUrl") or j.get("applyUrl", ""),
            "description": desc,
            "posted_at": ""
        })
    return out

def ashby(src):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{urllib.parse.quote(src['board'])}"
    data = get_json(url)
    out = []
    for j in data.get("jobs", []):
        out.append({
            "id": f"ashby:{src['board']}:{j.get('jobUrl') or j.get('applyUrl')}",
            "source": "ashby",
            "company": src["company"],
            "title": j.get("title", ""),
            "location": j.get("location", ""),
            "url": j.get("jobUrl") or j.get("applyUrl", ""),
            "description": j.get("descriptionPlain", "") or clean_html(j.get("description", "")),
            "posted_at": j.get("publishedAt", "")
        })
    return out

def score(job):
    text = f"{job['title']} {job['description']} {job['location']}".lower()
    title = job["title"].lower()
    score = 0
    matched = []

    for t in PROFILE["target_titles"]:
        if t.lower() in title:
            score += 25
            break

    for skill in PROFILE["skills"]:
        if re.search(r"\b" + re.escape(skill.lower()) + r"\b", text):
            matched.append(skill)
            score += 3

    if any(x.lower() in job["location"].lower() for x in PROFILE["locations"]):
        score += 10

    excluded = [x for x in PROFILE["exclude_keywords"] if x in text]
    if excluded:
        score -= 40

    job["matched_skills"] = matched
    job["score"] = max(0, min(100, score))
    return job

def notify(job):
    topic = os.getenv("NTFY_TOPIC", "").strip()
    if not topic:
        return
    payload = {
        "topic": topic,
        "title": f"{job['company']}: {job['title']}",
        "message": f"Match {job['score']}/100 | {job['location']}\n{job['url']}",
        "priority": "high",
        "tags": ["briefcase", "new"]
    }
    req = urllib.request.Request(
        "https://ntfy.sh/",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:
        print(f"notification failed: {e}", file=sys.stderr)

def main():
    try:
        seen = json.loads(SEEN_PATH.read_text()) if SEEN_PATH.exists() else {}
    except Exception:
        seen = {}

    all_jobs = []
    for src in SOURCES:
        try:
            kind = src.get("type")
            if kind == "greenhouse":
                jobs = greenhouse(src)
            elif kind == "lever":
                jobs = lever(src)
            elif kind == "ashby":
                jobs = ashby(src)
            else:
                print(f"Skipping unknown source: {kind}")
                continue
            all_jobs.extend(jobs)
            time.sleep(0.5)
        except Exception as e:
            print(f"Source failed {src}: {e}", file=sys.stderr)

    now = datetime.now(timezone.utc).isoformat()
    fresh = 0
    normalized = []

    for job in all_jobs:
        job = score(job)
        first = seen.get(job["id"])
        if not first:
            seen[job["id"]] = now
            job["first_seen"] = now
            if job["score"] >= 50 and job["url"]:
                notify(job)
            fresh += 1
        else:
            job["first_seen"] = first
        normalized.append(job)

    normalized.sort(key=lambda x: (x.get("score", 0), x.get("first_seen", "")), reverse=True)
    JOBS_PATH.write_text(json.dumps(normalized[:500], indent=2, ensure_ascii=False) + "\n")
    SEEN_PATH.write_text(json.dumps(seen, indent=2, ensure_ascii=False) + "\n")
    print(f"Scanned {len(all_jobs)} jobs; {fresh} newly seen; {len(normalized)} stored.")

if __name__ == "__main__":
    main()
