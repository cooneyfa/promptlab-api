# Publishing PromptLab to your GitHub

Everything below runs on **your** machine, under **your** GitHub account.
Nothing here was published for you — the repo step is yours on purpose.

## 1. Create the public repo (pick one)

**Option A — GitHub CLI (fastest):**
```bash
cd promptlab-api
git init
git add .
git commit -m "Initial commit: PromptLab versioned prompt-template API"
gh repo create promptlab-api --public --source=. --push
```

**Option B — website:**
1. Go to github.com/new, name it `promptlab-api`, set **Public**, create it
   (do NOT add a README/license — the project already has one).
2. Then:
```bash
cd promptlab-api
git init
git branch -M main
git add .
git commit -m "Initial commit: PromptLab versioned prompt-template API"
git remote add origin https://github.com/YOUR-USERNAME/promptlab-api.git
git push -u origin main
```

## 2. Confirm it's public

Your repo page should show a **Public** badge. The Actions tab will run the
test suite automatically on that first push — watch it go green.

## 3. Suggested repo settings

- **About** blurb: "Versioned prompt-template REST API (FastAPI + SQLite) with
  deterministic prompt evaluation and a full pytest suite."
- Topics: `fastapi`, `python`, `rest-api`, `prompt-engineering`, `pytest`
- Pin it to your profile — it's the repo link hiring screens will open.

## 4. Talking about it in interviews

One-liners that land:
- "Versioned CRUD API — every template update is an immutable version row."
- "Hermetic test suite: 18 tests against in-memory SQLite, CI on every push."
- "The evaluator is a swappable mock — designed so a real model scorer can
  drop in without changing the contract."
