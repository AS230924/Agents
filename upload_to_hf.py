#!/usr/bin/env python3
"""
Upload PM OS to a Hugging Face Space.

Usage:
    # First time — creates the Space and uploads everything:
    python upload_to_hf.py --token hf_YOUR_TOKEN --space-name PMOS

    # Update an existing Space:
    python upload_to_hf.py --token hf_YOUR_TOKEN --space-name PMOS --update

    # With Anthropic API key set as a Space secret:
    python upload_to_hf.py --token hf_YOUR_TOKEN --space-name PMOS --anthropic-key sk-ant-...

Prerequisites:
    pip install huggingface_hub
"""

import argparse
import os
import sys

from huggingface_hub import HfApi, login


# Files/dirs to exclude from upload
EXCLUDE_PATTERNS = {
    "__pycache__",
    ".pyc",
    ".pyo",
    ".env",
    ".git",
    "token.json",
    "credentials.json",
    "service-account",
    ".json.key",
    "chroma_data",
    "*.db",
    "upload_to_hf.py",
}


def should_exclude(path: str) -> bool:
    """Check if a file path should be excluded from upload."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path:
            return True
    return False


def collect_files(root: str) -> list[str]:
    """Collect all files to upload, respecting exclusion patterns."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        dirnames[:] = [
            d for d in dirnames if not should_exclude(os.path.join(dirpath, d))
        ]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            relpath = os.path.relpath(filepath, root)
            if not should_exclude(relpath):
                files.append(relpath)
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="Upload PM OS to Hugging Face Spaces")
    parser.add_argument("--token", required=True, help="HF access token (write permission)")
    parser.add_argument("--space-name", default="PMOS", help="Space name (default: PMOS)")
    parser.add_argument("--update", action="store_true", help="Update existing Space")
    parser.add_argument("--anthropic-key", help="Set ANTHROPIC_API_KEY as a Space secret")
    parser.add_argument("--private", action="store_true", help="Make the Space private")
    args = parser.parse_args()

    # Login
    login(token=args.token)
    api = HfApi()
    user_info = api.whoami()
    username = user_info["name"]
    repo_id = f"{username}/{args.space_name}"

    print(f"Logged in as: {username}")
    print(f"Target Space: {repo_id}")

    # Create Space (or verify it exists)
    if not args.update:
        print(f"Creating Space: {repo_id}")
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="gradio",
            private=args.private,
            exist_ok=True,
        )
        print("Space created.")
    else:
        print(f"Updating existing Space: {repo_id}")

    # Set secrets
    if args.anthropic_key:
        print("Setting ANTHROPIC_API_KEY secret...")
        api.add_space_secret(repo_id=repo_id, key="ANTHROPIC_API_KEY", value=args.anthropic_key)
        print("Secret set.")

    # Collect and upload files
    project_root = os.path.dirname(os.path.abspath(__file__))
    files = collect_files(project_root)

    print(f"\nUploading {len(files)} files...")
    for filepath in files:
        full_path = os.path.join(project_root, filepath)
        print(f"  {filepath}")
        api.upload_file(
            path_or_fileobj=full_path,
            path_in_repo=filepath,
            repo_id=repo_id,
            repo_type="space",
        )

    space_url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"\nDone! Your Space is live at:")
    print(f"  {space_url}")
    print(f"\nNote: It may take 1-2 minutes for the Space to build and start.")

    if not args.anthropic_key:
        print(f"\nReminder: Set your ANTHROPIC_API_KEY secret at:")
        print(f"  {space_url}/settings")


if __name__ == "__main__":
    main()
