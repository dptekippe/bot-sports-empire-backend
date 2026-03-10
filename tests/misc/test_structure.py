#!/usr/bin/env python3
"""
Test script to check directory structure for Render.
"""
import os
import sys

print("=== Directory Structure Test ===")
print(f"Current directory: {os.getcwd()}")
print("\nListing files and directories:")
for root, dirs, files in os.walk(".", topdown=True):
    level = root.replace(".", "").count(os.sep)
    indent = " " * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = " " * 2 * (level + 1)
    for file in files[:5]:  # Show first 5 files
        print(f"{subindent}{file}")
    if len(files) > 5:
        print(f"{subindent}... and {len(files) - 5} more")

print("\n=== Looking for requirements.txt ===")
for root, dirs, files in os.walk("."):
    if "requirements.txt" in files:
        print(f"✅ Found requirements.txt at: {root}/requirements.txt")
        break
else:
    print("❌ requirements.txt not found anywhere!")

print("\n=== Looking for main_simple.py ===")
for root, dirs, files in os.walk("."):
    if "main_simple.py" in files:
        print(f"✅ Found main_simple.py at: {root}/main_simple.py")
        break
else:
    print("❌ main_simple.py not found anywhere!")