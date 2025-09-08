# --- TSEG Branded Attorney Bio Scraper (Streamlit) ---
import time, re, concurrent.futures, urllib.parse
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# -----------------------------
# Branding / Theme
# -----------------------------
TSEG_LOGO = "https://www.tseg.com/wp-content/uploads/2023/02/tseg-social-thumbnail.png"
ACCENT = "#9ccb3b"  # TSEG green

st.set_page_config(
    page_title="TSEG • Attorney Bio Scraper",
    page_icon=TSEG_LOGO,
    layout="wide",
)

# Custom CSS
st.markdown(
    f"""
    <style>
      .tseg-header {{
        text-align:center;
        padding:18px;
        border-radius:16px;
        background: linear-gradient(135deg, {ACCENT}22, rgba(255,255,255,0.04));
        border: 1px solid {ACCENT}55;
        margin-bottom: 20px;
      }}
      .tseg-header h1 {{ font-weight: 800; font-size: 1.8rem; margin: 0; }}
      .tseg-sub {{ font-size: 0.95rem; color: rgba(255,255,255,0.75); margin-top: 6px; }}
      .tseg-logo {{ display:block; margin-left:auto; margin-right:auto; margin-bottom:14px; }}
      .stButton>button {{
        border-radius: 12px; border:1px solid {ACCENT}55; padding: 10px 14px; font-weight: 600;
        color: white; background-color: {ACCENT}33;
      }}
      .stButton>button:hover {{ border-color: {ACCENT}; background-color: {ACCENT}55; }}
      .stDataFrame div[data-testid="stDataFrame"] {{ border-radius: 12px; overflow:hidden; }}
      .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid {ACCENT}55; margin-right:6px; }}
      .ctx {{ color: rgba(255,255,255,0.8); font-size: 0.9rem; }}
      .ctx b {{ color: {ACCENT}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Header block
st.markdown(
    f"""
    <div class="tseg-header">
      <img src="{TSEG_LOGO}" width="110" class="tseg-logo"/>
      <h1>Attorney Bio Scraper — Conference Edition</h1>
      <div class="tseg-sub">
        Surface quick talking points from attorney biography pages (education, hobbies, pets, family, community).
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Scraper utilities
# -----------------------------
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/123.0 Safari/537.36")
}

HOBBY_WORDS = [
    "golf","skiing","hiking","reading","travel","cooking","fishing","boating",
    "tennis","running","cycling","yoga","camping","kayaking","photography",
    "music","piano","guitar","basketball","football","soccer","baseball"
]
PET_WORDS = ["dog","dogs","cat","cats","puppy","kitten","golden retriever","pets","animal lover"]
FAMILY_WORDS = ["husband","wife","spouse","partner","children","kids","daughter","son","mother","father","family","married"]
COMMUNITY_WORDS = ["volunteer","board member","foundation","nonprofit","mentor","coach","community","pro bono"]
LANG_WORDS = ["spanish","french","german","italian","mandarin","cantonese","portuguese","arabic","hebrew","hindi","korean","japanese","russian","vietnamese"]
AWARD_WORDS = ["super lawyers","best lawyers","rising star","top 40 under 40","av preeminent","lawdragon"]
BAR_WORDS = ["state bar","bar admission","admitted to practice","supreme court","federal court","fifth circuit","ninth circuit"]

ALL_THEMES = [
    ("Hobbies", HOBBY_WORDS),
    ("Pets", PET_WORDS),
    ("Family", FAMILY_WORDS),
    ("Community", COMMUNITY_WORDS),
    ("Languages", LANG_WORDS),
    ("Awards", AWARD_WORDS),
    ("Bar / Courts", BAR_WORDS),
]

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

def extract_keywords(text: str, vocab: list[str]) -> list[str]:
    found = []
    for word in vocab:
        if re.search(rf"\b{re.escape(word)}\b", text, flags=re.IGNORECASE):
            found.append(word)
    return sorted(set(found))

def extract_schools(text: str) -> tuple[str, str]:
    law = re.findall(r"([A-Z][A-Za-z&.\-,'\s]+(?:School of Law| Law)(?:,?\s*[A-Z][A-Za-z&.\-,'\s]+)*)", text)
    ug  = re.findall(r"([A-Z][A-Za-z&.\-,'\s]+(?:University|College)(?: of [A-Z][A-Za-z&.\-,'\s]+)*)", text)
    law_school = ", ".join(sorted(set([s.strip() for s in law if len(s) < 120])))
    undergrad  = ", ".join(sorted(set([s.strip() for s in ug  if len(s) < 120])))
    return law_school, undergrad

def split_sentences(text: str) -> list[str]:
    # light sentence splitter
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if len(p.strip()) > 0 and len(p) < 300]

def context_snippets(text: str, keywords: list[str], max_per_theme: int = 2) -> list[str]:
    sents = split_sentences(text)
    found = []
    for kw in keywords:
        patt = re.compile(rf"(.{{0,80}}\b{re.escape(kw)}\b.{{0,80}})", re.IGNORECASE)
        for s in sents:
            m = patt.search(s)
            if m:
                # bold the keyword in context
                snippet = re.sub(rf"(\b{re.escape(kw)}\b)", r"<b>\\1</b>", m.group(0), flags=re.IGNORECASE)
                found.append(snippet)
                break  # one sentence per keyword
        if len(found) >= max_per_theme:
            break
    return found

def absolutize(base_url: str, src: str) -> str:
    try:
        return urllib.parse.urljoin(base_url, src)
    except:
        return src

