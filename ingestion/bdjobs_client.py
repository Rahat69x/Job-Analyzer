import urllib.request
import urllib.parse
import json
import os
import time
from typing import List, Optional, Dict
from datetime import datetime, timezone
from core.models import NormalizedJob, CompanyInfo
from core.normalizer import parse_salary, parse_experience, parse_date, classify_company_tier, clean_html

API_ENDPOINT = "https://api.bdjobs.com/Jobs/api/JobSearch/GetJobSearch"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://bdjobs.com',
    'Referer': 'https://bdjobs.com/'
}

class BDJobsClient:
    def __init__(self, taxonomy_path: Optional[str] = None):
        if not taxonomy_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            taxonomy_path = os.path.join(base_dir, 'data', 'taxonomy.json')
            
        self.taxonomy = {}
        self.category_map: Dict[int, Dict] = {}
        if os.path.exists(taxonomy_path):
            with open(taxonomy_path, 'r', encoding='utf-8') as f:
                self.taxonomy = json.load(f)
                for cat in self.taxonomy.get('categories', []):
                    self.category_map[cat['id']] = cat

    def get_category_info(self, category_id: int) -> Dict:
        return self.category_map.get(category_id, {
            "name": f"Category {category_id}",
            "type": "Functional"
        })

    def fetch_jobs_by_category(self, category_id: int, page: int = 1, rpp: int = 50) -> List[NormalizedJob]:
        """Fetch live job postings from BDJobs production REST API for a given category."""
        params = {
            "Icat": "",
            "industry": "",
            "category": str(category_id),
            "org": "",
            "jobNature": "",
            "Fcat": "",
            "location": "",
            "Qot": "",
            "jobType": "",
            "jobLevel": "",
            "postedWithin": "",
            "deadline": "",
            "keyword": "",
            "pg": str(page),
            "qAge": "",
            "Salary": "",
            "experience": "",
            "gender": "",
            "MExp": "",
            "genderB": "",
            "MPostings": "",
            "MCat": "",
            "version": "",
            "rpp": str(rpp),
            "Newspaper": "",
            "armyp": "",
            "QDisablePerson": "",
            "pwd": "",
            "workplace": "",
            "facilitiesForPWD": "",
            "SaveFilterList": "",
            "UserFilterName": "",
            "HUserFilterName": "",
            "earlyJobAccess": "",
            "isPro": "0",
            "ToggleJobs": "true",
            "isFresher": "false"
        }
        
        url = f"{API_ENDPOINT}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=HEADERS)
        
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_jobs = data.get('data', [])
                cat_info = self.get_category_info(category_id)
                
                normalized_jobs = []
                for item in raw_jobs:
                    job_id = str(item.get('Jobid', ''))
                    title = item.get('jobTitle', '').strip()
                    company_name = item.get('companyName', '').strip()
                    
                    if not title or not company_name:
                        continue
                        
                    tier = classify_company_tier(company_name)
                    logo = item.get('logoUrl')
                    company = CompanyInfo(
                        name=company_name,
                        tier=tier,
                        verified=(item.get('standout', 0) == 1),
                        logo_url=logo if logo and "http" in logo else None
                    )
                    
                    raw_salary = item.get('Salary', '')
                    if raw_salary == "--":
                        raw_salary = "Negotiable"
                        
                    salary_info = parse_salary(raw_salary)
                    exp_info = parse_experience(item.get('experience'))
                    pub_date = parse_date(item.get('publishDate'))
                    dead_date = parse_date(item.get('deadlineDB') or item.get('deadline'))
                    
                    # Direct Apply link
                    apply_url = f"https://jobs.bdjobs.com/jobdetails.asp?id={job_id}"
                    
                    normalized_jobs.append(NormalizedJob(
                        id=f"bdjobs-{job_id}",
                        source="BDJobs",
                        title=title,
                        company=company,
                        category_id=category_id,
                        category_name=cat_info['name'],
                        category_type=cat_info['type'],
                        location=item.get('location', 'Bangladesh'),
                        publish_date=pub_date,
                        deadline=dead_date,
                        experience=exp_info,
                        salary=salary_info,
                        job_type=item.get('JobType', 'FullTime'),
                        vacancies=int(item.get('Vacancies') or 1),
                        job_context=clean_html(item.get('jobContext', '')),
                        apply_url=apply_url
                    ))
                    
                return normalized_jobs
        except Exception as e:
            print(f"[BDJobsClient] Error fetching category {category_id}: {e}")
            return []
