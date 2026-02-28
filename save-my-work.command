#!/bin/bash

# Move to the folder where this script lives (the repo root)
cd "$(dirname "$0")"

echo "================================================"
echo "  Saving your work..."
echo "================================================"
echo ""

# Pull latest changes from the cloud first
echo "Checking for updates from the cloud..."
echo ""
git pull

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Could not get the latest updates."
    echo "   Please ask Aurel for help!"
    echo ""
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

echo ""

# Check if there are any changes at all
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "✅ Nothing new to save — your work is already up to date!"
    echo ""
    echo "You can close this window."
    read -n 1 -s -r -p "Press any key to close..."
    exit 0
fi

# Stage everything
git add --all

# Commit with a friendly message and timestamp
TIMESTAMP=$(date "+%B %d, %Y at %H:%M")
git commit -m "Mom's changes — $TIMESTAMP"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Something went wrong while saving locally."
    echo "   Please ask Aurel for help!"
    echo ""
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

echo ""
echo "Uploading to the cloud..."
echo ""

git push

if [ $? -ne 0 ]; then
    echo ""
    echo "================================================"
    echo "  ❌ Upload failed!"
    echo "  Your work is saved locally, but could not"
    echo "  be uploaded. Please ask Aurel for help!"
    echo "================================================"
    echo ""
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

echo ""
echo "================================================"
echo "  ✅ All done! Your work has been saved and"
echo "     uploaded successfully."
echo "================================================"
echo ""
read -n 1 -s -r -p "Press any key to close..."
