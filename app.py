# --- TSEG Branded Attorney Bio Scraper (Streamlit) ---
# Drop this file in your repo as app.py

import time, re
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# -----------------------------
# Branding / Theme
# -----------------------------
TSEG_LOGO = "https://www.tseg.com/wp-content/uploads/2023/02/tseg-social-thumbnail.png"
ACCENT = "#0EA5E9"  # cyan-ish accent; easy to read on dark or light themes

st.set_page_config(
    page_title="TSEG • Attorney Bio Scraper",
    page_icon=TSEG_LOGO,
    layout="wide",
)

# Minimal CSS polish
st.markdown(
    f"""
    <style>
      /* Header bar */
      .tseg-header {{
        display:flex; align-items:center; gap:14px;
        padding:10px 16px; border-radius:14px;
        background: linear-gradient(135deg, rgba(14,165,233,0.18), rgba(14,165,233,0.06));
        border: 1px solid rgba(14,165,233,0.25);
        margin-bottom: 18px;
      }}
      .tseg-title {{
        font-weight: 700; font-size: 1.4rem; margin:0; line-height:1.2;
      }}
      .small-dim {{ color: rgba(255,255,255,0.65); }}
      .stButton>button {{
        border-radius: 12px; border:1px solid rgba(255,255,255,0.08);
        padding: 10px 14px; font-weight: 600;
      }}
      .stButton>button:hover {{ border-color: {ACCENT}55; }}
      .download-btn > button {{ border:1px solid {ACCENT}44; }}
      /* Dataframe corners */
      .stDataFrame div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow:hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
with st.container():
    c1, c2 = st.columns([1, 9])
    with c1:
        st.image(TSEG_LOGO, width=64)
    with c2:
        st.markdown(
            """
            <div class="tseg-header">
              <div>
                <h1 class="tseg-title">Attorney Bio Scraper — Conference Edition</h1>
                <div class="small-dim">Surface quick talking points from attorney biography pages (education, hobbies, pets, family, community).</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# -----------------------------
# Scraper utilities
# -----------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    )
}

HOBBY_WORDS = [
    "golf","skiing","hiking","reading","travel","cooking","fishing","boating",
    "tennis","running","cycling","yoga","camping","kayaking","photography",
    "music","piano","guitar","basketball","football","soccer","baseball"
]
PET_WORDS = ["dog","dogs","cat","cats","puppy","kitten","golden retriever","pets","animal lover"]
FAMILY_WORDS = ["husband","wife","spouse","partner","children","kids","daughter","son","mother","father","family","married"]
COMMUNITY_WORDS = ["volunteer","board member","foundation","nonprofit","mentor","coach","community","pro bono"]

def fetch_html(url: str, timeout: int = 25) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        st.session_state.setdefault("logs", []).append(f"[WARN] Fetch failed for {url}: {e}")
        return None

def nearest_block_with_name(soup: BeautifulSoup, name: str):
    lowered = name.lower()
    candidates = soup.find_all(string=lambda t: t and lowered in t.lower())
    for t in candidates:
        node = t.parent
        for _ in range(6):
            if not node: break
            if node.name in ("section","article","li","div"):
                if len(node.get_text(strip=True)) > 30:
                    return node
            node = node.parent
    return None

def extract_keywords(text: str, vocab: list[str]) -> str:
    found = []
    for word in vocab:
        if re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE):
            found.append(word)
    return ", ".join(sorted(set(found))) if found else ""

def extract_schools(text: str) -> tuple[str, str]:
    law = re.findall(r"([A-Z][A-Za-z&.\-,'\s]+(?:School of Law| Law)(?:,?\s*[A-Z][A-Za-z&.\-,'\s]+)*)", text)
    ug  = re.findall(r"([A-Z][A-Za-z&.\-,'\s]+(?:University|College)(?: of [A-Z][A-Za-z&.\-,'\s]+)*)", text)
    law_school = ", ".join(sorted(set([s.strip() for s in law if len(s) < 120])))
    undergrad  = ", ".join(sorted(set([s.strip() for s in ug  if len(s) < 120])))
    return law_school, undergrad