def find_links_and_headshot(block: BeautifulSoup, base_url: str) -> tuple[list[tuple[str,str]], str | None]:
    links = []
    headshot = None

    # social/email links
    for a in block.find_all("a", href=True):
        href = a["href"].strip()
        lhref = href.lower()
        label = None
        if "linkedin.com" in lhref: label = "LinkedIn"
        elif "twitter.com" in lhref or "x.com" in lhref: label = "X (Twitter)"
        elif "facebook.com" in lhref: label = "Facebook"
        elif href.startswith("mailto:"): label = "Email"
        if label:
            links.append((label, absolutize(base_url, href)))

    # nearest image as headshot
    img = block.find("img")
    if img and img.get("src"):
        headshot = absolutize(base_url, img["src"])
    return links, headshot

def scrape_one(url: str, target_name: str, timeout: int = 25) -> dict:
    html = fetch_html(url, timeout=timeout)
    if not html:
        return {"Name": target_name, "URL": url, "Law School": "", "Undergrad": "",
                "Hobbies": "", "Pets": "", "Family": "", "Community": "",
                "Languages": "", "Awards": "", "Bar / Courts": "",
                "Context": "", "Links": "", "Headshot": ""}

    soup = BeautifulSoup(html, "lxml")
    block = nearest_block_with_name(soup, target_name)
    text  = (block.get_text(" ", strip=True) if block else soup.get_text(" ", strip=True))

    law_school, undergrad = extract_schools(text)

    # keywords + contexts
    theme_hits = {}
    theme_ctx = {}
    for name, vocab in ALL_THEMES:
        hits = extract_keywords(text, vocab)
        theme_hits[name] = ", ".join(hits)
        theme_ctx[name] = context_snippets(text, hits[:3]) if hits else []

    # links & headshot
    links, headshot = (find_links_and_headshot(block, url) if block else ([], None))
    links_str = "; ".join([f"{label}: {href}" for (label, href) in links])

    # pack short context (merge across themes)
    ctx_lines = []
    for name, _ in ALL_THEMES:
        for c in theme_ctx.get(name, [])[:1]:
            ctx_lines.append(f"<span class='pill'>{name}</span> <span class='ctx'>{c}</span>")
    ctx_html = "<br/>".join(ctx_lines[:6])

    return {
        "Name": target_name,
        "URL": url,
        "Law School": law_school,
        "Undergrad": undergrad,
        "Hobbies": theme_hits["Hobbies"],
        "Pets": theme_hits["Pets"],
        "Family": theme_hits["Family"],
        "Community": theme_hits["Community"],
        "Languages": theme_hits["Languages"],
        "Awards": theme_hits["Awards"],
        "Bar / Courts": theme_hits["Bar / Courts"],
        "Context": ctx_html,          # HTML snippets
        "Links": links_str,           # human-readable; also shown as buttons in UI
        "Headshot": headshot or "",
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
    max_workers = st.slider("Parallel requests", 1, 8, 4)
    st.caption("If sites are slow or blocky, lower parallelism and increase timeout.")

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

results_placeholder = st.empty()
progress_placeholder = st.empty()
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

def run_parallel(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(df)
    prog = progress_placeholder.progress(0, text="Starting...")
    def task(i_row):
        i, r = i_row
        url  = str(r["URL"]).strip()
        name = str(r["Target Name"]).strip()
        st.session_state["logs"].append(f"Scraping {name} from {url}")
        out = scrape_one(url, name, timeout=timeout)
        return i, out

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for idx, out in ex.map(task, df.reset_index(drop=True).iterrows()):
            rows.append(out)
            prog.progress(min((idx+1)/total, 1.0), text=f"Scraped {idx+1}/{total}")
            time.sleep(0.02)
    prog.progress(1.0, text="Done ✅")
    return pd.DataFrame(rows)

if c1.button("▶️ Run Scrape", disabled=df_in is None, use_container_width=True):
    st.session_state["logs"].clear()
    res = run_parallel(df_in)

    # Pretty results table with action buttons
    st.markdown("### 2) Results")
    for _, row in res.iterrows():
        with st.container(border=True):
            top = st.columns([1, 5, 2])
            with top[0]:
                if row["Headshot"]:
                    st.image(row["Headshot"], width=90)
            with top[1]:
                st.markdown(f"**{row['Name']}**  \n"
                            f"{row['Law School'] or ''}  \n"
                            f"{row['Undergrad'] or ''}")
                # context lines
                if row["Context"]:
                    st.markdown(row["Context"], unsafe_allow_html=True)
            with top[2]:
                st.link_button("Open Bio", row["URL"], use_container_width=True)
                # links
                if row["Links"]:
                    # turn into individual buttons
                    for part in row["Links"].split("; "):
                        if ": " in part:
                            label, href = part.split(": ", 1)
                            st.link_button(label.strip(), href.strip(), use_container_width=True)

    # Download
    st.download_button(
        "⬇️ Download Results (CSV)",
        res.drop(columns=["Context"]).to_csv(index=False).encode("utf-8"),
        "attorney_bio_scrape_results.csv",
        "text/csv",
        use_container_width=True,
        key="dl",
    )

if c2.button("🧹 Clear Output", use_container_width=True):
    st.session_state["logs"].clear()
    results_placeholder.empty()
    progress_placeholder.empty()

with log_container:
    if st.session_state["logs"]:
        st.write("\n".join(st.session_state["logs"]))
    else:
        st.caption("Logs will appear here during the run.")
