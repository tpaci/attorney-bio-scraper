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
