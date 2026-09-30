import streamlit as st
import cloudinary
import cloudinary.uploader
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import datetime
import io
import json
import os

# ─────────────────────────────────────────────
#  PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🌾 Farm Scout",
    page_icon="🌾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  MOBILE-FIRST CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Global font + background */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }

    /* Big friendly top banner */
    .banner {
        background: linear-gradient(135deg, #2e7d32, #66bb6a);
        color: white;
        border-radius: 16px;
        padding: 22px 20px 16px 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .banner h1 { font-size: 2rem; margin: 0; }
    .banner p  { font-size: 1rem; margin: 6px 0 0 0; opacity: 0.9; }

    /* Section cards */
    .section-card {
        background: #f9fbe7;
        border-left: 5px solid #66bb6a;
        border-radius: 10px;
        padding: 14px 16px;
        margin: 14px 0;
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #2e7d32;
        margin-bottom: 6px;
    }

    /* Make buttons BIG for farm workers */
    .stButton > button {
        width: 100%;
        height: 56px;
        font-size: 1.1rem;
        font-weight: 700;
        border-radius: 12px;
        background: linear-gradient(135deg, #2e7d32, #43a047);
        color: white;
        border: none;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        transition: 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1b5e20, #2e7d32);
        transform: translateY(-1px);
    }

    /* Success / error boxes */
    .success-box {
        background: #e8f5e9;
        border: 2px solid #43a047;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        font-size: 1.1rem;
        color: #1b5e20;
    }
    .error-box {
        background: #ffebee;
        border: 2px solid #e53935;
        border-radius: 12px;
        padding: 14px;
        font-size: 1rem;
        color: #b71c1c;
    }

    /* Larger select / text inputs */
    .stSelectbox > div > div,
    .stTextArea > div > textarea,
    .stTextInput > div > input {
        font-size: 1.05rem !important;
    }

    /* GPS pill */
    .gps-pill {
        display: inline-block;
        background: #e3f2fd;
        border: 1px solid #42a5f5;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.9rem;
        color: #0d47a1;
        margin-top: 6px;
    }
    
    /* Step numbers */
    .step-badge {
        display: inline-block;
        background: #2e7d32;
        color: white;
        border-radius: 50%;
        width: 28px; height: 28px;
        line-height: 28px;
        text-align: center;
        font-weight: bold;
        margin-right: 8px;
        font-size: 0.95rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SECRETS / CONFIG
# ─────────────────────────────────────────────
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)

# ─────────────────────────────────────────────
#  CLOUDINARY SETUP
# ─────────────────────────────────────────────
def setup_cloudinary():
    cloud_name = get_secret("CLOUDINARY_CLOUD_NAME")
    api_key    = get_secret("CLOUDINARY_API_KEY")
    api_secret = get_secret("CLOUDINARY_API_SECRET")
    if cloud_name and api_key and api_secret:
        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
        return True
    return False

def upload_to_cloudinary(image_bytes, filename):
    try:
        result = cloudinary.uploader.upload(
            image_bytes,
            folder="farm_scout",
            public_id=filename,
            resource_type="image",
        )
        return result.get("secure_url", "")
    except Exception as e:
        return f"ERROR: {e}"

# ─────────────────────────────────────────────
#  GOOGLE SHEETS SETUP
# ─────────────────────────────────────────────
def get_gsheet():
    try:
        creds_raw = get_secret("GSHEET_CREDENTIALS")
        if not creds_raw:
            return None, None
        if isinstance(creds_raw, str):
            creds_dict = json.loads(creds_raw)
        else:
            creds_dict = dict(creds_raw)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet_id = get_secret("GSHEET_ID")
        sh = client.open_by_key(sheet_id)
        try:
            ws = sh.worksheet("Issues")
        except Exception:
            ws = sh.add_worksheet(title="Issues", rows=1000, cols=20)
            ws.append_row([
                "Timestamp", "Farm", "Location/Side", "Issue Type",
                "Description", "Reporter Name", "Latitude", "Longitude",
                "Photo URL", "Severity"
            ])
        return sh, ws
    except Exception as e:
        return None, None

def save_to_gsheet(ws, row_data):
    try:
        ws.append_row(row_data)
        return True
    except Exception as e:
        return False

# ─────────────────────────────────────────────
#  EMAIL NOTIFICATION
# ─────────────────────────────────────────────
def send_email_notification(issue_data, photo_url):
    try:
        sender_email   = get_secret("EMAIL_SENDER")
        sender_pass    = get_secret("EMAIL_PASSWORD")
        receiver_email = get_secret("EMAIL_RECEIVER")
        if not all([sender_email, sender_pass, receiver_email]):
            return False, "Email secrets missing"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 Farm Issue Reported – {issue_data['farm']} | {issue_data['issue_type']}"
        msg["From"]    = sender_email
        msg["To"]      = receiver_email

        severity_color = {
            "🔴 High – Urgent":   "#e53935",
            "🟡 Medium – Monitor":"#f9a825",
            "🟢 Low – Note it":   "#43a047",
        }.get(issue_data["severity"], "#555")

        photo_html = (
            f'<img src="{photo_url}" style="max-width:400px;border-radius:10px;margin-top:10px;" />'
            if photo_url and not photo_url.startswith("ERROR") else
            "<p><em>No photo attached.</em></p>"
        )

        maps_link = ""
        if issue_data.get("lat") and issue_data.get("lon"):
            maps_link = (
                f'<a href="https://maps.google.com/?q={issue_data["lat"]},{issue_data["lon"]}" '
                f'style="color:#1976d2;">📍 View on Google Maps</a>'
            )

        html = f"""
        <html><body style="font-family:Segoe UI,sans-serif;background:#f5f5f5;padding:20px;">
          <div style="background:white;border-radius:14px;padding:24px;max-width:600px;margin:auto;
                      box-shadow:0 2px 10px rgba(0,0,0,0.1);">
            <div style="background:linear-gradient(135deg,#2e7d32,#66bb6a);color:white;
                        border-radius:10px;padding:16px;text-align:center;margin-bottom:20px;">
              <h2 style="margin:0;">🌾 Farm Scout – Issue Report</h2>
            </div>
            <table style="width:100%;border-collapse:collapse;">
              <tr><td style="padding:8px;font-weight:bold;color:#555;width:38%;">🏡 Farm</td>
                  <td style="padding:8px;font-size:1.05rem;">{issue_data['farm']}</td></tr>
              <tr style="background:#f9fbe7;">
                  <td style="padding:8px;font-weight:bold;color:#555;">📍 Location/Side</td>
                  <td style="padding:8px;">{issue_data['location']}</td></tr>
              <tr><td style="padding:8px;font-weight:bold;color:#555;">⚠️ Issue Type</td>
                  <td style="padding:8px;">{issue_data['issue_type']}</td></tr>
              <tr style="background:#f9fbe7;">
                  <td style="padding:8px;font-weight:bold;color:#555;">🔥 Severity</td>
                  <td style="padding:8px;color:{severity_color};font-weight:bold;">{issue_data['severity']}</td></tr>
              <tr><td style="padding:8px;font-weight:bold;color:#555;">👤 Reporter</td>
                  <td style="padding:8px;">{issue_data['reporter']}</td></tr>
              <tr style="background:#f9fbe7;">
                  <td style="padding:8px;font-weight:bold;color:#555;">🕒 Time</td>
                  <td style="padding:8px;">{issue_data['timestamp']}</td></tr>
              <tr><td style="padding:8px;font-weight:bold;color:#555;">🗺️ GPS</td>
                  <td style="padding:8px;">{issue_data.get('lat','N/A')}, {issue_data.get('lon','N/A')}<br>{maps_link}</td></tr>
            </table>
            <div style="background:#fff3e0;border-left:4px solid #fb8c00;border-radius:6px;
                        padding:14px;margin-top:16px;">
              <strong>📝 Description:</strong><br>
              <span style="font-size:1rem;">{issue_data['description']}</span>
            </div>
            <div style="margin-top:16px;">
              <strong>📷 Photo:</strong><br>
              {photo_html}
            </div>
            <p style="color:#999;font-size:0.8rem;margin-top:20px;text-align:center;">
              Sent by Farm Scout App • {issue_data['timestamp']}
            </p>
          </div>
        </body></html>
        """

        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)

# ─────────────────────────────────────────────
#  FARM LIST  (editable in secrets)
# ─────────────────────────────────────────────
def get_farm_list():
    try:
        farms_raw = get_secret("FARM_LIST")
        if farms_raw:
            if isinstance(farms_raw, str):
                return [f.strip() for f in farms_raw.split(",") if f.strip()]
            return list(farms_raw)
    except Exception:
        pass
    # Default starter farms – replace in secrets
    return [
        "🌱 Select a farm…",
        "Lee Farm – North",
        "Lee Farm – South",
        "Knott Farm",
        "UK Research Farm",
        "Henderson Farm",
        "Other",
    ]

ISSUE_TYPES = [
    "🌿 Select issue type…",
    "🐛 Pest / Insect Damage",
    "🍄 Disease / Fungal",
    "🌾 Nutrient Deficiency",
    "💧 Water / Irrigation Problem",
    "🌿 Weed Pressure",
    "🔧 Equipment / Infrastructure",
    "🌩️ Weather / Storm Damage",
    "🐾 Wildlife / Animal Damage",
    "⚠️ Other",
]

FARM_SIDES = [
    "📍 Select location…",
    "North End",
    "South End",
    "East Side",
    "West Side",
    "Center / Middle",
    "Entire Field",
    "Near Entrance",
    "Near Waterway / Ditch",
    "Headlands",
    "Other – see description",
]

# ─────────────────────────────────────────────
#  GPS COMPONENT  (HTML5 Geolocation via JS)
# ─────────────────────────────────────────────
GPS_COMPONENT = """
<div id="gps_status" style="margin:6px 0;">
  <button onclick="getLocation()"
    style="background:#1976d2;color:white;border:none;border-radius:8px;
           padding:10px 18px;font-size:1rem;cursor:pointer;width:100%;">
    📡 Get My GPS Location
  </button>
  <div id="coords" style="margin-top:8px;font-size:0.9rem;color:#555;"></div>
</div>
<script>
function getLocation() {
  var btn = document.querySelector('#gps_status button');
  btn.textContent = '⏳ Getting location…';
  btn.disabled = true;
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        var lat = pos.coords.latitude.toFixed(6);
        var lon = pos.coords.longitude.toFixed(6);
        document.getElementById('coords').innerHTML =
          '✅ <strong>Lat:</strong> ' + lat + ' | <strong>Lon:</strong> ' + lon;
        // Push into Streamlit via query param trick
        var url = new URL(window.location.href);
        url.searchParams.set('lat', lat);
        url.searchParams.set('lon', lon);
        window.history.replaceState({}, '', url);
        btn.textContent = '✅ Location Captured!';
      },
      function(err) {
        document.getElementById('coords').innerHTML =
          '❌ Could not get location: ' + err.message;
        btn.textContent = '📡 Retry GPS';
        btn.disabled = false;
      },
      {enableHighAccuracy: true, timeout: 10000}
    );
  } else {
    document.getElementById('coords').innerHTML = '❌ GPS not supported on this device.';
    btn.disabled = false;
  }
}
</script>
"""

# ─────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────
def main():
    # ── Banner ──────────────────────────────
    st.markdown("""
    <div class="banner">
      <h1>🌾 Farm Scout</h1>
      <p>Report a field issue quickly &amp; easily</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Setup services ───────────────────────
    cloudinary_ok = setup_cloudinary()
    _, gsheet_ws  = get_gsheet()

    farms      = get_farm_list()
    issue_types = ISSUE_TYPES
    sides       = FARM_SIDES

    # ── Read GPS from URL params (set by JS) ─
    params  = st.query_params
    gps_lat = params.get("lat", "")
    gps_lon = params.get("lon", "")

    # ════════════════════════════════════════
    #  STEP 1 – Farm & Location
    # ════════════════════════════════════════
    st.markdown("""
    <div class="section-card">
      <div class="section-title"><span class="step-badge">1</span>Where is the problem?</div>
    </div>
    """, unsafe_allow_html=True)

    farm_selected = st.selectbox("🏡 Choose Farm", farms, index=0)
    side_selected = st.selectbox("📍 Which Part of the Farm?", sides, index=0)

    # ── GPS ──────────────────────────────────
    st.markdown("**📡 GPS Coordinates** *(tap button on your phone)*")
    st.components.v1.html(GPS_COMPONENT, height=110)

    lat_col, lon_col = st.columns(2)
    with lat_col:
        lat_input = st.text_input("Latitude", value=gps_lat, placeholder="auto-filled")
    with lon_col:
        lon_input = st.text_input("Longitude", value=gps_lon, placeholder="auto-filled")

    # ════════════════════════════════════════
    #  STEP 2 – Issue Details
    # ════════════════════════════════════════
    st.markdown("""
    <div class="section-card">
      <div class="section-title"><span class="step-badge">2</span>What is the problem?</div>
    </div>
    """, unsafe_allow_html=True)

    issue_type = st.selectbox("⚠️ Type of Issue", issue_types, index=0)
    severity   = st.radio(
        "🔥 How serious is it?",
        ["🔴 High – Urgent", "🟡 Medium – Monitor", "🟢 Low – Note it"],
        horizontal=True,
    )
    description = st.text_area(
        "📝 Describe the problem",
        placeholder="e.g. Yellowing leaves on the north corner, about 10 rows affected. Looks like nitrogen deficiency.",
        height=130,
    )

    # ════════════════════════════════════════
    #  STEP 3 – Photo
    # ════════════════════════════════════════
    st.markdown("""
    <div class="section-card">
      <div class="section-title"><span class="step-badge">3</span>Take or Upload a Photo 📷 <em style="font-weight:normal;font-size:0.9rem;">(Highly Recommended)</em></div>
    </div>
    """, unsafe_allow_html=True)

    photo_file = st.file_uploader(
        "Tap to take a photo or choose from gallery",
        type=["jpg", "jpeg", "png", "heic", "webp"],
        accept_multiple_files=False,
        help="Use your phone camera for best results",
    )

    if photo_file:
        try:
            img = Image.open(photo_file)
            st.image(img, caption="📷 Photo Preview", use_container_width=True)
        except Exception:
            st.warning("Could not preview photo, but it will still be submitted.")

    # ════════════════════════════════════════
    #  STEP 4 – Reporter Name
    # ════════════════════════════════════════
    st.markdown("""
    <div class="section-card">
      <div class="section-title"><span class="step-badge">4</span>Your Name</div>
    </div>
    """, unsafe_allow_html=True)

    reporter_name = st.text_input("👤 Your Name", placeholder="e.g. John Smith")

    # ════════════════════════════════════════
    #  SUBMIT
    # ════════════════════════════════════════
    st.markdown("---")

    if st.button("🚀 Submit Issue Report", use_container_width=True):

        # ── Validation ───────────────────────
        errors = []
        if farm_selected.startswith("🌱"):
            errors.append("Please select a farm.")
        if side_selected.startswith("📍"):
            errors.append("Please select the farm location/side.")
        if issue_type.startswith("🌿"):
            errors.append("Please select an issue type.")
        if not description.strip():
            errors.append("Please describe the problem.")
        if not reporter_name.strip():
            errors.append("Please enter your name.")

        if errors:
            st.markdown(
                '<div class="error-box">⚠️ <strong>Please fix these:</strong><br>• '
                + "<br>• ".join(errors) + "</div>",
                unsafe_allow_html=True,
            )
            st.stop()

        # ── Progress ─────────────────────────
        progress = st.progress(0, text="Submitting…")

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        photo_url = ""

        # ── Upload photo to Cloudinary ────────
        progress.progress(20, text="Uploading photo…")
        if photo_file and cloudinary_ok:
            photo_file.seek(0)
            raw = photo_file.read()
            try:
                img_pil = Image.open(io.BytesIO(raw))
                if img_pil.mode in ("RGBA", "P"):
                    img_pil = img_pil.convert("RGB")
                buf = io.BytesIO()
                img_pil.save(buf, format="JPEG", quality=85)
                buf.seek(0)
                safe_farm = farm_selected.replace(" ", "_").replace("/", "-")
                fname = f"{safe_farm}_{timestamp.replace(' ','_').replace(':','-')}"
                photo_url = upload_to_cloudinary(buf.read(), fname)
            except Exception as ex:
                photo_url = f"ERROR: {ex}"
        elif photo_file and not cloudinary_ok:
            photo_url = "Cloudinary not configured"

        issue_data = {
            "farm":        farm_selected,
            "location":    side_selected,
            "issue_type":  issue_type,
            "severity":    severity,
            "description": description.strip(),
            "reporter":    reporter_name.strip(),
            "lat":         lat_input or "N/A",
            "lon":         lon_input or "N/A",
            "timestamp":   timestamp,
            "photo_url":   photo_url,
        }

        # ── Save to Google Sheets ─────────────
        progress.progress(50, text="Saving record…")
        sheet_ok = False
        if gsheet_ws:
            row = [
                timestamp,
                farm_selected,
                side_selected,
                issue_type,
                description.strip(),
                reporter_name.strip(),
                lat_input or "N/A",
                lon_input or "N/A",
                photo_url,
                severity,
            ]
            sheet_ok = save_to_gsheet(gsheet_ws, row)

        # ── Send email ────────────────────────
        progress.progress(75, text="Sending notification…")
        email_ok, email_msg = send_email_notification(issue_data, photo_url)

        progress.progress(100, text="Done!")

        # ── Result summary ────────────────────
        status_lines = []
        if photo_url and not photo_url.startswith("ERROR") and "not configured" not in photo_url:
            status_lines.append("✅ Photo saved to Cloudinary")
        elif photo_file:
            status_lines.append("⚠️ Photo upload issue – check Cloudinary config")
        else:
            status_lines.append("📷 No photo submitted")

        status_lines.append("✅ Record saved to Google Sheets" if sheet_ok else "⚠️ Sheet save skipped – check config")
        status_lines.append("✅ Email notification sent" if email_ok else f"⚠️ Email not sent ({email_msg})")

        st.markdown(f"""
        <div class="success-box">
          <div style="font-size:2.5rem;">✅</div>
          <strong style="font-size:1.3rem;">Issue Reported!</strong><br><br>
          {"<br>".join(status_lines)}
          <br><br>
          <span style="font-size:0.9rem;color:#555;">Submitted: {timestamp}</span>
        </div>
        """, unsafe_allow_html=True)

        if photo_url and not photo_url.startswith("ERROR") and "not configured" not in photo_url:
            st.image(photo_url, caption="📷 Saved Photo", use_container_width=True)

        # Clear GPS params
        st.query_params.clear()

    # ── Footer ────────────────────────────────
    st.markdown("""
    <div style="text-align:center;color:#aaa;font-size:0.8rem;margin-top:30px;padding-bottom:20px;">
      🌾 Farm Scout App • Built for Kentucky Field Teams
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
