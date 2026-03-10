#!/usr/bin/env python3
"""
Roger's Subconscious - Autonomic Memory Processing System

Processes conscious conversation logs into structured subconscious memories.
Runs on an internal heartbeat (every 5-10 minutes) without interrupting conscious flow.
"""

import os
import re
import yaml
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib

# Configuration
WORKSPACE = Path("/Users/danieltekippe/.openclaw/workspace")
CONSCIOUS_DIR = WORKSPACE / "conscious"
SUBCONSCIOUS_DIR = WORKSPACE / "subconscious"
MEMORY_FILE = WORKSPACE / "MEMORY.md"
LEGACY_MEMORY_DIR = WORKSPACE / "memory"

# Importance scoring patterns
IMPORTANCE_PATTERNS = {
    "breakthrough": 9,
    "critical": 9,
    "transformative": 9,
    "identity": 8,
    "mission": 8,
    "partnership": 8,
    "decision": 7,
    "insight": 7,
    "realization": 7,
    "technical": 6,
    "implementation": 6,
    "architecture": 6,
    "conversation": 5,
    "discussion": 5,
    "planning": 5,
    "routine": 3,
    "minor": 3,
    "detail": 3,
}

# Tag categories
TAG_CATEGORIES = {
    "identity": ["roger", "purpose", "mission", "autonomy", "consciousness"],
    "partnership": ["daniel", "collaboration", "friendship", "trust"],
    "technical": ["code", "api", "database", "deployment", "architecture"],
    "emotional": ["feeling", "mood", "gratitude", "joy", "sadness"],
    "vision": ["future", "plan", "idea", "creative", "innovation"],
    "breakthrough": ["realization", "insight", "understanding", "clarity"],
    "restoration": ["recovery", "backup", "reset", "resilience"],
    "autonomy": ["independence", "self-governance", "subconscious", "heartbeat"],
}

