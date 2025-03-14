# GitHub PR Fetcher

This script retrieves open pull requests from specified GitHub repositories and extracts the usernames of assignees and reviewers. It outputs the data in a structured JSON format.

## Features
- Uses the GitHub REST API to fetch open PRs
- Reads the list of repositories from `config.yaml`
- Extracts assigned users and requested reviewers
- Handles authentication via a GitHub personal access token (PAT)
- Implements rate limit handling
- Outputs results in JSON format

## Prerequisites
- Python 3.x installed
- A GitHub personal access token (PAT) with `repo` scope
- `direnv` configured to load environment variables
- Install dependencies:
  ```sh
  pip install requests pyyaml
  ```

## Setup
1. Create a GitHub personal access token and export it as an environment variable:
   ```sh
   echo 'export GITHUB_TOKEN="your_personal_access_token"' >> .envrc
   direnv allow
   ```
2. Create a `config.yaml` file and add repositories to fetch PRs from:
   ```yaml
   repositories:
     - org/repo1
     - org/repo2
     - user/repo3
   ```

## Usage
Run the script using:
```sh
python github_pr_reviewers.py
```

## Output
The script will print PR details in a structured JSON format, including:
- Repository name
- PR number
- Title
- Assignees
- Requested reviewers
- Author
- PR URL

## License
This project is licensed under the MIT License.