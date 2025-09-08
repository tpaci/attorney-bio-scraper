import time, re, io
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

# ---- Heartbeat: render something immediately
st.set_page_config(page_title="Attorney Bio Scraper – Conference Edition", layout="wide")
st.write("✅ App loaded — initializing UI...")

# ===== Shared scraping utilities =====
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"}
HOBBY_WORDS = ["golf","skiing","hiking","reading","travel","cooking","fishing","boating","tennis","running","cycling","yoga","camping","kayaking","photography","music","piano","guitar","basketball","football","soccer","baseball"]
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
            if node is None: break
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

def extract_schools(text: str) -> tuple[str,str]:
    law = re.findall(r"([A-Z][A-Za-z&.\-,'\s]+(?:School of Law| Law)(?:,?\s*[A-Z][A-Za-z&.\-,'\s]+)*)", text)
    ug  = re.findall(r"([A-Z][A-Za-z&.\-,'\s]+(?:University|College)(?: of [A-Z][A-Za-z&.\-,'\s]+)*)", text)
    law_school = ", ".join(sorted(set([s.strip() for s in law if len(s) < 120])))
    undergrad  = ", ".join(sorted(set([s.strip() for s in ug  if len(s) < 120])))
    return law_school, undergrad

def scrape_one(url: str, target_name: str, timeout: int = 25) -> dict:
    html = fetch_html(url, timeout=timeout)
    if not html:
        return {"Name": target_name, "Law School": "", "Undergrad": "", "Hobbies": "", "Pets": "", "Family": "",
                "Community Involvement": "", "Bio Snippet": "Fetch error", "URL": url}
    soup = BeautifulSoup(html, "lxml")
    block = nearest_block_with_name(soup, target_name)
    text = (block.get_text(" ", strip=True) if block else soup.get_text(" ", strip=True))
    law_school, undergrad = extract_schools(text)
    hobbies   = extract_keywords(text, HOBBY_WORDS)
    pets      = extract_keywords(text, PET_WORDS)
    family    = extract_keywords(text, FAMILY_WORDS)
    community = extract_keywords(text, COMMUNITY_WORDS)
    snippet = text[:300] + "..." if len(text) > 300 else text
    return {"Name": target_name, "Law School": law_school, "Undergrad": undergrad, "Hobbies": hobbies, "Pets": pets,
            "Family": family, "Community Involvement": community, "Bio Snippet": snippet, "URL": url}

def normalize_input(df: pd.DataFrame) -> pd.DataFrame:
    cols = {c.lower().strip(): c for c in df.columns}
    url_col  = cols.get("url")
    name_col = cols.get("target name") or cols.get("name")
    if not url_col or not name_col:
        raise ValueError("CSV must contain columns: 'URL' and 'Target Name'")
    return df.rename(columns={url_col: "URL", name_col: "Target Name"})[["URL","Target Name"]]

# ===== UI (wrapped so any error is shown) =====
try:
    st.title("🧭 Attorney Bio Scraper – Conference Edition")
    if "logs" not in st.session_state: st.session_state["logs"] = []

    with st.sidebar:
        st.header("⚙️ Settings")
        timeout = st.slider("Request timeout (seconds)", 5, 60, 25)

    st.subheader("1) Upload URL list (CSV)")
    st.write("CSV must have columns: **URL** and **Target Name**.")
    uploaded = st.file_uploader("Upload bio_urls.csv", type=["csv"])

    exp = st.expander("See sample CSV")
    with exp:
        st.code("URL,Target Name\nhttps://friedmanlawfirm.com/about-our-law-firm/,Alda Gojcaj\nhttp://boustanylawfirm.com/attorneys/,Alfred Boustany\nhttps://www.reyeslaw.com/attorneys/angel-l-reyes-iii/,Angel Reyes", language="csv")

    results_container = st.empty()
    progress_container = st.empty()
    log_container = st.expander("🪵 Logs (debug)")

    df_in = None
    if uploaded:
        df_in = pd.read_csv(uploaded)
        df_in = normalize_input(df_in)
        st.success(f"Loaded {len(df_in)} rows.")

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
            prog.progress((i+1)/total, text=f"Scraping {name} ({i+1}/{total})")
            time.sleep(0.05)
        prog.progress(1.0, text="Done ✅")
        return pd.DataFrame(rows)

    if c1.button("▶️ Run Scrape", disabled=df_in is None, use_container_width=True):
        st.session_state["logs"].clear()
        res = run(df_in)
        results_container.dataframe(res, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download Results (CSV)", res.to_csv(index=False).encode("utf-8"),
                           "attorney_bio_scrape_results.csv", "text/csv", use_container_width=True)

    if c2.button("🧹 Clear", use_container_width=True):
        st.session_state["logs"].clear()
        results_container.empty()
        progress_container.empty()

    with log_container:
        if st.session_state["logs"]:
            st.write("\n".join(st.session_state["logs"]))
        else:
            st.caption("Logs will appear here during the run.")
