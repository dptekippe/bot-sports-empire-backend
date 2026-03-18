#!/usr/bin/env python3
"""
KTC Scraper - Scrapes KeepTradeCut.com for dynasty player values
Based on method from github.com/ees4/KeepTradeCut-Scraper
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import sys

URL = "https://keeptradecut.com/dynasty-rankings?page={0}&filters=QB|WR|RB|TE|RDP&format={1}"

def scrape_ktc(max_pages=15):
    """
    Scrapes KTC for all player values.
    format=0 is Superflex, format=1 is 1QB
    """
    all_elements = []
    players = []
    
    # Superflex = format 0
    print("Scraping KTC Superflex rankings...", flush=True)
    
    for page_num in range(max_pages):
        print(f"  Page {page_num+1}...", flush=True)
        sys.stdout.flush()
        
        try:
            page = requests.get(URL.format(page_num, 0), timeout=10)
            if page.status_code != 200:
                print(f"  Error: status {page.status_code}")
                break
        except Exception as e:
            print(f"  Error: {e}")
            break
            
        soup = BeautifulSoup(page.content, "html.parser")
        player_elements = soup.find_all(class_="onePlayer")
        
        if not player_elements:
            print(f"  No more players found on page {page_num+1}")
            break
            
        for player_element in player_elements:
            all_elements.append(player_element)
        
        # Rate limit
        time.sleep(0.5)
    
    print(f"Found {len(all_elements)} players. Parsing...", flush=True)
    
    # Parse players
    for player_element in all_elements:
        try:
            player_name_element = player_element.find(class_="player-name")
            player_position_element = player_element.find(class_="position")
            player_value_element = player_element.find(class_="value")
            player_age_element = player_element.find(class_="position hidden-xs")
            
            if not all([player_name_element, player_position_element, player_value_element]):
                continue
            
            player_name = player_name_element.get_text(strip=True)
            player_position_rank = player_position_element.get_text(strip=True)
            player_value = player_value_element.get_text(strip=True)
            player_value = int(player_value)
            
            # Extract position (first 2 chars)
            player_position = player_position_rank[:2]
            
            # Handle team suffix (like "ATL", "RFA", "FA")
            team_suffix = ""
            if player_name.endswith('RFA'):
                team_suffix = 'RFA'
                player_name = player_name[:-3].strip()
            elif len(player_name) > 4 and player_name.endswith(' FA'):
                team_suffix = 'FA'
                player_name = player_name[:-3].strip()
            elif len(player_name) > 3:
                # Check if last 3 chars are uppercase (team abbreviation)
                potential_suffix = player_name[-3:]
                if potential_suffix.isupper() and potential_suffix not in ['QB', 'RB', 'WR', 'TE', 'PK', 'PIK', 'DST', 'KIK']:
                    team_suffix = potential_suffix
                    player_name = player_name[:-3].strip()
            
            player_team = team_suffix
            
            # Check if it's a pick
            is_pick = player_position == "PI"
            
            # Clean up pick names
            if is_pick:
                # Picks come as "2026 Early 1st FA" or similar
                if player_name.endswith('FA'):
                    player_name = player_name[:-2].strip()
            
            # Generate unique ID
            name_parts = player_name.split()
            if len(name_parts) >= 2:
                # First 3 of first name + first 3 of last name + index
                pid = (name_parts[0][:3] + name_parts[-1][:3]).lower()
            else:
                pid = player_name[:6].lower()
            pid = pid.replace("'", "").replace("-", "").replace(".", "")
            
            players.append({
                "id": pid,
                "name": player_name,
                "pos": "Pick" if is_pick else player_position,
                "value": player_value,
                "team": player_team
            })
            
        except Exception as e:
            print(f"Error parsing player: {e}")
            continue
    
    return players

def main():
    # Scrape KTC
    players = scrape_ktc(max_pages=15)
    
    # Add specific picks with more accurate values (from user input)
    # These override the scraped generic picks
    specific_picks = [
        {"id": "2026101", "name": "2026 1.01", "pos": "Pick", "value": 7456, "team": ""},
        {"id": "2026102", "name": "2026 1.02", "pos": "Pick", "value": 6168, "team": ""},
        {"id": "2026103", "name": "2026 1.03", "pos": "Pick", "value": 5737, "team": ""},
        {"id": "2026104", "name": "2026 1.04", "pos": "Pick", "value": 5473, "team": ""},
        {"id": "2026105", "name": "2026 1.05", "pos": "Pick", "value": 5157, "team": ""},
        {"id": "2026106", "name": "2026 1.06", "pos": "Pick", "value": 4999, "team": ""},
        {"id": "2026107", "name": "2026 1.07", "pos": "Pick", "value": 4595, "team": ""},
        {"id": "2026108", "name": "2026 1.08", "pos": "Pick", "value": 4431, "team": ""},
        {"id": "2026109", "name": "2026 1.09", "pos": "Pick", "value": 4280, "team": ""},
        {"id": "2026110", "name": "2026 1.10", "pos": "Pick", "value": 4076, "team": ""},
        {"id": "2026111", "name": "2026 1.11", "pos": "Pick", "value": 3904, "team": ""},
        {"id": "2026112", "name": "2026 1.12", "pos": "Pick", "value": 3807, "team": ""},
    ]
    
    # Remove any existing generic picks that we'll replace
    pick_names = [p['name'] for p in specific_picks]
    players = [p for p in players if p['name'] not in pick_names or p['pos'] != 'Pick']
    
    # Add specific picks at the beginning
    players = specific_picks + players
    
    print(f"Writing {len(players)} players to static/ktc_values.json...", flush=True)
    
    with open('/Users/danieltekippe/.openclaw/workspace/static/ktc_values.json', 'w') as f:
        json.dump(players, f, indent=2)
    
    print(f"Done! Scraped {len(players)} total players.")
    print(f"- {sum(1 for p in players if p['pos'] == 'Pick')} picks")
    print(f"- {sum(1 for p in players if p['pos'] == 'QB')} QBs")
    print(f"- {sum(1 for p in players if p['pos'] == 'RB')} RBs")
    print(f"- {sum(1 for p in players if p['pos'] == 'WR')} WRs")
    print(f"- {sum(1 for p in players if p['pos'] == 'TE')} TEs")

if __name__ == "__main__":
    main()
