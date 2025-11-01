# GitHub Actions Setup

This guide explains how to run the scraper automatically on GitHub's servers daily at 10 PM IST.

## Prerequisites
- GitHub account
- This repository pushed to GitHub

## Setup Steps

### 1. Initialize Git Repository (if not done)
```bash
cd /Users/harshdeepsingh/amazon_godrej_scraper
git init
git add .
git commit -m "Initial commit"
```

### 2. Create GitHub Repository
1. Go to https://github.com/new
2. Create a new **private** repository (e.g., `amazon-godrej-scraper`)
3. Don't initialize with README (we already have files)

### 3. Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/amazon-godrej-scraper.git
git branch -M main
git push -u origin main
```

### 4. Add GitHub Secrets
Go to your repo: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

Add these secrets:

**Secret 1:**
- Name: `EMAIL_APP_PASSWORD`
- Value: `jmsy jvqy thgl hjcx`

**Secret 2:**
- Name: `EMAIL_RECIPIENTS`
- Value: `dfaharsh@gmail.com,harsh999deep@gmail.com`

### 5. Enable GitHub Actions
1. Go to `Actions` tab in your repo
2. If prompted, enable workflows
3. You should see "Godrej Scraper" workflow

### 6. Test It
- Click on "Godrej Scraper" workflow
- Click "Run workflow" button to test manually
- Check the run logs

### 7. Scheduled Execution
- Runs automatically daily at 10:00 PM IST (16:30 UTC)
- Reports are emailed to recipients
- Reports also saved as artifacts in GitHub Actions (downloadable for 30 days)

## Important Notes

⚠️ **GitHub Actions Requirements:**
- Free for public repos (unlimited minutes)
- Private repos: 2,000 minutes/month free
- This scraper takes ~5-10 minutes per run

⚠️ **Amazon may block GitHub IPs:**
- If scraping fails, you may need to use proxies or run from your Mac
- Check workflow logs in Actions tab

## Manual Trigger
You can manually run the scraper anytime:
1. Go to Actions tab
2. Select "Godrej Scraper"
3. Click "Run workflow"

## Unload Local Scheduler
Since GitHub Actions will handle scheduling, unload the local launchd job:
```bash
launchctl unload ~/Library/LaunchAgents/com.godrej.scraper.plist
```

## Troubleshooting
- Check workflow logs in Actions tab
- Verify secrets are set correctly
- Ensure recipients.txt is committed (optional, secrets take precedence)
