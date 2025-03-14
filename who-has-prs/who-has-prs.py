import requests
import json
import time
import os
import yaml
from typing import List, Dict, Any

GITHUB_API_URL = "https://api.github.com"

class GitHubPRFetcher:
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def fetch_open_prs(self, repo: str) -> List[Dict[str, Any]]:
        """Fetches open pull requests for a given repository."""
        url = f"{GITHUB_API_URL}/repos/{repo}/pulls?state=open"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                reset_time = int(response.headers['X-RateLimit-Reset'])
                wait_time = reset_time - int(time.time()) + 1
                print(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                return self.fetch_open_prs(repo)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PRs for {repo}: {e}")
            return []

    def extract_usernames(self, prs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extracts assignees and requested reviewers from PR data."""
        extracted_data = []
        for pr in prs:
            pr_data = {
                "repo": pr['base']['repo']['full_name'],
                "pr_number": pr['number'],
                "title": pr['title'],
                "assignees": [user['login'] for user in pr.get('assignees', [])],
                "reviewers": [user['login'] for user in pr.get('requested_reviewers', [])],
                "author": pr['user']['login'],
                "url": pr['html_url']
            }
            extracted_data.append(pr_data)
        return extracted_data

    def fetch_and_display_prs(self, repos: List[str]):
        """Fetches and displays PR data for multiple repositories."""
        all_pr_data = []
        for repo in repos:
            prs = self.fetch_open_prs(repo)
            if prs:
                all_pr_data.extend(self.extract_usernames(prs))
        
        # Print results in a structured JSON format
        print(json.dumps(all_pr_data, indent=4))
        return all_pr_data

if __name__ == "__main__":
    # Read GitHub token from environment variable
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set.")
    
    # Read repository list from YAML file
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
        repositories = config.get("repositories", [])
    
    fetcher = GitHubPRFetcher(GITHUB_TOKEN)
    fetcher.fetch_and_display_prs(repositories)