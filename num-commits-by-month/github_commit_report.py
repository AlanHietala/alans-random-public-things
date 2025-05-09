import os
import requests
import datetime
from dotenv import load_dotenv
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
import calendar
import yaml

# Load GitHub token
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise EnvironmentError("Missing GITHUB_TOKEN in .env file.")

HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
BASE_URL = "https://api.github.com"

# Load repos from repos.yml
def load_repos_from_yaml(path="repos.yml"):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config.get("repos", [])

REPOS = load_repos_from_yaml()

# Get last 3 full months
def get_last_3_months():
    today = datetime.date.today().replace(day=1)
    months = []
    for _ in range(3):
        last_day = today - datetime.timedelta(days=1)
        first_day = last_day.replace(day=1)
        label = first_day.strftime("%B %Y")
        months.insert(0, (first_day.isoformat(), last_day.isoformat(), label))
        today = first_day
    return months

# Fetch commit counts
def get_commit_count(repo, since, until):
    total_commits = 0
    page = 1
    while True:
        url = f"{BASE_URL}/repos/{repo}/commits"
        params = {
            "since": f"{since}T00:00:00Z",
            "until": f"{until}T23:59:59Z",
            "per_page": 100,
            "page": page
        }
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code != 200:
            print(f"Error fetching {repo} ({resp.status_code})")
            break
        commits = resp.json()
        total_commits += len(commits)
        if len(commits) < 100:
            break
        page += 1
    return total_commits

# Build report data
date_ranges = get_last_3_months()
report_data = defaultdict(list)

for repo in REPOS:
    for since, until, label in date_ranges:
        count = get_commit_count(repo, since, until)
        report_data[repo].append((label, count))

# Render HTML report
env = Environment(loader=FileSystemLoader('.'))
template = env.from_string("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>GitHub Commits Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container mt-5">
    <h1 class="mb-4">GitHub Commits Report (Last 3 Months)</h1>
    {% for repo, data in report_data.items() %}
    <div class="card mb-4 shadow">
        <div class="card-header bg-dark text-white">
            <h5 class="mb-0">{{ repo }}</h5>
        </div>
        <div class="card-body">
            <table class="table table-striped">
                <thead><tr><th>Month</th><th>Commits</th></tr></thead>
                <tbody>
                    {% for label, count in data %}
                    <tr><td>{{ label }}</td><td>{{ count }}</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endfor %}
</div>
</body>
</html>
""")

output = template.render(report_data=report_data)
with open("github_commits_report.html", "w") as f:
    f.write(output)

print("✅ Report generated: github_commits_report.html")