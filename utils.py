from datetime import datetime
from pathlib import Path
import json
from typing import Dict, Any



def save_to_json(self, data: Dict[str, Any]) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    filename = Path(f"monster_jobs_{today}.json")
    
    if not filename.exists():
        with open(filename, 'w') as file:
            json.dump([], file)
    
    with open(filename, 'r') as file:
        jobs = json.load(file)
        
    jobs.append(data)
    
    with open(filename, 'w') as file:
        json.dump(jobs, file, indent=4)
        self.logger.info(f"Saved {len(jobs)} jobs to {filename}")
