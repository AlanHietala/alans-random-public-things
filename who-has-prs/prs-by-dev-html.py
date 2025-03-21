import requests
import json
import time
import os
import yaml
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
from collections import defaultdict




GITHUB_API_URL = "https://api.github.com"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GitHubPRFetcher:
    def __init__(self, token: str, developers: List[str], days_stale: int = 7):
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.developers = developers
        self.days_stale = days_stale
    
    def fetch_open_prs(self, repo: str) -> List[Dict[str, Any]]:
        """Fetches open PRs for a given repository, handling pagination."""
        all_prs = []
        page = 1
        while True:
            url = f"{GITHUB_API_URL}/repos/{repo}/pulls?state=open&per_page=100&page={page}"
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers:
                    reset_time = int(response.headers['X-RateLimit-Reset'])
                    wait_time = reset_time - int(time.time()) + 1
                    logging.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    return self.fetch_open_prs(repo)

                response.raise_for_status()
                prs = response.json()
                
                if not prs:
                    break

                all_prs.extend(prs)
                page += 1

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching PRs for {repo}: {e}")
                break

        return all_prs

    def has_reviewer_feedback(self, repo: str, pr_number: int, reviewer: str) -> bool:
        """Checks if the reviewer has left comments or a review on the PR."""
        comments_url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments"
        reviews_url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}/reviews"

        try:
            # Fetch PR comments
            comments_response = requests.get(comments_url, headers=self.headers)
            reviews_response = requests.get(reviews_url, headers=self.headers)

            if comments_response.status_code == 200 and reviews_response.status_code == 200:
                comments = comments_response.json()
                reviews = reviews_response.json()

                # Check if the reviewer has commented
                for comment in comments:
                    if comment["user"]["login"] == reviewer:
                        return True

                # Check if the reviewer has left a review
                for review in reviews:
                    if review["user"]["login"] == reviewer and review["state"] in ["COMMENTED", "APPROVED", "CHANGES_REQUESTED"]:
                        return True

            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching review feedback for PR #{pr_number} in {repo}: {e}")
            return False

    def extract_reviewers(self, prs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extracts PRs for each developer with `inProgress` flag if they provided feedback."""
        reviewers_data = {dev: [] for dev in self.developers}

        for pr in prs:
            repo_name = pr['base']['repo']['full_name']
            pr_number = pr['number']

            for reviewer in pr.get("requested_reviewers", []):
                reviewer_name = reviewer["login"]

                if reviewer_name in self.developers:
                    in_progress = self.has_reviewer_feedback(repo_name, pr_number, reviewer_name)
                    last_updated = datetime.strptime(pr['updated_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    is_stale = (datetime.now(timezone.utc) - last_updated) > timedelta(days=self.days_stale)

                    reviewers_data[reviewer_name].append({
                        "repo": repo_name,
                        "pr_number": pr_number,
                        "title": pr['title'],
                        "author": pr['user']['login'],
                        "url": pr['html_url'],
                        "inProgress": in_progress,
                        "isStale": is_stale
                    })
                

        # Remove empty reviewer entries
        return {dev: prs for dev, prs in reviewers_data.items() if prs}

    def generate_html_report(self, reviewers_data: Dict[str, List[Dict[str, Any]]]):
        """Generates an HTML file displaying each developer's PRs, grouped by repo."""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>GitHub PR Reviewers Report</title>
            <style>
                body { font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; text-align: center; }
                .developer-card {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                    margin: 10px auto;
                    width: 60%;
                    max-width: 600px;
                    text-align: left;
                }
                h1 { color: #333; }
                h2 { color: #0366d6; }
                h3 { color: #555; margin-top: 16px; }
                ul { list-style-type: none; padding: 0; }
                li { margin: 8px 0; padding: 8px; border-radius: 6px; background: #f9f9f9; }
                a { text-decoration: none; color: #0366d6; font-weight: bold; }
                .status { font-size: 14px; padding: 4px 6px; border-radius: 4px; margin-left: 10px; }
                .in-progress { background: #ffcc00; color: #333; }
                .not-started { background: #ccc; color: #333; }
                .stale { background: #ff4d4f; color: white; margin-left: 8px; }
            </style>
        </head>
        <body>
            <h1>GitHub PR Reviewers Report</h1>
        """

        for dev, prs in reviewers_data.items():
            html_content += f'<div class="developer-card"><h2>{dev}</h2>'

            # Group PRs by repo
            prs_by_repo = defaultdict(list)
            for pr in prs:
                prs_by_repo[pr["repo"]].append(pr)

            for repo, repo_prs in prs_by_repo.items():
                html_content += f'<h3>{repo}</h3><ul>'
                for pr in repo_prs:
                    status_class = "in-progress" if pr["inProgress"] else "not-started"
                    status_text = "In Progress" if pr["inProgress"] else "Not Started"
                    stale_tag = '<span class="status stale">Stale</span>' if pr.get("isStale") else ""

                    html_content += (
                        f'<li><a href="{pr["url"]}" target="_blank">{pr["title"]}</a> '
                        f'<span class="status {status_class}">{status_text}</span> {stale_tag}</li>'
                    )
                html_content += '</ul>'

            html_content += '</div>'

        html_content += """
        </body>
        </html>
        """

        with open("reviewers_prs.html", "w") as f:
            f.write(html_content)
        logging.info("PR review data saved to reviewers_prs.html")
            #######
    

    def fetch_and_display_prs(self, repos: List[str], save_to_file: bool = False, output_html: bool = False):
        """Fetches PR data and structures it by reviewer."""
        all_reviewers_data = {}

        for repo in repos:
            prs = self.fetch_open_prs(repo)
            if prs:
                extracted_reviewers = self.extract_reviewers(prs)
                for reviewer, pr_list in extracted_reviewers.items():
                    if reviewer not in all_reviewers_data:
                        all_reviewers_data[reviewer] = []
                    all_reviewers_data[reviewer].extend(pr_list)

        # Convert to JSON format
        output_json = json.dumps(
            [{"developer": dev, "reviewing_prs": prs} for dev, prs in all_reviewers_data.items()],
            indent=4
        )

        print(output_json)

        if save_to_file:
            with open("reviewers_prs.json", "w") as f:
                f.write(output_json)
            logging.info("PR review data saved to reviewers_prs.json")

        if output_html:
            self.generate_html_report(all_reviewers_data)

        return all_reviewers_data

def load_config(filename: str) -> Dict[str, Any]:
    """Loads repositories, developers, and stale threshold from a YAML file."""
    try:
        with open(filename, "r") as file:
            config = yaml.safe_load(file)
            repositories = config.get("repositories", [])
            developers = config.get("developers", [])
            days_stale = config.get("days_stale", 7)
            if not repositories:
                logging.warning("No repositories found in config file.")
            if not developers:
                logging.warning("No developers found in config file.")
            return {
                "repositories": repositories,
                "developers": developers,
                "days_stale": days_stale
            }
    except FileNotFoundError:
        logging.error(f"Configuration file {filename} not found.")
        return {"repositories": [], "developers": [], "days_stale": 7}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {filename}: {e}")
        return {"repositories": [], "developers": [], "days_stale": 7}

if __name__ == "__main__":
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set.")

    config = load_config("config.yaml")
    repositories = config["repositories"]
    developers = config["developers"]
    days_stale = config["days_stale"]

    if repositories and developers:
        fetcher = GitHubPRFetcher(GITHUB_TOKEN, developers, days_stale)
        fetcher.fetch_and_display_prs(repositories, save_to_file=True, output_html=True)
    else:
        logging.error("No repositories or developers to process.")
