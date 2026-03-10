#!/bin/bash
# Git sync script for workspace
# Pulls latest changes from remote

cd /workspace || exit 1

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "Not a git repository"
    exit 1
fi

# Fetch and check status
git fetch origin

# Get current branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Check if we need to pull
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "Changes available on remote, pulling..."
    git pull origin $BRANCH
else
    echo "Branch $BRANCH is up to date"
fi
