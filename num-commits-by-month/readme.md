# GitHub Commits Report

This Python app reads a list of GitHub repositories from a YAML file, retrieves the number of commits for each of the past 3 full calendar months, and generates a slick, Bootstrap-styled HTML report.

## 📦 Features

- 🔐 Authenticated GitHub API access using a `.env` token
- 📅 Monthly commit counts for each repo
- 📄 Clean, styled HTML report
- 🛠 Configurable repo list via `repos.yml`

---

## 📁 Project Structure

.
├── github_commits_report.py # Main script
├── repos.yml # YAML file listing GitHub repos
├── .env # Contains your GitHub token (not committed)
├── .gitignore # Excludes environment, secrets, etc.
└── github_commits_report.html # Output report (generated)


---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/github-commits-report.git
cd github-commits-report
```
### 2. Create and activate a virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 3. Install dependencies

```bash
pip install -r requirements.txt
```
Or manually:

```bash
pip install requests python-dotenv jinja2 pyyaml
```

### 4. Add your GitHub token
Create a file named .envrc in the project root:

```bash
GITHUB_TOKEN=your_personal_access_token
```

⚠️ The token must have access to the repositories (public or private).

### 5. Define your repositories
Create a file named repos.yml:

```yaml
repos:
  - octocat/Hello-World
  - tensorflow/tensorflow
  - microsoft/vscode
```

### 6. Run the script

```bash
python github_commits_report.py
```

This will generate github_commits_report.html in the same directory.

🧾 Example Output
The HTML report shows commit counts for each repo by month in a styled Bootstrap table.