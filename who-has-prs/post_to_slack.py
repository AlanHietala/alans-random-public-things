import json
import os
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load Slack Webhook URL from environment variable
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

if not SLACK_WEBHOOK_URL:
    raise ValueError("SLACK_WEBHOOK_URL environment variable is not set.")

def load_pr_data(json_file: str):
    """Loads PR data from JSON file."""
    try:
        with open(json_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"JSON file {json_file} not found.")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON file {json_file}.")
        return []

def format_slack_message(pr_data):
    """Formats PR data into a structured Slack message."""
    if not pr_data:
        return {"text": "No PRs found for reviewers."}

    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "*GitHub PR Review Summary* 📢"}}]

    for developer in pr_data:
        dev_name = developer["developer"]
        prs = developer["reviewing_prs"]

        if not prs:
            continue

        pr_list = "\n".join([f"- <{pr['url']}|{pr['title']}>" for pr in prs])
        dev_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{dev_name}* 👤\n{pr_list}"
            }
        }
        blocks.append(dev_block)
        blocks.append({"type": "divider"})

    return {"blocks": blocks}

def post_to_slack(pr_data):
    """Posts formatted PR data to Slack."""
    payload = format_slack_message(pr_data)
    
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    
    if response.status_code == 200:
        logging.info("Successfully posted PR review summary to Slack.")
    else:
        logging.error(f"Failed to post to Slack: {response.status_code} - {response.text}")

if __name__ == "__main__":
    pr_data = load_pr_data("reviewers_prs.json")

    if pr_data:
        post_to_slack(pr_data)
    else:
        logging.error("No valid PR data to post.")