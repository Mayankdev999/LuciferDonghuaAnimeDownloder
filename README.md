# TheAnimeLink - Universal Donghua Hub & Video Extractor

A modern, full-stack application that provides in-app Donghua browsing, search, dynamic episode listings, per-anime watch/download progress tracking, and 1-click SaveTheVideo downloading using advanced browser TLS/JA3 impersonation (`curl_cffi` with `chrome124`).

---

## Features

- **Universal Search & Catalog**: Search and browse any anime on LuciferDonghua without ads or popups.
- **Dynamic Episode Browser**: Automatically lists all episodes for any series (whether 6, 52, or 500+ episodes) with instant episode search and Oldest/Newest sort toggle.
- **⭐ Persistent Bookmarks**: Pin your favorite series to the home screen using `localStorage` ($0 cost, instant load).
- **Independent Progress Tracker**: Remembers the last downloaded episode for **each anime individually** (e.g. *Perfect World* tracks Ep 3 separately from *BTTH* tracking Ep 208).
- **⚡ Batch Range Downloader**: Extract and open an episode sequence (e.g. Ep 1 to Ep 5 or "Next 5 Unwatched") in SaveTheVideo tabs automatically.
- **Advanced Bot Impersonation**: Uses `curl_cffi` with `impersonate="chrome124"` to bypass Cloudflare and bot protections.
- **Direct Link Extractor**: Retains manual URL input for quick extraction of any standalone video or episode page.

---

## Project Structure

```
TheAnimeLink/
├── app.py                # FastAPI backend & extraction engine
├── requirements.txt      # Dependencies (fastapi, curl_cffi, bs4, etc.)
├── static/
│   ├── index.html        # Single-page modern user interface
│   ├── style.css         # Dark theme, modern layout & animations
│   └── script.js         # Frontend fetch logic & clipboard handler
├── tests/
│   └── test_app.py       # Automated unit & integration tests
└── README.md             # Documentation & guide
```

---

## Step-by-Step Installation & Setup

### 1. Prerequisites
Ensure you have Python 3.9+ installed on your system.

### 2. Clone / Navigate to Directory
```bash
cd /path/to/TheAnimeLink
```

### 3. Create a Python Virtual Environment
```bash
python3 -m venv venv
```

### 4. Activate the Virtual Environment
- **On Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```
- **On Windows (Command Prompt):**
  ```cmd
  venv\Scripts\activate.bat
  ```
- **On Windows (PowerShell):**
  ```powershell
  venv\Scripts\Activate.ps1
  ```

### 5. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Running the Application

### Option 1: Direct Python Execution
```bash
python app.py
```

### Option 2: Using Uvicorn CLI
```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

After starting the server, open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## API Specification

### Extract Links Endpoint

- **URL:** `/api/extract`
- **Method:** `POST`
- **Headers:** `Content-Type: application/json`

#### Request Payload:
```json
{
  "url": "https://example.com/anime-episode-page"
}
```

#### Success Response (`200 OK`):
```json
{
  "success": true,
  "links": [
    "https://www.dailymotion.com/embed/video/k12345"
  ],
  "source": "iframe_selector",
  "error": null
}
```

#### Empty / Failure Response (`200 OK`):
```json
{
  "success": false,
  "links": [],
  "source": null,
  "error": "No embedded iframe (#pembed) or Dailymotion video source links were found on the page."
}
```

---

## Running Automated Tests

To run the test suite:
```bash
pytest tests/
```

---

## Deploying to Render (Free Online Hosting)

You can host this application online for free on [Render.com](https://render.com) in a few easy steps:

### Step 1: Push Code to GitHub
Create a new GitHub repository (public or private) and push your project:
```bash
git init
git add .
git commit -m "Initial commit for TheAnimeLink"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### Step 2: Deploy on Render
1. Go to [dashboard.render.com](https://dashboard.render.com/) and log in.
2. Click **New +** $\rightarrow$ **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your GitHub repo.
4. Render will automatically detect `render.yaml` or you can configure manually:
   - **Name**: `theanimelink-extractor`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
5. Click **Create Web Service**.

Once the build finishes (takes ~1-2 minutes), your web app will be live with a free HTTPS URL (e.g., `https://theanimelink-extractor.onrender.com`).