def scrape_one(url: str, target_name: str, timeout: int = 25) -> dict:
    html = fetch_html(url, timeout=timeout)
    if not html:
        return {
            "Name": target_name, "Law School": "", "Undergrad": "", "Hobbies": "",
            "Pets": "", "Family": "", "Community Involvement": "",
            "Bio Snippet": "Fetch error", "URL": url
        }
    soup = BeautifulSoup(html, "lxml")
    block = nearest_block_with_name(soup, target_name)
    text  = (block.get_text(" ", strip=True) if block else soup.get_text(" ", strip=True))
    law_school, undergrad = extract_schools(text)
    return {
        "Name": target_name,
        "Law School": law_school,
        "Undergrad": undergrad,
        "Hobbies":   extract_keywords(text, HOBBY_WORDS),
        "Pets":      extract_keywords(text, PET_WORDS),
        "Family":    extract_keywords(text, FAMILY_WORDS),
        "Community Involvement": extract_keywords(text, COMMUNITY_WORDS),
        "Bio Snippet": (text[:300] + "...") if len(text) > 300 else text,
        "URL": url,
    }

def normalize_input(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    url_col  = cols.get("url")
    name_col = cols.get("target name") or cols.get("name")
    if not url_col or not name_col:
        raise ValueError("CSV must contain columns: 'URL' and 'Target Name'")
    return df.rename(columns={url_col: "URL", name_col: "Target Name"})[["URL", "Target Name"]]

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    timeout = st.slider("Request timeout (seconds)", 5, 60, 25)
    st.caption("If a site is slow to respond, increase the timeout.")

# -----------------------------
# Main UI
# -----------------------------
if "logs" not in st.session_state:
    st.session_state["logs"] = []

st.subheader("1) Upload URL list (CSV)")
st.write("CSV must have columns: **URL** and **Target Name** (headers not case-sensitive).")
uploaded = st.file_uploader("Upload bio_urls.csv", type=["csv"])

with st.expander("📄 See sample CSV"):
    st.code(
        "URL,Target Name\n"
        "https://friedmanlawfirm.com/about-our-law-firm/,Alda Gojcaj\n"
        "http://boustanylawfirm.com/attorneys/,Alfred Boustany\n"
        "https://www.reyeslaw.com/attorneys/angel-l-reyes-iii/,Angel Reyes",
        language="csv",
    )

results_container = st.empty()
progress_container = st.empty()
log_container = st.expander("🪵 Logs (debug)")

df_in = None
if uploaded:
    try:
        df_in = pd.read_csv(uploaded)
        df_in = normalize_input(df_in)
        st.success(f"Loaded {len(df_in)} rows.")
    except Exception as e:
        st.error(f"CSV read/validation failed: {e}")

c1, c2 = st.columns(2)

def run(df: pd.DataFrame):
    rows = []
    prog = progress_container.progress(0, text="Starting...")
    total = len(df)
    for i, r in df.reset_index(drop=True).iterrows():
        url  = str(r["URL"]).strip()
        name = str(r["Target Name"]).strip()
        st.session_state["logs"].append(f"Scraping {name} from {url}")
        rows.append(scrape_one(url, name, timeout=timeout))
        prog.progress((i + 1) / total, text=f"Scraping {name} ({i+1}/{total})")
        time.sleep(0.05)
    prog.progress(1.0, text="Done ✅")
    return pd.DataFrame(rows)

if c1.button("▶️ Run Scrape", disabled=df_in is None, use_container_width=True):
    st.session_state["logs"].clear()
    res = run(df_in)
    results_container.dataframe(res, use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Download Results (CSV)",
        res.to_csv(index=False).encode("utf-8"),
        "attorney_bio_scrape_results.csv",
        "text/csv",
        use_container_width=True,
        key="dl",
    )

if c2.button("🧹 Clear Output", use_container_width=True):
    st.session_state["logs"].clear()
    results_container.empty()
    progress_container.empty()

with log_container:
    if st.session_state["logs"]:
        st.write("\n".join(st.session_state["logs"]))
    else:
        st.caption("Logs will appear here during the run.")
