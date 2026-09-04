# Sir Ron's Sharp Signal — Railway Deployment

Persistent NFL ATS 3-Factor system with bet tracking. Runs on Railway with a mounted volume for permanent bet storage.

---

## Files in this repo

- `app.py` — the Streamlit application
- `requirements.txt` — Python dependencies
- `Dockerfile` — container definition for Railway
- `railway.toml` — Railway build configuration

---

## Deployment to Railway (one-time setup, ~5 minutes)

### 1. Push these files to a GitHub repo
You already have `dueham/nfl-ats-backtest` — just replace the current files with these four.

### 2. In Railway, create a new project from this repo
- Log into railway.app
- Click **New Project** → **Deploy from GitHub repo**
- Select `dueham/nfl-ats-backtest`
- Railway auto-detects the Dockerfile and starts building

### 3. Add a persistent volume for bet storage
This is what keeps your bets forever, even through restarts and deploys.

- In your Railway project, click the **service** (the app tile)
- Go to the **Settings** tab
- Scroll to **Volumes** → click **+ New Volume**
- **Mount path:** `/data`
- **Size:** 1 GB is plenty (a lifetime of bet logs is only a few MB)
- Click **Add**

### 4. Generate a public URL
- Still in Settings, scroll to **Networking**
- Click **Generate Domain**
- You'll get a URL like `sirron-sharp-signal.up.railway.app`
- Bookmark it — this is your app forever

### 5. Deploy
Railway auto-deploys on every push to `main`. First deploy takes ~3-4 minutes.

---

## Ongoing use

- Open your Railway URL any time — bets persist forever in the mounted volume
- To update the app, push new `app.py` to GitHub → Railway auto-redeploys
- Bet log export (CSV) still works as a backup

---

## Monthly cost

Runs comfortably within the Railway Pro plan's $20/mo usage credit. Typical usage for this kind of app: **~$1-3/month** in resources. RevPar MD continues to run independently on its own service.