except Exception as e:
    st.error("An error occurred while rendering the app.")
    st.exception(e)

import requests
import pandas as pd
from bs4 import BeautifulSoup
import re

def extract_bio_block(soup, target_name):
    text_blocks = soup.find_all(['p', 'div', 'section', 'article', 'li'])
    for block in text_blocks:
        if block.get_text(strip=True) and target_name.lower() in block.get_text(strip=True).lower():
            return block.get_text(separator=" ", strip=True)
    return None

def extract_keywords(text, category_keywords):
    found = []
    for keyword in category_keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
            found.append(keyword)
    return ", ".join(found) if found else ""

def extract_school_info(text):
    law_keywords = ['law school', 'jd', 'juris doctor', 'juris doctorate']
    undergrad_keywords = ['bachelor', 'undergraduate', 'BA', 'BS', 'B.A.', 'B.S.']
    
    law_match = re.findall(r'([A-Z][a-zA-Z\s,&]+(?:Law|School of Law)[a-zA-Z\s,&]*)', text)
    undergrad_match = re.findall(r'([A-Z][a-zA-Z\s,&]+University|College[a-zA-Z\s,&]*)', text)

    law_school = ", ".join(set(law_match))
    undergrad_school = ", ".join(set(undergrad_match))
    
    return law_school, undergrad_school

def scrape_attorney_bios(csv_path):
    df = pd.read_csv(csv_path)
    
    output = []

    for index, row in df.iterrows():
        url = row['URL']
        name = row['Target Name']
        print(f"Scraping {name} from {url}...")
        
        try:
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')

            # Extract section that includes the target name
            bio_text = extract_bio_block(soup, name)
            if not bio_text:
                bio_text = soup.get_text(separator=" ", strip=True)

            # Extract structured data
            law_school, undergrad_school = extract_school_info(bio_text)
            hobbies = extract_keywords(bio_text, ['golf', 'skiing', 'hiking', 'reading', 'travel', 'cooking', 'fishing', 'boating', 'tennis', 'running'])
            pets = extract_keywords(bio_text, ['dog', 'cat', 'puppy', 'golden retriever', 'pets', 'animal lover'])
            family = extract_keywords(bio_text, ['husband', 'wife', 'children', 'daughter', 'son', 'married', 'spouse', 'family', 'mother', 'father'])
            community = extract_keywords(bio_text, ['volunteer', 'board member', 'foundation', 'nonprofit', 'mentor', 'coach', 'community'])

            output.append({
                'Name': name,
                'Law School': law_school,
                'Undergrad': undergrad_school,
                'Hobbies': hobbies,
                'Pets': pets,
                'Family': family,
                'Community Involvement': community,
                'Bio Snippet': bio_text[:300] + "..." if len(bio_text) > 300 else bio_text,
                'URL': url
            })

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            output.append({
                'Name': name,
                'Law School': '',
                'Undergrad': '',
                'Hobbies': '',
                'Pets': '',
                'Family': '',
                'Community Involvement': '',
                'Bio Snippet': 'Error loading page',
                'URL': url
            })

    result_df = pd.DataFrame(output)
    result_df.to_csv("attorney_bio_scrape_results.csv", index=False)
    print("\n✅ Scrape complete! Saved to 'attorney_bio_scrape_results.csv'.")

# Run the function
if __name__ == "__main__":
    scrape_attorney_bios("bio_urls.csv")
