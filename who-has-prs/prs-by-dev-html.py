import requests
import json
import time
import os
import yaml
import logging
from typing import List, Dict, Any

GITHUB_API_URL = "https://api.github.com"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GitHubPRFetcher:
    def __init__(self, token: str, developers: List[str]):
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.developers = developers  # Explicit list of developers

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

    def extract_reviewers(self, prs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Extracts PRs for each developer who is explicitly listed in config."""
        reviewers_data = {dev: [] for dev in self.developers}

        for pr in prs:
            pr_info = {
                "repo": pr['base']['repo']['full_name'],
                "pr_number": pr['number'],
                "title": pr['title'],
                "author": pr['user']['login'],
                "url": pr['html_url']
            }
            for reviewer in pr.get("requested_reviewers", []):
                reviewer_name = reviewer["login"]
                if reviewer_name in self.developers:
                    reviewers_data[reviewer_name].append(pr_info)

        # Remove empty reviewer entries
        return {dev: prs for dev, prs in reviewers_data.items() if prs}

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

    def generate_html_report(self, reviewers_data: Dict[str, List[Dict[str, Any]]]):
        """Generates an HTML file displaying each developer's PRs with a sleek modern theme."""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>GitHub PR Reviewers Report</title>
            <style>
                body {
                    font-family: 'Arial', sans-serif;
                    background-color: #f4f4f4;
                    margin: 20px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                h1 {
                    text-align: center;
                    color: #333;
                    font-size: 28px;
                }
                .developer-card {
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                    margin: 10px;
                    width: 60%;
                    max-width: 600px;
                    transition: transform 0.2s ease-in-out;
                }
                .developer-card:hover {
                    transform: scale(1.02);
                }
                h2 {
                    color: #0366d6;
                    font-size: 20px;
                    margin-bottom: 10px;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                }
                li {
                    margin: 8px 0;
                    padding: 8px;
                    border-radius: 6px;
                    background: #f9f9f9;
                    transition: background 0.3s ease;
                }
                li:hover {
                    background: #eaeaea;
                }
                a {
                    text-decoration: none;
                    color: #0366d6;
                    font-weight: bold;
                }
                a:hover {
                    text-decoration: underline;
                }
            </style>
        </head>
        <body>
            <h1>GitHub PR Reviewers Report</h1>
        """

        for dev, prs in reviewers_data.items():
            html_content += f'<div class="developer-card"><h2>{dev}</h2><ul>'
            for pr in prs:
                html_content += f'<li><a href="{pr["url"]}" target="_blank">{pr["title"]}</a></li>'
            html_content += '</ul></div>'

        html_content += """
        </body>
        </html>
        """

        with open("reviewers_prs.html", "w") as f:
            f.write(html_content)
        logging.info("PR review data saved to reviewers_prs.html")

def load_config(filename: str) -> Dict[str, Any]:
    """Loads repositories and developers list from a YAML file."""
    try:
        with open(filename, "r") as file:
            config = yaml.safe_load(file)
            repositories = config.get("repositories", [])
            developers = config.get("developers", [])
            if not repositories:
                logging.warning("No repositories found in config file.")
            if not developers:
                logging.warning("No developers found in config file.")
            return {"repositories": repositories, "developers": developers}
    except FileNotFoundError:
        logging.error(f"Configuration file {filename} not found.")
        return {"repositories": [], "developers": []}
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {filename}: {e}")
        return {"repositories": [], "developers": []}

if __name__ == "__main__":
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set.")
    
    config = load_config("config.yaml")
    repositories = config["repositories"]
    developers = config["developers"]

    if repositories and developers:
        fetcher = GitHubPRFetcher(GITHUB_TOKEN, developers)
        fetcher.fetch_and_display_prs(repositories, save_to_file=True, output_html=True)
    else:
        logging.error("No repositories or developers to process.")
