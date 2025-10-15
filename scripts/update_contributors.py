#!/usr/bin/env python3
"""
Script to update CONTRIBUTORS.md with contributor information from GitHub API.
"""

import base64
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import requests


def get_contributors(
    repo_owner: str, repo_name: str, token: str
) -> list[dict[str, Any]]:
    """Fetch contributors from GitHub API."""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contributors"
    headers = {"Accept": "application/vnd.github.v3+json"}

    # Only add authorization header if we have a real token
    if token != "anonymous":
        headers["Authorization"] = f"token {token}"

    # Get all contributors (up to 100 per page)
    all_contributors = []
    page = 1
    per_page = 100

    while True:
        params = {"page": page, "per_page": per_page}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Error fetching contributors: {response.status_code}")
            print(f"Response: {response.text}")
            return []

        contributors = response.json()
        if not contributors:
            break

        all_contributors.extend(contributors)
        page += 1

        # Safety check to avoid infinite loops
        if page > 10:
            break

    return all_contributors


def get_user_details(username: str, token: str) -> dict[str, Any]:
    """Get detailed user information."""
    url = f"https://api.github.com/users/{username}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    # Return basic info if detailed fetch fails
    return {
        "login": username,
        "avatar_url": f"https://avatars.githubusercontent.com/u/{hash(username) % 1000000}?v=4",
        "html_url": f"https://github.com/{username}",
        "name": username,
        "contributions": 0,
    }


def generate_contributor_row(
    contributor: dict[str, Any],
    user_details: dict[str, Any],
    repo_owner: str,
    repo_name: str,
) -> str:
    """Generate a markdown table row for a contributor."""
    username = contributor["login"]
    avatar_url = user_details.get(
        "avatar_url",
        f"https://avatars.githubusercontent.com/u/{hash(username) % 1000000}?v=4",
    )
    profile_url = user_details.get("html_url", f"https://github.com/{username}")
    display_name = user_details.get("name", username)

    return f"""      <td align="center" valign="top" width="14.28%"><a href="{profile_url}"><img src="{avatar_url}?s=100" width="100px;" alt="{display_name}"/><br /><sub><b>{display_name}</b></sub></a><br /><a href="https://github.com/{repo_owner}/{repo_name}/commits?author={username}" title="Code">💻</a></td>"""


def update_contributors_file(
    contributors: list[dict[str, Any]], repo_owner: str, repo_name: str
):
    """Update the CONTRIBUTORS.md file with new contributor data."""
    # Generate contributor rows
    contributor_rows = []
    for contributor in contributors[:20]:  # Limit to first 20 contributors
        username = contributor["login"]
        user_details = get_user_details(username, os.getenv("GITHUB_TOKEN", ""))
        contributor_rows.append(
            generate_contributor_row(contributor, user_details, repo_owner, repo_name)
        )

    # Fill remaining cells if we have less than 7 contributors (for a full row)
    while len(contributor_rows) < 7:
        contributor_rows.append(
            '      <td align="center" valign="top" width="14.28%"></td>'
        )

    # Create the contributors table
    contributors_table = "\n".join(contributor_rows)

    # Read current file
    try:
        with open("CONTRIBUTORS.md", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("CONTRIBUTORS.md not found")
        return False

    # Replace the contributors section
    start_marker = (
        "<!-- CONTRIBUTORS-LIST:START - Do not remove or modify this section -->"
    )
    end_marker = "<!-- CONTRIBUTORS-LIST:END -->"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("Could not find contributors markers in file")
        return False

    # Replace the section
    before = content[: start_idx + len(start_marker)]
    after = content[end_idx:]

    new_content = f"""{before}
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->

<table>
  <tbody>
    <tr>
{contributors_table}
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
{after}"""

    # Write back to file
    with open("CONTRIBUTORS.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated CONTRIBUTORS.md with {len(contributors)} contributors")
    return True


def main():
    """Main function."""
    repo_owner = os.getenv("REPO_OWNER", "DeepCritical")
    repo_name = os.getenv("REPO_NAME", "DeepCritical")
    token = os.getenv("GITHUB_TOKEN")

    # Use a default token for testing if none provided
    if not token:
        print(
            "Warning: No GITHUB_TOKEN provided, using anonymous access (limited to 60 requests/hour)"
        )
        token = "anonymous"

    print(f"Using repository: {repo_owner}/{repo_name}")

    print(f"Fetching contributors for {repo_owner}/{repo_name}...")

    contributors = get_contributors(repo_owner, repo_name, token)

    if not contributors:
        print("No contributors found or error fetching data")
        sys.exit(1)

    print(f"Found {len(contributors)} contributors")

    # Sort by contributions (most first)
    contributors.sort(key=lambda x: x["contributions"], reverse=True)

    success = update_contributors_file(contributors, repo_owner, repo_name)

    if success:
        print("Contributors file updated successfully!")
    else:
        print("Failed to update contributors file")
        sys.exit(1)


if __name__ == "__main__":
    main()
