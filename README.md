# AI Career Agent

Personal job-intelligence and application-preparation agent for an AWS/DevOps engineer.

## MVP
- Poll public ATS job feeds (Greenhouse, Lever, Ashby)
- Normalize and deduplicate jobs
- Match jobs against a configurable career profile
- Detect newly seen jobs
- Publish a JSON feed for the iPhone app
- Optional ntfy notifications
- Human-in-the-loop application flow: review and submit manually

## Zero-cost architecture

GitHub Actions -> ATS adapters -> matcher -> `data/jobs.json` -> native SwiftUI app

No passwords, CAPTCHA bypass, blind application submission, or fabricated experience.

## Setup

```bash
python scripts/job_radar.py
```

Optional notification:
```bash
export NTFY_TOPIC="your-random-topic"
python scripts/job_radar.py
```

The GitHub Actions workflow runs on a schedule and commits the feed when it changes.

## Sources

Edit `config/sources.json`. Each source is an official public ATS endpoint configuration. Add company boards as you identify them.

## iOS

`ios/AdityaJobAgent` contains the SwiftUI source for the native review app. It reads the public GitHub raw JSON feed.
