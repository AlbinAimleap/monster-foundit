import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

class Config:
    LOGGER = logging.getLogger("MonsterScraper")
    JOB_FRESHNESS = 1
    QUERIES = ["aws", "python", "java", "devops", "data science", "machine learning"]
    UNAVALIABLE_MESSAGES = [
        
    ]
    HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'priority': 'u=1, i',
    'referer': 'https://www.foundit.in/srp/results?query=python&locations=&searchId=c6334916-695e-482d-a102-15d11b3c57f7',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'x-language-code': 'EN',
    'x-source-country': 'IN',
    'x-source-freshpaint-id': 'null',
    'x-source-site-context': 'rexmonster',
}