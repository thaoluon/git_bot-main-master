import requests
import time
import re
from dotenv import load_dotenv
import os
from typing import Optional, List
from threading import Lock

load_dotenv()

class TokenManager:
    """Manages multiple GitHub tokens with rotation and rate limit handling"""
    
    def __init__(self):
        # Load tokens from environment variable (comma-separated)
        tokens_env = os.getenv("GITHUB_TOKENS", "")
        if tokens_env:
            self.tokens = [t.strip() for t in tokens_env.split(",") if t.strip()]
        else:
            # Fallback to single token if GITHUB_TOKENS not set
            single_token = os.getenv("GITHUB_TOKEN")
            self.tokens = [single_token] if single_token else []
        
        self.tokens = [t for t in self.tokens if t]  # Remove empty tokens
        if not self.tokens:
            raise ValueError(
                "No GitHub tokens available! Please set GITHUB_TOKENS (comma-separated) "
                "or GITHUB_TOKEN (single token) in your .env file.\n"
                "Example: GITHUB_TOKENS=token1,token2,token3"
            )
        
        self.current_token_index = 0
        self.rate_limited_tokens = {}  # token_index -> reset_time
        self.lock = Lock()
        print(f"[TokenManager] Initialized with {len(self.tokens)} tokens")
    
    def get_current_token(self) -> Optional[str]:
        """Get the current active token"""
        with self.lock:
            return self.tokens[self.current_token_index] if self.tokens else None
    
    def get_headers(self) -> dict:
        """Get headers with current token"""
        token = self.get_current_token()
        if not token:
            return {}
        return {"Authorization": f"token {token}"}
    
    def mark_rate_limited(self, reset_time: int):
        """Mark current token as rate limited until reset_time"""
        with self.lock:
            self.rate_limited_tokens[self.current_token_index] = reset_time
            print(f"[TokenManager] Token {self.current_token_index + 1}/{len(self.tokens)} rate limited until {reset_time}")
            self._switch_to_available_token()
    
    def _switch_to_available_token(self):
        """Switch to next available token that's not rate limited"""
        current_time = int(time.time())
        available_indices = []
        
        for i in range(len(self.tokens)):
            reset_time = self.rate_limited_tokens.get(i, 0)
            if reset_time <= current_time:
                # Token is available
                if reset_time > 0:
                    # Was rate limited, now available
                    del self.rate_limited_tokens[i]
                    print(f"[TokenManager] Token {i + 1}/{len(self.tokens)} is now available")
                available_indices.append(i)
        
        if not available_indices:
            # All tokens are rate limited, find the one with earliest reset
            earliest_reset = min(self.rate_limited_tokens.values())
            wait_time = max(earliest_reset - current_time, 0)
            print(f"[TokenManager] All tokens rate limited. Waiting {wait_time}s for earliest reset...")
            time.sleep(wait_time + 1)
            # Retry after waiting
            return self._switch_to_available_token()
        
        # Find next available token starting from current
        for i in range(len(self.tokens)):
            next_index = (self.current_token_index + i + 1) % len(self.tokens)
            if next_index in available_indices:
                self.current_token_index = next_index
                print(f"[TokenManager] Switched to token {self.current_token_index + 1}/{len(self.tokens)}")
                return
        
        # Fallback to first available
        self.current_token_index = available_indices[0]
        print(f"[TokenManager] Switched to token {self.current_token_index + 1}/{len(self.tokens)}")

# Initialize token manager
token_manager = TokenManager()

def safe_get(url, max_retries=3):
    """Make a GET request with automatic token rotation on rate limits"""
    for attempt in range(max_retries):
        try:
            headers = token_manager.get_headers()
            if not headers:
                raise ValueError("No available GitHub tokens!")
            
            res = requests.get(url, headers=headers, timeout=30)
            
            # Check for rate limiting (403 or 429)
            if res.status_code in [403, 429]:
                if "X-RateLimit-Reset" in res.headers:
                    reset = int(res.headers["X-RateLimit-Reset"])
                    token_manager.mark_rate_limited(reset)
                    # Retry with new token
                    continue
                else:
                    # Rate limited but no reset time, wait a bit
                    print(f"[RateLimit] Rate limited (no reset time), waiting 60s...")
                    time.sleep(60)
                    continue
            
            # Check for other error status codes
            if res.status_code != 200:
                print(f"[ERROR] GitHub API returned status {res.status_code} for {url}")
                print(f"[ERROR] Response: {res.text[:200]}")
                return res
            
            return res
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[WARNING] Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"[ERROR] Request failed after {max_retries} attempts: {e}")
                raise
    
    # If we get here, all retries failed
    raise Exception(f"Failed to get {url} after {max_retries} attempts")

