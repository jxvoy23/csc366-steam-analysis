import requests
import time
import json
import os
from dotenv import load_dotenv

# 1. Setup and Authentication
load_dotenv()
steam_key = os.getenv('STEAM_API_KEY')

if not steam_key:
    raise ValueError("API Key not found. Please check your .env file.")

os.makedirs('data', exist_ok=True)
master_dataset = []
file_path = 'data/raw_steam_snapshot.json'

# 2. Source a high-quality list of AppIDs (Top 1,000 games via SteamSpy)
print("Fetching master list of popular games from SteamSpy...")
spy_all_url = "https://steamspy.com/api.php?request=all&page=0"
spy_all_res = requests.get(spy_all_url).json()

target_appids = list(spy_all_res.keys())[:1000]
print(f"Collected {len(target_appids)} active AppIDs. Starting API extraction...\n")

# 3. Main Multi-Endpoint Scraping Loop
count = 0
for appid in target_appids:
    store_url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    reviews_url = f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all"
    players_url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}&key={steam_key}"
    spy_url = f"https://steamspy.com/api.php?request=appdetails&appid={appid}"
    
    game_record = {'steam_appid': appid}
    
    try:
        # Fetch Steam Storefront (Most heavily rate-limited endpoint)
        store_res = requests.get(store_url)
        
        # If rate-limited, trigger the 5-minute compliance cooldown
        if store_res.status_code == 429:
            print(f"\n[!] Rate limit hit at {count} games! Sleeping for 5 minutes...")
            time.sleep(305)  
            store_res = requests.get(store_url)
            
        if store_res.status_code == 200:
            store_json = store_res.json()
            if store_json and str(appid) in store_json and store_json[str(appid)].get('success'):
                game_record['store_data'] = store_json[str(appid)]['data']
        
        # Fetch Reviews
        reviews_res = requests.get(reviews_url)
        if reviews_res.status_code == 200:
            game_record['review_data'] = reviews_res.json().get('query_summary', {})
            
        # Fetch Current Players
        players_res = requests.get(players_url)
        if players_res.status_code == 200:
            game_record['current_players'] = players_res.json().get('response', {}).get('player_count', 0)
            
        # Fetch SteamSpy Data
        spy_res = requests.get(spy_url)
        if spy_res.status_code == 200:
            game_record['steamspy_data'] = spy_res.json()
            
        master_dataset.append(game_record)
        count += 1
        
        # 4. Checkpointing: Save locally every 50 games
        if count % 50 == 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(master_dataset, f, indent=4)
            print(f"Checkpoint saved: {count}/{len(target_appids)} games processed...")
            
    except Exception as e:
        print(f"Error scraping AppID {appid}: {e}")
        
    # Standard spacing to slow the rate of requests
    time.sleep(1.5)

# 5. Final Save
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(master_dataset, f, indent=4)
print(f"\nComplete! Saved {len(master_dataset)} merged records to {file_path}")