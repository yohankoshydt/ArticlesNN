import argparse
import time
from bs4 import BeautifulSoup
import pandas as pd
import random
import requests
import asyncio
import aiohttp
import socket
import re
import warnings
import os
from inf import encode_text
from mongo_upload import upload_to_mongo, search_mongo, vector_search
warnings.filterwarnings('ignore')

user_agents = [
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) Gecko/20100101 Firefox/55.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36"
]

def make_header():
    headers = {'User-Agent': random.choice(user_agents)}
    print(f"[DEBUG] Using header: {headers}")
    return headers

articles_data = []
urls = []
scraped_urls = []
semaphore = asyncio.BoundedSemaphore(100)
PMID_FILE = "scraped_pmids.csv"

def read_existing_pmids():
    if os.path.exists(PMID_FILE):
        df = pd.read_csv(PMID_FILE)
        return set(df['PMID'].astype(str))  # Convert to string for consistency
    return set()

def save_new_pmids(new_pmids):
    if os.path.exists(PMID_FILE):
        df_existing = pd.read_csv(PMID_FILE)
    else:
        df_existing = pd.DataFrame(columns=['PMID'])

    new_df = pd.DataFrame({'PMID': list(new_pmids)})
    updated_df = pd.concat([df_existing, new_df]).drop_duplicates()
    updated_df.to_csv(PMID_FILE, index=False)

# Get the existing PMIDs
existing_pmids = read_existing_pmids()
print(f"[DEBUG] Found {len(existing_pmids)} previously scraped PMIDs.")


async def extract_by_article(url):
    global articles_data
    headers = make_header()
    conn = aiohttp.TCPConnector(family=socket.AF_INET)
    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        async with semaphore, session.get(url, allow_redirects=True) as response:
            print(f"[DEBUG] Final URL: {response.url}")
            print(f"[DEBUG] Fetching article: {url}")
            data = await response.text()
            soup = BeautifulSoup(data, "lxml")
            try:
                title = soup.find('meta', {'name': 'citation_title'})['content'].strip('[]')
            except:
                try:
                   title = soup.find('h1', class_='heading-title').get_text(strip=True)
                except:
                    title = 'NO_TITLE'

            try:
                abstract_raw = soup.find('div', {'class': 'abstract-content selected'}).find_all('p')
                abstract = ' '.join([paragraph.text.strip() for paragraph in abstract_raw])
            except:
                abstract = 'NO_ABSTRACT'
            
            try:
                #Find the DOI link
                doi_tag = soup.find("span", class_="identifier doi")
                doi = doi_tag.find("a").text.strip()  # Extract DOI text
                  
            except:
                doi = "NO_DOI_FOUND"

            
            try:
                button = soup.find("button", {"id": "full-view-journal-trigger"})
                journal = button.get("title")
            except:
                journal = "NO_Journal"

            try:
                authors = [a.text.strip() for a in soup.find_all("a", class_="full-name")]
                authors = ','.join(authors)
            except:
                authors = 'NO_Authors'

            try:
                citation_text = soup.find("span", class_="cit").text
                pattern = r"(\d{4}) (\w+);(\d+)\((\d+)\):(\d+-\d+)\."
                match = re.search(pattern, citation_text)

                if match:
                    pub_year = match.group(1)      
                    pub_month = match.group(2)   
                    date = pub_month + ' ' + pub_year  
                    volume = match.group(3)        
                    issue = match.group(4)         
                    pages = match.group(5) 
                
                else:

                    pattern = r"(\d{4}) (\w+) (\d{1,2});(\d+)\((\d+)\):(\d+-\d+|\d+)\."
                    match = re.search(pattern, citation_text)

                    if match:
                        pub_year = match.group(1)      # '2024'
                        pub_month = match.group(2)     # 'Jan'
                        pub_day = match.group(3)       # '26'
                        date = f"{pub_month} {pub_day}, {pub_year}"  # 'Jan 26, 2024'
                        volume = match.group(4)        # '25'
                        issue = match.group(5)         # '3'
                        pages = match.group(6)  

                    else:
                        date = 'NO_DATE'
                        volume = 'NO_VOL'
                        issue = 'NO_ISSUE'
                        pages = 'NO_pages'

            except:
                date = 'NO_DATE'
                volume = 'NO_VOL'
                issue = 'NO_ISSUE'
                pages = 'NO_pages'

            try:
                pubmed_id = soup.find("strong", {"title": "PubMed ID"}).text.strip()

            except:
                pubmed_id = 'NO_PMID'

            try:
                # print('trying to feth keywords..')
                keywords_strong = soup.find(lambda tag: tag.name == "strong" and tag.text.strip() == "Keywords:")
                parent_p = keywords_strong.find_parent("p")
                keywords_text = parent_p.get_text(strip=True).replace("Keywords:", "").strip()
                keywords = [kw.strip() for kw in keywords_text.split(';') if kw.strip()]

                

                
            except Exception as e:
                print(e)
                keywords = 'NO_KEYWORDS'

            try:
                publication_type = soup.find('span', {'class': 'publication-types'}).text.strip()
            except:
                publication_type = 'NO_PUB_TYPE'


            try:
                response = requests.get('https://doi.org/'+ doi, allow_redirects=True)
                full_text_link = response.url
            except:
                full_text_link = 'NO_LINK'



            article_data = {
                'therapy': therapy,
                'molecule': molecule,
                'url': url,
                'title': title,
                'authors': authors,
                'journal name': journal,
                'Volume': volume,
                'Issue': issue,
                'Pages': pages,
                'Publication Date': date,
                'doi':doi,
                'pubmed ID': pubmed_id,
                'Full-Text Article Link': full_text_link,
                'abstract': abstract,
                'keywords': keywords,
                'Category' : publication_type,
                'article encoding' : encode_text(f'{abstract or ''}', 'article')
                
            }
            articles_data.append(article_data)
            #print(f"[DEBUG] Extracted article data: {article_data}")

            save_new_pmids({pubmed_id})