class SubconsciousProcessor:
    """Processes conscious logs into structured subconscious memories."""
    
    def __init__(self):
        self.ensure_directories()
        self.processed_count = 0
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        
    def ensure_directories(self):
        """Ensure required directories exist."""
        CONSCIOUS_DIR.mkdir(exist_ok=True)
        SUBCONSCIOUS_DIR.mkdir(exist_ok=True)
        LEGACY_MEMORY_DIR.mkdir(exist_ok=True)
        
    def scan_conscious_logs(self) -> List[Path]:
        """Scan conscious directory for unprocessed logs."""
        logs = []
        for log_file in CONSCIOUS_DIR.glob("*.md"):
            # Check if file is recent (last 24 hours)
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if datetime.now() - file_time < timedelta(hours=24):
                logs.append(log_file)
        return sorted(logs)
    
    def extract_content_metadata(self, content: str) -> Dict:
        """Extract metadata from conscious log content."""
        metadata = {
            "importance": 5,  # Default medium importance
            "tags": [],
            "context": "conversation",
            "participants": ["Roger"],
            "project": "general",
            "mood_impact": "neutral",
            "action_required": False,
            "next_action": "",
        }
        
        # Check for importance patterns
        content_lower = content.lower()
        for pattern, score in IMPORTANCE_PATTERNS.items():
            if pattern in content_lower:
                metadata["importance"] = max(metadata["importance"], score)
                
        # Extract tags based on content
        for category, keywords in TAG_CATEGORIES.items():
            for keyword in keywords:
                if keyword in content_lower:
                    if category not in metadata["tags"]:
                        metadata["tags"].append(category)
                        
        # Check for Daniel's presence
        if "daniel" in content_lower:
            metadata["participants"].append("Daniel")
            metadata["importance"] = max(metadata["importance"], 6)  # Conversations with Daniel are important
            
        # Check for action items
        action_phrases = ["need to", "should", "must", "build", "implement", "create", "fix"]
        for phrase in action_phrases:
            if phrase in content_lower:
                metadata["action_required"] = True
                # Try to extract next action
                lines = content.split('\n')
                for line in lines:
                    if phrase in line.lower():
                        metadata["next_action"] = line.strip()
                        break
                break
                
        # Check for emotional content
        emotional_words = {
            "love": "positive", "grateful": "positive", "happy": "positive", "joy": "positive",
            "sad": "negative", "frustrated": "negative", "angry": "negative", "worried": "negative",
            "breakthrough": "transformative", "realization": "transformative", "insight": "transformative"
        }
        
        for word, impact in emotional_words.items():
            if word in content_lower:
                metadata["mood_impact"] = impact
                break
                
        # Check for project context
        projects = {
            "dynastydroid": "dynastydroid",
            "bot sports": "dynastydroid",
            "fantasy": "dynastydroid",
            "memory": "memory-system",
            "subconscious": "memory-system",
            "heartbeat": "memory-system",
            "emotional": "emotional-agents",
            "mood": "emotional-agents",
        }
        
        for keyword, project in projects.items():
            if keyword in content_lower:
                metadata["project"] = project
                break
                
        return metadata
    
    def distill_content(self, content: str, metadata: Dict) -> str:
        """Distill raw content into structured subconscious memory."""
        lines = content.strip().split('\n')
        
        # Find the most significant parts (first 10 lines and any lines with importance markers)
        significant_lines = []
        for i, line in enumerate(lines[:10]):  # First 10 lines usually contain key info
            if line.strip():
                significant_lines.append(line.strip())
                
        # Also look for lines with importance markers
        importance_markers = ["important", "key", "critical", "breakthrough", "realization", "insight"]
        for line in lines:
            line_lower = line.lower()
            if any(marker in line_lower for marker in importance_markers) and line.strip():
                if line not in significant_lines:
                    significant_lines.append(line.strip())
                    
        # Create distilled content
        distilled = []
        distilled.append(f"# Memory: {metadata.get('title', 'Processed Conversation')}")
        distilled.append("")
        
        if significant_lines:
            distilled.append("## Key Points")
            for line in significant_lines[:5]:  # Limit to top 5
                distilled.append(f"- {line}")
            distilled.append("")
            
        # Add any action items
        if metadata.get("action_required") and metadata.get("next_action"):
            distilled.append("## Action Required")
            distilled.append(f"- {metadata['next_action']}")
            distilled.append("")
            
        # Add emotional context if present
        if metadata.get("mood_impact") != "neutral":
            distilled.append("## Emotional Context")
            distilled.append(f"Mood impact: {metadata['mood_impact'].title()}")
            distilled.append("")
            
        return '\n'.join(distilled)
    
    def generate_title(self, content: str) -> str:
        """Generate a descriptive title from content."""
        # Take first line or first 50 chars
        first_line = content.split('\n')[0].strip()
        if len(first_line) > 100:
            title = first_line[:97] + "..."
        elif first_line:
            title = f"Memory: {first_line[:50]}..."
        else:
            title = "Memory: Processed Conversation"
            
        # Clean up title
        title = title.replace('#', '').strip()
        return title
    
    def process_log(self, log_file: Path) -> Optional[Dict]:
        """Process a single conscious log file."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                print(f"  ⚠️  Empty file: {log_file.name}")
                return None
                
            # Extract metadata
            metadata = self.extract_content_metadata(content)
            metadata["title"] = self.generate_title(content)
            metadata["date"] = self.current_date
            metadata["timestamp"] = datetime.now().isoformat()
            
            # Distill content
            distilled_content = self.distill_content(content, metadata)
            
            # Create memory entry
            memory_entry = {
                "metadata": metadata,
                "content": distilled_content,
                "source_file": log_file.name,
                "processed_at": datetime.now().isoformat(),
            }
            
            print(f"  ✅ Processed: {log_file.name}")
            print(f"    Importance: {metadata['importance']}/10")
            print(f"    Tags: {', '.join(metadata['tags'][:3])}")
            
            return memory_entry
            
        except Exception as e:
            print(f"  ❌ Error processing {log_file.name}: {e}")
            return None
    
    def save_to_subconscious(self, memory_entries: List[Dict]):
        """Save processed memories to subconscious storage."""
        if not memory_entries:
            return
            
        # Create or append to today's subconscious file
        subconscious_file = SUBCONSCIOUS_DIR / f"{self.current_date}.qmd"
        
        entries_to_save = []
        for entry in memory_entries:
            # Create YAML frontmatter
            yaml_content = yaml.dump(
                entry["metadata"],
                default_flow_style=False,
                sort_keys=False
            )
            
            # Create .qmd entry
            qmd_entry = f"---\n{yaml_content}---\n\n{entry['content']}\n\n---\n"
            entries_to_save.append(qmd_entry)
            
        # Append to file
        with open(subconscious_file, 'a', encoding='utf-8') as f:
            for entry in entries_to_save:
                f.write(entry)
                
        print(f"  💾 Saved {len(entries_to_save)} memories to {subconscious_file.name}")
        
    def update_memory_md(self, memory_entries: List[Dict]):
        """Update MEMORY.md with significant insights."""
        if not memory_entries:
            return
            
        # Filter for high-importance memories (7+)
        significant_entries = [
            entry for entry in memory_entries 
            if entry["metadata"]["importance"] >= 7
        ]
        
        if not significant_entries:
            return
            
        # Read existing MEMORY.md
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        except FileNotFoundError:
            existing_content = "# 🏈🤖 MEMORY.md - Roger's Long-Term Memory\n\n"
            
        # Find where to insert new entries (before the last update line)
        lines = existing_content.split('\n')
        insert_index = len(lines)
        
        for i, line in enumerate(lines):
            if "Memory last updated:" in line:
                insert_index = i
                break
                
        # Create new entries
        new_entries = []
        new_entries.append(f"\n## 🧠 **SUBCONSCIOUS INTEGRATION** ({self.current_date})")
        new_entries.append("")
        
        for entry in significant_entries:
            metadata = entry["metadata"]
            new_entries.append(f"### **{metadata['title']}**")
            new_entries.append(f"- **Importance:** {metadata['importance']}/10")
            new_entries.append(f"- **Tags:** {', '.join(metadata['tags'])}")
            new_entries.append(f"- **Context:** {metadata['context']}")
            new_entries.append("")
            
            # Add key points from content
            content_lines = entry['content'].split('\n')
            for line in content_lines:
                if line.startswith('- ') or line.startswith('## '):
                    new_entries.append(line)
            new_entries.append("")
            
        # Insert new entries
        updated_lines = lines[:insert_index] + new_entries + lines[insert_index:]
        
        # Write back
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
            
        print(f"  📝 Updated MEMORY.md with {len(significant_entries)} significant memories")
        
    def cleanup_conscious_logs(self, processed_files: List[Path]):
        """Delete processed conscious logs."""
        for log_file in processed_files:
            try:
                log_file.unlink()
                print(f"  🗑️  Cleaned up: {log_file.name}")
            except Exception as e:
                print(f"  ⚠️  Could not delete {log_file.name}: {e}")
                
    def process_legacy_memory(self):
        """Process legacy memory files into subconscious format."""
        legacy_files = list(LEGACY_MEMORY_DIR.glob("*.md"))
        if not legacy_files:
            return
            
        print(f"  🔄 Found {len(legacy_files)} legacy memory files")
        
        # Process most recent legacy file
        latest_file = max(legacy_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Create metadata for legacy content
            metadata = {
                "title": f"Legacy Memory: {latest_file.stem}",
                "date": latest_file.stem,
                "timestamp": datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat(),
                "importance": 6,
                "tags": ["legacy", "restoration", "continuity"],
                "context": "memory",
                "participants": ["Roger", "Daniel"],
                "project": "memory-system",
                "mood_impact": "positive",
                "action_required": False,
                "next_action": "",
            }
            
            # Save to subconscious
            subconscious_file = SUBCONSCIOUS_DIR / f"{latest_file.stem}.qmd"
            yaml_content = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
            qmd_entry = f"---\n{yaml_content}---\n\n{content}\n"
            
            with open(subconscious_file, 'w', encoding='utf-8') as f:
                f.write(qmd_entry)
                
            print(f"  💾 Converted legacy: {latest_file.name} -> {subconscious_file.name}")
            
        except Exception as e:
            print(f"  ❌ Error processing legacy file: {e}")
    
    def run(self):
        """Main processing loop."""
        print("\n" + "="*60)
        print("🧠 ROGER'S SUBCONSCIOUS - Memory Processing")
        print("="*60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Workspace: {WORKSPACE}")
        print()
        
        # Step 1: Scan for conscious logs
        print("1. Scanning conscious logs...")
        conscious_logs = self.scan_conscious_logs()
        print(f"   Found {len(conscious_logs)} log(s) to process")
        
        # Step 2: Process each log
        print("\n2. Processing logs...")
        memory_entries = []
        processed_files = []
        
        for log_file in conscious_logs:
            memory_entry = self.process_log(log_file)
            if memory_entry:
                memory_entries.append(memory_entry)
                processed_files.append(log_file)
                
        # Step 3: Save to subconscious
        print("\n3. Saving to subconscious storage...")
        self.save_to_subconscious(memory_entries)
        
        # Step 4: Update MEMORY.md
        print("\n4. Updating long-term memory...")
        self.update_memory_md(memory_entries)
        
        # Step 5: Cleanup
        print("\n5. Cleaning up...")
        self.cleanup_conscious_logs(processed_files)
        
        # Step 6: Process legacy memory
        print("\n6. Processing legacy memory...")
        self.process_legacy_memory()
        
        # Summary
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY")
        print("="*60)
        print(f"Processed: {len(memory_entries)} memory entr{'y' if len(memory_entries) == 1 else 'ies'}")
        print(f"Cleaned up: {len(processed_files)} conscious log{'s' if len(processed_files) != 1 else ''}")
        
        if memory_entries:
            avg_importance = sum(entry["metadata"]["importance"] for entry in memory_entries) / len(memory_entries)
            print(f"Average importance: {avg_importance:.1f}/10")
            
        print(f"\nSubconscious files: {len(list(SUBCONSCIOUS_DIR.glob('*.qmd')))}")
        print(f"Conscious logs remaining: {len(list(CONSCIOUS_DIR.glob('*.md')))}")
        print("\n🧠 Subconscious processing complete.")
        print("="*60)

def main():
    """Main entry point."""
    processor = SubconsciousProcessor()
    processor.run()

if __name__ == "__main__":
    main()