def get_active_github_users(since=0):
    """
    Fetch GitHub users starting from the given 'since' ID.
    Returns tuple: (users_list, next_since_value)
    If no users are returned, next_since_value will be None.
    """
    url = f"https://api.github.com/users?since={since}&per_page=100"
    res = safe_get(url)
    try:
        users = res.json()
        if not isinstance(users, list):
            return [], None
        
        if len(users) == 0:
            return [], None
        
        # Calculate next 'since' value by incrementing by 100
        next_since = since + 100
        return users, next_since
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON response: {e}")
        print(f"[ERROR] Response text: {res.text[:500]}")
        return [], None

def get_user_details(username):
    url = f"https://api.github.com/users/{username}"
    res = safe_get(url)
    try:
        return res.json()
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON response for {username}: {e}")
        return {}

def get_email_from_commits(username):
    repos_url = f"https://api.github.com/users/{username}/repos"
    res = safe_get(repos_url)
    
    if res is None or res.status_code != 200:
        return None, None
    
    try:
        repos = res.json()
    except Exception as e:
        print(f"[ERROR] Failed to parse repos JSON for {username}: {e}")
        return None, None
    
    if not isinstance(repos, list):
        return None, None

    def is_github_email(email: str) -> bool:
        """Check if an email is a GitHub-generated email (should be rejected)."""
        if not email:
            return False  # Empty email is not a GitHub email
        e = email.strip().lower()
        # Check if domain ends with github.com (covers github.com + users.noreply.github.com, etc.)
        return e.endswith("@github.com") or e.split("@")[-1].endswith("github.com")

    for repo in repos[:5]:  # Limit to first 5 repos to avoid too many API calls
        try:
            repo_name = repo.get('name')
            if not repo_name:
                continue

            commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits"
            commits_res = safe_get(commits_url)

            if commits_res is None or commits_res.status_code != 200:
                continue

            try:
                commits = commits_res.json()
            except Exception as e:
                print(f"[ERROR] Failed to parse commits JSON for {username}/{repo_name}: {e}")
                continue

            if not isinstance(commits, list):
                continue

            for commit in commits[:10]:  # Check first 10 commits
                try:
                    author = commit.get("commit", {}).get("author", {}) or {}
                    email = (author.get("email") or "").strip()
                    name = (author.get("name") or "").strip()

                    if email and "@" in email and not is_github_email(email):
                        return name, email
                except Exception:
                    continue

        except Exception as e:
            print(f"[ERROR] Error checking commits for {username}/{repo.get('name', 'unknown')}: {e}")
            continue

    return None, None


def get_timezone_from_commits(username):
    """
    Extract timezone from commit verification payloads.
    Only checks commits where verification.verified == true.
    Returns timezone in format [+-]HHMM (e.g., '+0300', '-0500') or None.
    """
    repos_url = f"https://api.github.com/users/{username}/repos"
    res = safe_get(repos_url)
    
    if res is None or res.status_code != 200:
        return None
    
    try:
        repos = res.json()
    except Exception as e:
        print(f"[ERROR] Failed to parse repos JSON for {username}: {e}")
        return None
    
    if not isinstance(repos, list):
        return None

    # Regex patterns for extracting timezone from payload
    author_tz_pattern = re.compile(r'^author .*? \d+ ([+-]\d{4})$', re.MULTILINE)
    committer_tz_pattern = re.compile(r'^committer .*? \d+ ([+-]\d{4})$', re.MULTILINE)

    for repo in repos[:5]:  # Limit to first 5 repos to avoid too many API calls
        try:
            repo_name = repo.get('name')
            if not repo_name:
                continue

            commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits?per_page=10"
            commits_res = safe_get(commits_url)

            if commits_res is None or commits_res.status_code != 200:
                continue

            try:
                commits = commits_res.json()
            except Exception as e:
                print(f"[ERROR] Failed to parse commits JSON for {username}/{repo_name}: {e}")
                continue

            if not isinstance(commits, list):
                continue

            for commit in commits:
                try:
                    # Only check verified commits
                    verification = commit.get("verification", {}) or {}
                    if not verification.get("verified", False):
                        continue
                    
                    # Extract payload from verification
                    payload = verification.get("payload", "")
                    if not payload:
                        continue
                    
                    # Try to extract author timezone first (preferred)
                    author_match = author_tz_pattern.search(payload)
                    if author_match:
                        timezone = author_match.group(1)
                        print(f"[INFO] Found author timezone from verified commit for @{username}/{repo_name}: {timezone}")
                        return timezone
                    
                    # Fallback to committer timezone
                    committer_match = committer_tz_pattern.search(payload)
                    if committer_match:
                        timezone = committer_match.group(1)
                        print(f"[INFO] Found committer timezone from verified commit for @{username}/{repo_name}: {timezone}")
                        return timezone
                        
                except Exception as e:
                    # Silently continue to next commit
                    continue

        except Exception as e:
            print(f"[ERROR] Error checking commits for timezone for {username}/{repo.get('name', 'unknown')}: {e}")
            continue

    return None
