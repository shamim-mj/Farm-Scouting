import streamlit as st
import gspread
import base64
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
from google.oauth2.service_account import Credentials
from PIL import Image
import smtplib
import datetime
import zoneinfo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import os

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="🌾 Robbie Williams Farms – Scout Report",
    page_icon="🌾",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
        background-color: #f4f6f0;
    }
    .hero {
        background: linear-gradient(150deg, #1b4332 0%, #2d6a4f 45%, #52b788 100%);
        border-radius: 20px; padding: 30px 24px 22px 24px;
        text-align: center; margin-bottom: 6px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.22);
        position: relative; overflow: hidden;
    }
    .hero::before { content:""; position:absolute; top:-40px; right:-40px;
        width:160px; height:160px; background:rgba(255,255,255,0.06); border-radius:50%; }
    .hero::after  { content:""; position:absolute; bottom:-50px; left:-30px;
        width:200px; height:200px; background:rgba(255,255,255,0.04); border-radius:50%; }
    .hero-icon  { font-size:3rem; margin-bottom:4px; line-height:1; }
    .hero-title { font-size:1.85rem; font-weight:800; color:#ffffff; margin:0;
        letter-spacing:0.5px; text-shadow:0 2px 8px rgba(0,0,0,0.3); }
    .hero-sub   { font-size:1rem; color:#b7e4c7; margin:6px 0 0 0;
        font-weight:500; letter-spacing:1.5px; text-transform:uppercase; }
    .hero-divider { width:60px; height:3px; background:#74c69d;
        border-radius:4px; margin:12px auto 0 auto; }
    .tagline { background:#d8f3dc; border-radius:0 0 14px 14px;
        text-align:center; padding:8px 16px; font-size:0.88rem;
        color:#1b4332; font-weight:600; margin-bottom:20px; }
    .section-card { background:#ffffff; border-left:5px solid #52b788;
        border-radius:12px; padding:14px 18px;
        margin:16px 0 8px 0; box-shadow:0 2px 8px rgba(0,0,0,0.06); }
    .section-title { font-size:1.1rem; font-weight:700; color:#1b4332; margin:0; }
    .step-badge { display:inline-flex; align-items:center; justify-content:center;
        background:#2d6a4f; color:white; border-radius:50%;
        width:28px; height:28px; font-weight:bold;
        margin-right:8px; font-size:0.9rem; flex-shrink:0; }
    .stButton > button { width:100%; height:58px; font-size:1.15rem; font-weight:700;
        border-radius:14px; background:linear-gradient(135deg,#1b4332,#2d6a4f);
        color:white; border:none; box-shadow:0 5px 15px rgba(27,67,50,0.35);
        transition:all 0.2s; letter-spacing:0.3px; }
    .stButton > button:hover { background:linear-gradient(135deg,#081c15,#1b4332);
        transform:translateY(-2px); box-shadow:0 8px 20px rgba(27,67,50,0.4); }
    .success-box { background:linear-gradient(135deg,#d8f3dc,#b7e4c7);
        border:2px solid #52b788; border-radius:16px; padding:22px;
        text-align:center; font-size:1.05rem; color:#1b4332;
        box-shadow:0 4px 12px rgba(82,183,136,0.2); }
    .error-box { background:#ffebee; border:2px solid #e53935;
        border-radius:12px; padding:14px; font-size:1rem; color:#b71c1c; }
    .stSelectbox > div > div,
    .stTextArea > div > textarea,
    .stTextInput > div > input { font-size:1.05rem !important; border-radius:10px !important; }
    .footer { text-align:center; color:#95a5a6; font-size:0.8rem;
        margin-top:36px; padding-bottom:24px;
        border-top:1px solid #e8f5e9; padding-top:16px; }
    .footer strong { color:#2d6a4f; }
    #MainMenu {visibility:hidden;} footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)

def get_timestamp():
    try:
        return datetime.datetime.now(
            zoneinfo.ZoneInfo("America/Chicago")
        ).strftime("%Y-%m-%d %H:%M:%S CDT")
    except Exception:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─────────────────────────────────────────────
#  CLOUDINARY
# ─────────────────────────────────────────────
def setup_cloudinary():
    if not CLOUDINARY_AVAILABLE:
        return False
    cn  = get_secret("CLOUDINARY_CLOUD_NAME")
    ak  = get_secret("CLOUDINARY_API_KEY")
    ase = get_secret("CLOUDINARY_API_SECRET")
    if cn and ak and ase:
        cloudinary.config(cloud_name=cn, api_key=ak, api_secret=ase)
        return True
    return False

def compress_to_jpeg(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82, optimize=True)
    buf.seek(0)
    return buf.read()

def upload_to_cloudinary(raw, filename):
    try:
        jpeg = compress_to_jpeg(raw)
        res  = cloudinary.uploader.upload(
            jpeg, folder="robbie_williams_farms",
            public_id=filename, resource_type="image"
        )
        return res.get("secure_url", "")
    except Exception as e:
        return f"ERROR: {e}"

def image_to_b64(raw):
    try:
        jpeg = compress_to_jpeg(raw)
        return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    except Exception:
        return ""

# ─────────────────────────────────────────────
#  GOOGLE SHEETS
# ─────────────────────────────────────────────
def get_gsheet():
    try:
        sheet_id     = get_secret("GSHEET_ID")
        client_email = get_secret("CLIENT_EMAIL")
        private_key  = get_secret("PRIVATE_KEY")

        if not all([sheet_id, client_email, private_key]):
            st.error("❌ Missing one of: GSHEET_ID, CLIENT_EMAIL, PRIVATE_KEY")
            return None, None

        creds_dict = {
            "type":                        "service_account",
            "project_id":                  "farm-scout-510216",
            "private_key_id":              get_secret("PRIVATE_KEY_ID", ""),
            "private_key":                 private_key,
            "client_email":                client_email,
            "client_id":                   "",
            "auth_uri":                    "https://accounts.google.com/o/oauth2/auth",
            "token_uri":                   "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url":        f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
        }

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sh     = client.open_by_key(sheet_id)

        try:
            ws = sh.worksheet("Issues")
        except Exception:
            ws = sh.add_worksheet(title="Issues", rows=1000, cols=20)
            ws.append_row([
                "Timestamp", "Farm", "Location/Side", "Issue Type",
                "Description", "Reporter", "Latitude", "Longitude",
                "Photo URL", "Severity"
            ])
        return sh, ws
    except Exception as e:
        st.error(f"❌ Sheet connection error: {e}")
        return None, None

def save_to_gsheet(ws, row):
    try:
        ws.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ Sheet save error: {e}")
        return False

# ─────────────────────────────────────────────
#  EMAIL  (shared HTML builder)
# ─────────────────────────────────────────────
def build_email_html(issue_data, photo_src):
    sev_color = {
        "🔴 High – Urgent":    "#c62828",
        "🟡 Medium – Monitor": "#f9a825",
        "🟢 Low – Note it":    "#2e7d32",
    }.get(issue_data["severity"], "#555")

    photo_html = (
        f'<img src="{photo_src}" style="max-width:420px;border-radius:10px;margin-top:10px;"/>'
        if photo_src else "<em>No photo submitted.</em>"
    )
    maps = ""
    if issue_data.get("lat") not in ("N/A", ""):
        maps = (
            f'<br><a href="https://maps.google.com/?q={issue_data["lat"]},{issue_data["lon"]}" '
            f'style="color:#1976d2;">📍 View on Google Maps</a>'
        )

    return f"""
    <html><body style="font-family:Segoe UI,sans-serif;background:#f0f4f0;padding:20px;">
    <div style="max-width:600px;margin:auto;background:white;border-radius:16px;
                overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.12);">
      <div style="background:linear-gradient(135deg,#1b4332,#52b788);
                  padding:22px;text-align:center;color:white;">
        <div style="font-size:2rem;">🌾</div>
        <h2 style="margin:4px 0 0 0;font-size:1.4rem;">Robbie Williams Farms</h2>
        <p style="margin:4px 0 0 0;opacity:0.85;font-size:0.95rem;letter-spacing:1px;">
          FIELD SCOUT REPORT</p>
      </div>
      <div style="padding:22px;">
        <table style="width:100%;border-collapse:collapse;font-size:0.97rem;">
          <tr><td style="padding:9px 10px;font-weight:700;color:#555;width:36%;
                         border-bottom:1px solid #f0f0f0;">🏡 Farm</td>
              <td style="padding:9px 10px;border-bottom:1px solid #f0f0f0;font-weight:600;">
              {issue_data['farm']}</td></tr>
          <tr style="background:#f9fbe7;">
              <td style="padding:9px 10px;font-weight:700;color:#555;border-bottom:1px solid #f0f0f0;">
              📍 Location</td>
              <td style="padding:9px 10px;border-bottom:1px solid #f0f0f0;">
              {issue_data['location']}</td></tr>
          <tr><td style="padding:9px 10px;font-weight:700;color:#555;border-bottom:1px solid #f0f0f0;">
              ⚠️ Issue</td>
              <td style="padding:9px 10px;border-bottom:1px solid #f0f0f0;">
              {issue_data['issue_type']}</td></tr>
          <tr style="background:#f9fbe7;">
              <td style="padding:9px 10px;font-weight:700;color:#555;border-bottom:1px solid #f0f0f0;">
              🔥 Severity</td>
              <td style="padding:9px 10px;border-bottom:1px solid #f0f0f0;
                         font-weight:700;color:{sev_color};">{issue_data['severity']}</td></tr>
          <tr><td style="padding:9px 10px;font-weight:700;color:#555;border-bottom:1px solid #f0f0f0;">
              👤 Reporter</td>
              <td style="padding:9px 10px;border-bottom:1px solid #f0f0f0;">
              {issue_data['reporter']}</td></tr>
          <tr style="background:#f9fbe7;">
              <td style="padding:9px 10px;font-weight:700;color:#555;">🕒 Time</td>
              <td style="padding:9px 10px;">{issue_data['timestamp']}</td></tr>
          <tr><td style="padding:9px 10px;font-weight:700;color:#555;">🗺️ GPS</td>
              <td style="padding:9px 10px;">
              {issue_data.get('lat','N/A')}, {issue_data.get('lon','N/A')}{maps}</td></tr>
        </table>
        <div style="background:#fff8e1;border-left:4px solid #fb8c00;
                    border-radius:8px;padding:14px;margin-top:16px;">
          <strong>📝 Description:</strong><br>
          <span style="font-size:0.97rem;line-height:1.6;">{issue_data['description']}</span>
        </div>
        <div style="margin-top:18px;">
          <strong>📷 Photo:</strong><br>{photo_html}
        </div>
      </div>
      <div style="background:#f1f8f4;padding:12px;text-align:center;
                  font-size:0.78rem;color:#888;border-top:1px solid #e0e0e0;">
        🌾 Robbie Williams Farms – Field Scout App | {issue_data['timestamp']}
      </div>
    </div>
    </body></html>"""

def send_email(issue_data, photo_src, receiver):
    """Send email to any receiver using shared HTML builder."""
    try:
        sender   = get_secret("EMAIL_SENDER")
        password = get_secret("EMAIL_PASSWORD")
        if not all([sender, password, receiver]):
            return False, "Email secrets missing"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 Scout Report – {issue_data['farm']} | {issue_data['issue_type']}"
        msg["From"]    = sender
        msg["To"]      = receiver
        msg.attach(MIMEText(build_email_html(issue_data, photo_src), "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)

# ─────────────────────────────────────────────
#  LISTS
# ─────────────────────────────────────────────
FARMS = [
    "🌱 Select a farm…",
    "Abbott (Bruce) – 27 Crop Acres",
    "Allen (Jennings) – 390 Crop Acres",
    "Allen (Matthew) – 181 Crop Acres",
    "Allgood (Lower) – 209 Crop Acres",
    "Allgood (Upper) – 45 Crop Acres",
    "Alves – 204 Crop Acres",
    "Ashworth – 14 Crop Acres",
    "Bennett – 15 Crop Acres",
    "Book McLevian – 187 Crop Acres",
    "Bugg (Wayne) – 68 Crop Acres",
    "Community College – 65 Crop Acres",
    "Dawson & Parker – 100 Crop Acres",
    "Dawson (Coraville) – 50 Crop Acres",
    "Dempewolf (Griffin) – 126 Crop Acres",
    "Dempewolf (Goben) – 90 Crop Acres",
    "Dempewolf (Ben Moss) – 116 Crop Acres",
    "Dempewolf (Cool Springs) – 229 Crop Acres",
    "Dempewolf (Farley) – 183 Crop Acres",
    "Dempewolf (Kimsey Ln) – 67 Crop Acres",
    "Dempewolf (Pearson) – 134 Crop Acres",
    "Dempewolf (Triplet) – 170 Crop Acres",
    "Dempewolf (by Wellmeier) – 25 Crop Acres",
    "Haynes (Terry) – 32 Crop Acres",
    "Haynes (Troy) – 151 Crop Acres",
    "Ijames (Lower) – 71 Crop Acres",
    "Ijames (Upper) – 65 Crop Acres",
    "Jones (Pete) – Crop Acres",
    "Keach Airline Road – 526 Crop Acres",
    "Keach Home – 585 Crop Acres",
    "McCollom – 113 Crop Acres",
    "McConathy – 218 Crop Acres",
    "McConathy (Rucker Rd) – 67 Crop Acres",
    "Reed North – 508 Crop Acres",
    "Reed South – 136 Crop Acres",
    "Sawyer (Silas) – 12 Crop Acres",
    "Staples – 200 Crop Acres",
    "VIP – 122 Crop Acres",
    "Williams (Dan) – 79 Crop Acres",
    "Williams Thrasher Busby – 274 Crop Acres",
]

ISSUE_TYPES = [
    "🌿 Select issue type…",
    "🍄 Disease / Fungal",
    "🔧 Equipment / Infrastructure",
    "🌾 Nutrient Deficiency",
    "🐛 Pest / Insect Damage",
    "📉 Soil Compaction",
    "⏳ Soil Erosion",
    "💨 Spray / Drift Damage",
    "💧 Water / Flooding Problem",
    "🌩️ Weather / Storm Damage",
    "🌿 Weed Pressure",
    "🐾 Wildlife / Animal Damage",
    "⚠️ Other",
]

FARM_SIDES = [
    "📍 Select location…",
    "🗺️ Entire Field",
    "🎯 Center / Middle",
    "⬆️ North End",
    "⬇️ South End",
    "➡️ East Side",
    "⬅️ West Side",
    "🚜 End Rows / Turn Rows",
    "🚜 Headlands",
    "📉 Low Spot / Swale",
    "⛰️ Terrace Top / Ridge",
    "🚧 Field Border / Edge",
    "🌳 Left Tree Line",
    "🌳 Right Tree Line",
    "🚗 Near Entrance",
    "🌊 Near Waterway / Ditch",
    "🛣️ Roadside",
    "📝 Other – see description",
]

# ─────────────────────────────────────────────
#  GPS  — uses st.components.v1.html (supports JS)
#          with full page reload to fill lat/lon
# ─────────────────────────────────────────────
GPS_HTML = """
<div id="gps_status" style="margin:6px 0;">
  <button onclick="getLocation()" id="gps_btn"
    style="background:linear-gradient(135deg,#1b4332,#2d6a4f);color:white;border:none;
           border-radius:12px;padding:14px 18px;font-size:1.05rem;font-weight:700;
           cursor:pointer;width:100%;box-shadow:0 4px 12px rgba(27,67,50,0.3);">
    📡 Tap to Get My GPS Location
  </button>
  <div id="coords" style="margin-top:10px;font-size:0.95rem;color:#333;"></div>
  <div id="gps_help" style="display:none;background:#fff8e1;border:1px solid #f9a825;
       border-radius:10px;padding:12px;margin-top:10px;font-size:0.88rem;
       color:#555;line-height:1.7;">
    <strong>📋 How to allow location:</strong><br>
    <b>iPhone:</b> Settings → Safari → Location → Allow<br>
    <b>Android:</b> Tap 🔒 in address bar → Site Settings → Location → Allow<br><br>
    <strong>📍 Manual:</strong> Open
    <a href="https://maps.google.com" target="_blank" style="color:#1976d2;">Google Maps</a>,
    long-press your spot → copy the numbers at the top.
  </div>
</div>
<script>
function getLocation() {
  var btn  = document.getElementById('gps_btn');
  var info = document.getElementById('coords');
  var help = document.getElementById('gps_help');
  btn.textContent = '⏳ Getting location…';
  btn.disabled = true;
  help.style.display = 'none';

  if (!navigator.geolocation) {
    info.innerHTML = '❌ GPS not supported. Enter coordinates manually below.';
    help.style.display = 'block';
    btn.textContent = '📡 GPS Not Available';
    btn.disabled = false;
    return;
  }

  navigator.geolocation.getCurrentPosition(
    function(pos) {
      var lat = pos.coords.latitude.toFixed(6);
      var lon = pos.coords.longitude.toFixed(6);
      // ✅ Full page reload with GPS params — Streamlit picks them up automatically
      var url = new URL(window.parent.location.href);
      url.searchParams.set('lat', lat);
      url.searchParams.set('lon', lon);
      window.parent.location.href = url.toString();
    },
    function(err) {
      var msgs = {
        1: '🚫 Location blocked. See help below, then tap again.',
        2: '📶 Location unavailable. Try moving outside.',
        3: '⏱️ Timed out. Try again or enter manually below.'
      };
      info.innerHTML = '<span style="color:#c62828;">' +
        (msgs[err.code] || '❌ ' + err.message) + '</span>';
      help.style.display = 'block';
      btn.textContent = '📡 Tap to Retry GPS';
      btn.disabled = false;
    },
    {enableHighAccuracy: true, timeout: 12000, maximumAge: 0}
  );
}
</script>
"""

# ─────────────────────────────────────────────
#  PDF SECTION
# ─────────────────────────────────────────────
def show_pdf_section():
    pdf_url = get_secret("FARM_PDF_URL", "")
    st.markdown("""
    <div class="section-card">
      <div class="section-title">📄 &nbsp;Farm Field Reference Map</div>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("📄 Tap to View Farm Fields & Acreage Guide", expanded=False):
        if pdf_url:
            st.iframe(pdf_url, height=560)
            st.caption("👆 Scroll inside the document to view all farm fields and acreage.")
        else:
            st.warning("⚠️ Farm PDF not configured. Add `FARM_PDF_URL` to Streamlit secrets.")

# ─────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────
def main():

    st.markdown("""
    <div class="hero">
      <div class="hero-icon">🌾</div>
      <h1 class="hero-title">Robbie Williams Farms</h1>
      <p class="hero-sub">Field Scout Report</p>
      <div class="hero-divider"></div>
    </div>
    <div class="tagline">
      📋 Report a field issue quickly — photo, location &amp; GPS included
    </div>
    """, unsafe_allow_html=True)

    cloudinary_ok = setup_cloudinary()
    _, gsheet_ws  = get_gsheet()

    show_pdf_section()

    # ── Read GPS from URL params ──────────────
    # ✅ FIX: read lat/lon from query params and pre-fill inputs
    params  = st.query_params
    gps_lat = params.get("lat", "")
    gps_lon = params.get("lon", "")

    # Show green banner if GPS was just captured
    if gps_lat and gps_lon:
        st.success(f"📍 GPS captured: **{gps_lat}**, **{gps_lon}** — coordinates filled below ✅")

    # STEP 1
    st.markdown("""
    <div class="section-card">
      <div class="section-title"><span class="step-badge">1</span>Where is the problem?</div>
    </div>
    """, unsafe_allow_html=True)

    farm_selected = st.selectbox("🏡 Choose Farm", FARMS, index=0)
    side_selected = st.selectbox("📍 Which Part of the Farm?", FARM_SIDES, index=0)

    # ── GPS button ────────────────────────────
    st.markdown("**📡 GPS Coordinates** — tap the button below on your phone")
    # ✅ KEY FIX: use st.components.v1.html — it runs JavaScript correctly
    # st.html() does NOT support JS; st.iframe() is for URLs not HTML strings
    st.components.v1.html(GPS_HTML, height=160)

    st.caption("🔒 GPS blocked? Enter coordinates manually (Google Maps → long-press → copy numbers).")

    lat_col, lon_col = st.columns(2)
    with lat_col:
        # ✅ FIX: pre-filled from URL params after GPS capture
        lat_input = st.text_input("Latitude",  value=gps_lat, placeholder="e.g. 37.989450")
    with lon_col:
        lon_input = st.text_input("Longitude", value=gps_lon, placeholder="e.g. -87.590321")

    # STEP 2
    st.markdown("""
    <div class="section-card">
      <div class="section-title"><span class="step-badge">2</span>What is the problem?</div>
    </div>
    """, unsafe_allow_html=True)

    issue_type  = st.selectbox("⚠️ Type of Issue", ISSUE_TYPES, index=0)
    severity    = st.radio(
        "🔥 How serious is it?",
        ["🔴 High – Urgent", "🟡 Medium – Monitor", "🟢 Low – Note it"],
        horizontal=True,
    )
    description = st.text_area(
        "📝 Describe the problem",
        placeholder="e.g. Yellowing leaves on the north corner, about 10 rows affected.",
        height=130,
    )

    # STEP 3
    st.markdown("""
    <div class="section-card">
      <div class="section-title">
        <span class="step-badge">3</span>Take or Upload a Photo 📷
        <em style="font-weight:400;font-size:0.88rem;color:#555;"> — Highly Recommended</em>
      </div>
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
            st.image(Image.open(photo_file), caption="📷 Photo Preview", use_container_width=True)
        except Exception:
            st.warning("Could not preview photo, but it will still be submitted.")

    # STEP 4
    st.markdown("""
    <div class="section-card">
      <div class="section-title"><span class="step-badge">4</span>Your Name</div>
    </div>
    """, unsafe_allow_html=True)

    reporter_name = st.text_input("👤 Your Name", placeholder="e.g. John Smith")

    st.markdown("---")

    if st.button("🚀 Submit Scout Report", use_container_width=True):

        errors = []
        if farm_selected.startswith("🌱"):  errors.append("Please select a farm.")
        if side_selected.startswith("📍"):  errors.append("Please select the farm location/side.")
        if issue_type.startswith("🌿"):     errors.append("Please select an issue type.")
        if not description.strip():         errors.append("Please describe the problem.")
        if not reporter_name.strip():       errors.append("Please enter your name.")

        if errors:
            st.markdown(
                '<div class="error-box">⚠️ <strong>Please fix these:</strong><br>• '
                + "<br>• ".join(errors) + "</div>",
                unsafe_allow_html=True,
            )
            st.stop()

        progress  = st.progress(0, text="Submitting…")
        timestamp = get_timestamp()
        photo_url = ""
        photo_b64 = ""

        # Upload photo
        progress.progress(20, text="Uploading photo…")
        if photo_file:
            photo_file.seek(0)
            raw   = photo_file.read()
            safe  = farm_selected[:30].replace(" ", "_").replace("/", "-")
            fname = f"{safe}_{timestamp.replace(' ','_').replace(':','-')}"
            if cloudinary_ok:
                photo_url = upload_to_cloudinary(raw, fname)
                if photo_url.startswith("ERROR"):
                    photo_b64 = image_to_b64(raw)
            else:
                photo_b64 = image_to_b64(raw)
                photo_url = "embedded-in-email"

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

        # Google Sheets
        progress.progress(50, text="Saving record…")
        sheet_ok = False
        if gsheet_ws:
            sheet_ok = save_to_gsheet(gsheet_ws, [
                timestamp, farm_selected, side_selected, issue_type,
                description.strip(), reporter_name.strip(),
                lat_input or "N/A", lon_input or "N/A", photo_url, severity,
            ])

        # Emails
        progress.progress(75, text="Sending notifications…")
        email_src = (
            photo_url if (photo_url and not photo_url.startswith("ERROR")
                          and photo_url != "embedded-in-email")
            else photo_b64
        )
        receiver1    = get_secret("EMAIL_RECEIVER",  "")
        receiver2    = get_secret("EMAIL_RECEIVER2", "")
        email1_ok, email1_msg = send_email(issue_data, email_src, receiver1)
        email2_ok, email2_msg = send_email(issue_data, email_src, receiver2)

        progress.progress(100, text="Done!")

        # Status lines
        lines = []
        if not photo_file:
            lines.append("📷 No photo submitted")
        elif photo_url and not photo_url.startswith("ERROR") and photo_url != "embedded-in-email":
            lines.append("✅ Photo saved to Cloudinary")
        elif photo_b64:
            lines.append("✅ Photo embedded in email")
        else:
            lines.append("⚠️ Photo could not be processed")

        lines.append("✅ Record saved to Google Sheets" if sheet_ok  else "⚠️ Sheet not saved – check config")
        lines.append("✅ Email sent to Shamim"          if email1_ok else f"⚠️ Email 1 not sent ({email1_msg})")
        lines.append("✅ Email sent to Robbie"          if email2_ok else f"⚠️ Email 2 not sent ({email2_msg})")

        st.markdown(f"""
        <div class="success-box">
          <div style="font-size:2.8rem;">✅</div>
          <strong style="font-size:1.25rem;">Scout Report Submitted!</strong><br><br>
          {"<br>".join(lines)}
          <br><br>
          <span style="font-size:0.88rem;color:#2d6a4f;">📅 {timestamp}</span>
        </div>
        """, unsafe_allow_html=True)

        # Clear GPS params after submit
        st.query_params.clear()

    st.markdown("""
    <div class="footer">
      🌾 <strong>Robbie Williams Farms</strong> &nbsp;|&nbsp;
      Field Scout App &nbsp;|&nbsp; Henderson, KY
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
