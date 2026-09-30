# 🌾 Farm Scout App

A mobile-friendly Streamlit app for farm workers to **report field issues** in seconds — with GPS, photo upload, Google Sheets logging, and email alerts.

---

## 📱 What It Does

| Feature | Details |
|---|---|
| 📋 Farm dropdown | Pick the farm from a list (you control the list) |
| 📍 Field location | Pick which side/area of the farm |
| 📡 Auto GPS | One tap captures lat/lon on any smartphone |
| ⚠️ Issue type | Dropdown (pest, disease, equipment, etc.) |
| 🔥 Severity | High / Medium / Low |
| 📝 Description | Free text |
| 📷 Photo | Take photo or upload — saved to Cloudinary |
| 📊 Google Sheets | Every submission auto-logged |
| 📧 Email alert | Instant email to you with all details + photo |

---

## 🚀 Deploy to Streamlit Cloud (5 minutes)

1. Push this folder to a **GitHub repo**
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → Select your repo
3. Set main file: `app.py`
4. Go to **Settings → Secrets** and paste all keys from `secrets_template.toml`
5. Click **Deploy**

---

## 🔑 Secrets Setup

### Cloudinary (photo storage)
1. Sign up free at [cloudinary.com](https://cloudinary.com)
2. Dashboard → copy `Cloud name`, `API Key`, `API Secret`

### Gmail App Password (email alerts)
1. Enable 2-Step Verification on your Google account
2. Go to: Google Account → Security → App Passwords
3. Create one for "Farm Scout" → copy the 16-character password

### Google Sheets (record keeping)
1. Create a new Google Sheet (name it anything)
2. Google Cloud Console → Create project → Enable Sheets API + Drive API
3. Create Service Account → Download JSON key
4. Share your Sheet with the service account email (Editor access)
5. Copy the Sheet ID from its URL

### Adding / Removing Farms
In Streamlit Cloud Secrets, edit this line:
```
FARM_LIST = "Farm A, Farm B, Farm C, Other"
```
Redeploy is **not needed** — secrets update live.

---

## 📊 Google Sheet Columns

| Timestamp | Farm | Location | Issue Type | Description | Reporter | Latitude | Longitude | Photo URL | Severity |

---

## 📱 Tips for Farm Workers
- Works on **any smartphone browser** — no app install
- Tap **"Get My GPS Location"** before submitting
- Taking a photo is highly recommended but optional
- The form takes < 1 minute to complete

---

*Built for University of Kentucky Extension field teams.*