#asyncio.run(extract_by_article(r'https://pubmed.ncbi.nlm.nih.gov/38338796/'))

async def get_pmids(page, keyword):
    page_url = f'{pubmed_url}+{keyword}+&page={page}'
    headers = make_header()
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(page_url) as response:
            print(f"[DEBUG] Fetching PMIDs from: {page_url}")
            data = await response.text()
            soup = BeautifulSoup(data, "lxml")
            pmids = soup.find('meta', {'name': 'log_displayeduids'})['content']
            for pmid in pmids.split(','):
                url = root_pubmed_url + '/' + pmid
                urls.append(url)
                print(f"[DEBUG] Found article URL: {url}")

def get_num_pages(keyword):
    headers = make_header()
    search_url = f'{pubmed_url}+{keyword}'
    with requests.get(search_url, headers=headers) as response:
        data = response.text
        soup = BeautifulSoup(data, "lxml")
        num_pages = int(soup.find('span', {'class': 'total-pages'}).get_text().replace(',', ''))
        print(f"[DEBUG] Total pages for keyword '{keyword}': {num_pages}")
        return num_pages

async def build_article_urls(keywords):
    tasks = []
    for keyword in keywords:
        num_pages = get_num_pages(keyword)
        for page in range(1, num_pages + 1):
            task = asyncio.create_task(get_pmids(page, keyword))
            tasks.append(task)
    await asyncio.gather(*tasks)



pubmed_url = 'https://pubmed.ncbi.nlm.nih.gov/?term='
root_pubmed_url = 'https://pubmed.ncbi.nlm.nih.gov'
molecule = 'Cagrilintide'
therapy = 'diabetes'
search_keywords = [f'(Novo Nordisk[Affiliation]) AND ({therapy}[MeSH Major Topic])) AND ({molecule}[Text Word])']

print(f"[DEBUG] Keywords to search: {search_keywords}")

Article = None
articles_data = []
urls = []
scraped_urls = []
semaphore = asyncio.BoundedSemaphore(100)

loop = asyncio.get_event_loop()
loop.run_until_complete(build_article_urls(search_keywords))
print(f"[DEBUG] Total article URLs found: {len(urls)}")
#print(urls)




i = 0

for url in urls:
    

    if i >= 20 :
        break

    

    asyncio.run(extract_by_article(rf'{url}'))
    upload_to_mongo(articles_data.pop())
    time.sleep(1.5)
    i+=1
  

articles_df = pd.DataFrame(articles_data)
articles_df.to_csv('articles.csv', index=False)

# query = 'Glucose regulation'
# query_vector = encode_text(query, 'query')

# search_results = vector_search(query_vector)

#     # Print results
# for doc in search_results:
#     print(doc)


# loop.run_until_complete(get_article_data(urls))

# articles_df = pd.DataFrame(articles_data)
# print("[DEBUG] Saving articles to CSV")
# articles_df.to_csv(args.output, index=False)