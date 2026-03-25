# Daily Digest — Setup Guide

Your personalised daily news brief. Runs automatically every morning, updates a web page
at a fixed URL, and emails the digest to you.

**Estimated setup time: 30–45 minutes (one-time only)**

---

## What this does

Every morning at 6am (UK time), an automated script:

1. Fetches news from BBC, The Economist, HBR, New Scientist, Wired, MIT Tech Review, and more
2. Uses Claude AI to write engaging, personalised summaries across 6 sections
3. Updates a web page at your fixed GitHub Pages URL
4. Emails the digest to you

The 6 sections are: **Data & AI · Tech World · Markets & Finance · Science ·
Strategy & Business · Today's Random Concept**

---

## What you need (all free or nearly free)

| What | Cost | Why you need it |
|---|---|---|
| GitHub account | Free | Hosts your code and web page |
| Anthropic API key | ~£1–3/month | Powers the AI summaries |
| Gmail account | Free | Sends the daily email |

---

## Step-by-step setup

### Step 1 — Create a GitHub account

1. Go to **https://github.com** and click **Sign up**
2. Choose a username (this will appear in your web page URL)
3. Verify your email address

---

### Step 2 — Create a new repository

1. Once logged in to GitHub, click the **+** icon in the top-right corner
2. Click **New repository**
3. Name it: `daily-digest`
4. Set it to **Public** (required for free hosting — the content is just news, nothing private)
5. Leave everything else as default
6. Click **Create repository**

---

### Step 3 — Upload the project files

You need to upload 4 things into your new GitHub repository.

**The files are already on your Mac at:** `/Users/yrathi/daily-digest/`

**Option A — Upload via GitHub website (no coding required)**

1. In your new repository, click **Add file** → **Upload files**
2. Open a Finder window and navigate to `/Users/yrathi/daily-digest/`
   (Press Cmd+Shift+G in Finder and paste the path)
3. Drag these files into the GitHub upload area:
   - `generate_digest.py`
   - `requirements.txt`
   - `index.html`
4. Click **Commit changes**

Then you need to create the workflow file (GitHub needs it in a specific folder):

5. In your repository, click **Add file** → **Create new file**
6. In the filename box at the top, type exactly: `.github/workflows/daily-digest.yml`
   (GitHub will automatically create the folders as you type the slashes)
7. Open the file `/Users/yrathi/daily-digest/.github/workflows/daily-digest.yml`
   on your Mac (you can open it with TextEdit), copy the entire contents,
   and paste it into the GitHub editor
8. Click **Commit changes**

**Option B — Use Terminal (faster if you're comfortable)**

```bash
cd /Users/yrathi/daily-digest
git init
git add .
git commit -m "Initial setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/daily-digest.git
git push -u origin main
```
Replace `YOUR_USERNAME` with your actual GitHub username.

---

### Step 4 — Enable GitHub Pages (your fixed web page URL)

1. In your repository, click **Settings** (the tab along the top)
2. In the left sidebar, click **Pages**
3. Under **Source**, select **Deploy from a branch**
4. Under **Branch**, select `main` and folder `/` (root)
5. Click **Save**

Your URL will be: `https://YOUR_USERNAME.github.io/daily-digest/`

It may take 1–2 minutes to activate the first time.

---

### Step 5 — Get your Anthropic API key

1. Go to **https://console.anthropic.com**
2. Sign up or log in
3. Click **API Keys** in the left sidebar
4. Click **Create Key**, give it a name like "daily-digest"
5. Copy the key — it starts with `sk-ant-...`
6. **Important:** Add a billing method. The digest costs roughly £0.01–0.05 per day.
   Go to **Billing** → **Add payment method** and add a card.
   Set a usage limit of £5/month to be safe.

---

### Step 6 — Set up Gmail for sending emails

To let the script send email from your Gmail account, you need to create an
**App Password** (a special one-time password just for this).

1. Go to your Google Account: **https://myaccount.google.com**
2. Click **Security** in the left sidebar
3. Make sure **2-Step Verification** is turned ON (required for App Passwords)
4. Search for "App passwords" in the search bar at the top of the page,
   or go to: **https://myaccount.google.com/apppasswords**
5. Under "App name", type: `daily-digest`
6. Click **Create**
7. Google will show you a 16-character password. Copy it — you will only see it once.

---

### Step 7 — Add your secret keys to GitHub

Your API keys must be stored as GitHub Secrets so they are never visible in the code.

1. In your GitHub repository, click **Settings**
2. In the left sidebar, expand **Secrets and variables** → click **Actions**
3. Click **New repository secret** and add each of these four secrets:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic key (starts with `sk-ant-...`) |
| `GMAIL_USER` | Your full Gmail address (e.g. `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | The 16-character app password from Step 6 |
| `EMAIL_TO` | The email address to send the digest to (can be the same Gmail) |

Add each one by clicking **New repository secret**, entering the name and value,
then clicking **Add secret**.

---

### Step 8 — Run it for the first time

1. In your repository, click the **Actions** tab
2. Click **Generate Daily Digest** in the left sidebar
3. Click **Run workflow** → **Run workflow** (green button)
4. Watch the run progress — it takes about 2–3 minutes
5. Once it shows a green tick, go to your GitHub Pages URL:
   `https://YOUR_USERNAME.github.io/daily-digest/`

Your first digest is live. From now on it runs automatically every morning.

---

## How to customise your digest

All customisation is done in one place: the **CONFIGURATION** section at the top
of `generate_digest.py` (lines 1–100 approximately).

To edit it on GitHub:

1. Open your repository on GitHub
2. Click on `generate_digest.py`
3. Click the pencil icon ✏️ (Edit this file)
4. Make your changes in the CONFIGURATION section
5. Click **Commit changes**

The next morning's digest will reflect your changes.

**Things you can change:**

- **`CLAUDE_MODEL`** — Change to `"claude-sonnet-4-6"` for richer analysis
  (costs a bit more, maybe £0.10–0.30/day instead of pennies)
- **`MY_BACKGROUND`** — Update if your interests or role changes
- **`SECTIONS`** — Change prompts, or swap in different RSS feeds
- **`cron: "0 6 * * *"`** in the workflow file — Change delivery time
  (format is `minute hour * * *` in UTC; `0 6` = 6am UTC = 7am UK winter)

---

## Your daily web page URL

```
https://YOUR_USERNAME.github.io/daily-digest/
```

This URL never changes. Bookmark it. The content updates every morning.

---

## Troubleshooting

**The workflow failed (red X in Actions tab)**
- Click on the failed run and expand the steps to see the error message
- Most common cause: a secret is missing or incorrectly named — double-check Step 7

**I got the email but it looks broken**
- Gmail renders it well. If you use Outlook it may look slightly different — try
  reading it in the browser instead via your GitHub Pages URL

**Some sections say "No articles available today"**
- Occasionally an RSS feed is temporarily down. It will recover on its own.

**I want to stop the daily emails temporarily**
- In your repository, go to `.github/workflows/daily-digest.yml`,
  edit it, and comment out the `schedule:` block by adding a `#` before those lines

---

## Cost summary

| Service | Monthly cost |
|---|---|
| GitHub | Free |
| GitHub Pages | Free |
| Anthropic API | ~£1–3 |
| Gmail | Free |
| **Total** | **~£1–3/month** |

---

*Generated by Claude Code · Edit `generate_digest.py` to customise*
