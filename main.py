import asyncio
import aiohttp
import tls_client
from datetime import datetime
from bs4 import BeautifulSoup
from config import Config
from utils import save_to_json
from typing import Generator, Dict, Any, Optional, List

class JobScraper:
    def __init__(self):
        self.logger = Config.LOGGER
        self.headers = Config.HEADERS
        self.job_freshness = Config.JOB_FRESHNESS
        self.unavaliable_messages = Config.UNAVALIABLE_MESSAGES
        self.base_url = 'https://www.foundit.in'
        self.session = tls_client.Session(
            client_identifier="chrome_108"
        )
        self.logger.info("JobScraper initialized")

    async def fetch(self, query: str, start: int = 0):
        self.logger.info(f"Fetching jobs for query: {query}, start: {start}")
        params = {
            'start': str(start),
            'sort': '1',
            'limit': '100',
            'query': query,
            'queryDerived': 'true',
            'jobFreshness' : self.job_freshness
        }

        try:
            response = self.session.get(
                f'{self.base_url}/middleware/jobsearch',
                headers=self.headers,
                params=params
            )
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch jobs: status code {response.status_code}")
                return None
            data = response.json()
            jobs = data.get("jobSearchResponse", {}).get("data", [])
            self.logger.info(f"Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            self.logger.error(f"Failed to fetch jobs: {str(e)}")
            return None

    async def get_details(self, job_id: int):
        url = f"{self.base_url}/middleware/jobdetail/{job_id}"
        self.logger.info(f"Getting details for job ID: {job_id}")
        try:
            response = self.session.get(url, headers=self.headers)
            if response.status_code != 200:
                self.logger.error(f"Failed to get job details: status code {response.status_code}")
                return None
            data = response.json()
            return data.get("jobDetailResponse", {})
        except Exception as e:
            self.logger.error(f"Failed to get job details for job ID {job_id}: {str(e)}")
            return None
    
    async def get_description(self, description: str, job_id: int) -> str:
        self.logger.info(f"Getting description for jobid: {job_id}")
        soup = BeautifulSoup(description, 'lxml')
        return soup.get_text()

    async def _parse_location(self, locations: str) -> tuple:
        self.logger.debug(f"Parsing location: {locations}")
        if not locations:
            return "", "", ""
        
        for location in locations:
            city = location.get("city", "")
            state = location.get("state", "")
            country = location.get("country", "")
            if any([city, state, country]):
                return city, state, country
        
        return "", "", ""
    
    async def parse_created_at(self, created_at: int) -> str:
        if created_at:
            created_at = datetime.fromtimestamp(created_at / 1000)
            created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        return created_at
    
    async def _is_job_available(self, job_url: str) -> bool:
        if not job_url:
            return True
        
        try:
            response = self.session.get(job_url, allow_redirects=True)
            unavailability = any(message in response.text.lower() for message in self.unavaliable_messages)
            if response.status_code != 200 or unavailability:
                self.logger.warning(f"Job is unavailable: {job_url} , status code: {response.status_code}, unavailability: {unavailability}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error checking job availability: {str(e)}")
            return False
    
    async def _get_salary_info(self, job_details: Dict[str, Any]) -> Dict[str, float]:
        from_salary = job_details.get("minimumSalary", {}).get("absoluteValue", 0)
        to_salary = job_details.get("maximumSalary", {}).get("absoluteValue", 0)
        
        return {
            'from': from_salary,
            'to': to_salary
        }    
    
    async def parse_job_data(self, data):
        try:
            self.logger.debug(f"Parsing job data for job ID: {data.get('jobId', 'unknown')}")
            job_id = data.get("jobId", "")
            job_details = await self.get_details(job_id)
            
            if not job_details:
                self.logger.warning(f"Failed to fetch job details for job ID: {job_id}")
                return False
            
            city, state, country = await self._parse_location(job_details.get("locations", ""))
            posted_on = await self.parse_created_at(data.get("createdAt"))
            
            job_url = job_details.get("redirectUrl", "")
            is_available = await self._is_job_available(job_url)
            if not is_available:
                return False
            
            salary_info = await self._get_salary_info(job_details)
            description = await self.get_description(job_details.get("description", ""), job_id)
            
            job_data = {
                'Domain': self.base_url,
                'PostUrl': job_details.get("applyUrl") or data.get("redirectUrl", ""),
                'JobID': job_id,
                'Title': data.get("title", ""),
                'City': city,
                'State': state,
                'Speciality': '',
                'JobType': ", ".join(data.get("employmentTypes", [])),
                'JobDetails': description,
                'Industry': '',
                'Company': job_details.get("company", {}).get("name", ""),
                'PostedOn': posted_on,
                'SalaryFrom': salary_info['from'],
                'SalaryUpto': salary_info['to'],
                'PayoutTerm': "yearly",
                'IsEstimatedSalary': data.get("isEstimatedSalary", ""),
                'ScrapedOn': datetime.now().isoformat(),
                'Experience': job_details.get("minimumExperience", {}).get("years", ""),
            }
            
            save_to_json(self, job_data)
            return True
        except Exception as e:
            self.logger.error(f"Error parsing job data: {str(e)}")
            return False

    async def process_jobs_batch(self, jobs):
        tasks = []
        for job in jobs:
            task = asyncio.create_task(self.parse_job_data(job))
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    self.logger.error(f"Error processing job: {str(result)}")
        return tasks

    async def fetch_and_process_jobs(self, query, start):
        jobs = await self.fetch(query, start)
        if not jobs:
            return None
        return await self.process_jobs_batch(jobs)

    async def run(self, queries: list):
        for query in queries:
            self.logger.info(f"Starting the scraper for query: {query}")
            start = 0
            self.query = query
            batch_size = 50
            active_tasks = []

            try:
                while True:
                    batch_tasks = await self.fetch_and_process_jobs(query, start)
                    if not batch_tasks:
                        break

                    active_tasks.extend(batch_tasks)
                    
                    if len(active_tasks) >= batch_size:
                        await asyncio.gather(*active_tasks, return_exceptions=True)
                        active_tasks = []

                    start += 100

                if active_tasks:
                    await asyncio.gather(*active_tasks, return_exceptions=True)

            except Exception as e:
                self.logger.error(f"Error occurred during scraping: {str(e)}")


async def main():
    scraper = JobScraper()
    await scraper.run(Config.QUERIES)

if __name__ == "__main__":
    main()
