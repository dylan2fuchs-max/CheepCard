import os
import shutil
from datetime import datetime
import pandas as pd
import urllib.parse
import requests
import time
import re
from collections import Counter
from Card_Filter import Card

class ExcelManager:
    def __init__(self, file_path="Magic Card Data Base Current View.xlsx"):
        if not os.path.isabs(file_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.file_path = os.path.join(base_dir, file_path)
        else:
            self.file_path = file_path
            
        self.card_pool = []
        self.df = None
        self.load_cards()

    def _make_safe_request(self, session, url, params=None, timeout=5):
        try:
            response = session.get(url, params=params, timeout=timeout)
            return response
        except Exception as e:
            print(f"Request error for {url}: {e}")
            return None

    def load_cards(self):
        self.card_pool = []
        print(f"\n📂 Loading database from: {self.file_path}...")
        
        if not os.path.exists(self.file_path):
            print(f"❌ File not found at path: {self.file_path}")
            return self.card_pool

        try:
            df = pd.read_excel(
                self.file_path, 
                engine="openpyxl",
                engine_kwargs={"read_only": True, "data_only": True}
            )
            
            df.columns = (
                df.columns.astype(str)
                .str.replace('\xa0', ' ', regex=False)
                .str.strip()
                .str.lower()
                .str.replace(r'\s+', '_', regex=True)
            )
            self.df = df

            RANK_MAP = {"optimized": 5, "fast": 4, "average": 3, "passive": 2, "low": 1}

            def get_row_val(row_data, *col_names, default="none"):
                for col in col_names:
                    if col in row_data and pd.notna(row_data[col]):
                        val = str(row_data[col]).strip()
                        if val and val.lower() not in ("nan", "none"):
                            return val
                return default

            for idx, row in df.iterrows():
                card_name = get_row_val(row, "name", "card_name", "title")
                if card_name == "none" or not card_name:
                    continue

                mana_cost = get_row_val(row, "mana_cost", "mana", default="{0}")
                
                raw_price = get_row_val(row, "price", "usd", default="0.00")
                try:
                    price = float(str(raw_price).replace('$', '').replace(',', '').strip())
                except ValueError:
                    price = 0.00

                c1 = get_row_val(row, "class_1", "class1", "card_class_1", "class", default="none")
                c2 = get_row_val(row, "class_2", "class2", "card_class_2", default="none")
                
                r1 = get_row_val(row, "ranking_1", "ranking1", "rank_1", "rank", default="none")
                r2 = get_row_val(row, "ranking_2", "ranking2", "rank_2", default="none")

                # Properly resolve words and values here
                r1_clean = r1.strip().lower()
                r2_clean = r2.strip().lower()
                
                r1_val = RANK_MAP.get(r1_clean, 0)
                r2_val = RANK_MAP.get(r2_clean, 0)
                
                r1_word = r1.capitalize() if r1.lower() != "none" else "None"
                r2_word = r2.capitalize() if r2.lower() != "none" else "None"

                card_type = get_row_val(row, "type", "card_type", default="")
                rarity = get_row_val(row, "rarity", default="Common")
                oracle_text = get_row_val(row, "text", "oracle_text", default="")
                set_name = get_row_val(row, "set", "set_name", default="")

                clean_name = card_name.split("//")[0].strip()
                encoded_name = urllib.parse.quote(clean_name)
                img_url = f"https://api.scryfall.com/cards/named?exact={encoded_name}&format=image"

                card_data = {
                    "name": card_name,
                    "identity": get_row_val(row, "identity", default="{COLORLESS}"),
                    "mana_cost": mana_cost,
                    "price": price,
                    "ranking_1": r1,  # <--- Pass raw r1 string so Card class handles validation
                    "ranking_2": r2,  # <--- Pass raw r2 string
                    "card_class_1": c1,
                    "card_class_2": c2,
                    "rarity": rarity,
                    "image_url": img_url,
                    "oracle_text": oracle_text,
                    "excel_row_num": idx + 2
                }
                
                self.card_pool.append(Card(**card_data))
                
            print(f"✅ Successfully loaded {len(self.card_pool)} cards into pool.\n")
            return self.card_pool
            
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}\n")
            return []

    def find_cards_by_value(self, column_name, value):
        if self.df is not None and column_name in self.df.columns:
            result_df = self.df[self.df[column_name].astype(str).str.contains(str(value), case=False, na=False)]
            return result_df.to_dict(orient='records')
        return []

    def _create_timestamped_backup(self):
        """Step 1: Creates a timestamped backup copy of the Excel sheet as a fall-safe fallback."""
        if not os.path.exists(self.file_path):
            return None
        
        # Create a dedicated backups directory if it doesn't already exist
        base_dir = os.path.dirname(self.file_path) or "."
        backup_dir = os.path.join(base_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        filename = os.path.basename(self.file_path)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"{name}_backup_{timestamp}{ext}"
        
        backup_path = os.path.join(backup_dir, backup_filename)
        shutil.copy2(self.file_path, backup_path)
        print(f"🛡️ Backup created successfully: backups/{backup_filename}")
        return backup_path

    def apply_class_judgement(self, df):
        """Step 5: Class Judgement check assigning classes based on Oracle text keywords if empty."""
        text_col = next((c for c in df.columns if c.strip().lower() in ['text', 'oracle_text']), None)
        class1_col = next((c for c in df.columns if c.strip().lower() in ['class_1', 'class1']), None)
        
        if not text_col or not class1_col:
            return df
            
        updated_classes = 0
        for idx, row in df.iterrows():
            current_class = str(row.get(class1_col, '')).strip()
            if not current_class or current_class.lower() in ['nan', 'none', '']:
                oracle_txt = str(row.get(text_col, '')).lower()
                
                assigned_class = ""
                if 'draw' in oracle_txt:
                    assigned_class = "Draw"
                elif any(keyword in oracle_txt for keyword in ['exile', 'destroy', 'return', 'fight', 'deal']):
                    assigned_class = "Removal"
                elif 'basic land' in oracle_txt or 'put that card' in oracle_txt:
                    assigned_class = "Ramp"
                    
                if assigned_class:
                    df.at[idx, class1_col] = assigned_class
                    updated_classes += 1
                    
        if updated_classes > 0:
            print(f"🏷️ Class Judgement applied to {updated_classes} cards.")
        return df

    def analyze_class_oracle_text(self, target_class="Removal", top_n=40):
        """
        Scans all cards in a specific class (e.g., 'Removal') and extracts 
        the most common words and two-word phrases (bigrams) from their Oracle text.
        """
        try:
            print(f"Analyzing Oracle text patterns for class: {target_class}...")
            df = pd.read_excel(self.file_path, engine="openpyxl")
            
            name_col = next((c for c in df.columns if c.strip().lower() in ['name', 'card_name', 'title']), 'Name')
            class1_col = next((c for c in df.columns if c.strip().lower() in ['class_1', 'class1']), 'Class 1')
            text_col = next((c for c in df.columns if c.strip().lower() in ['text', 'oracle_text']), 'Text')
            
            class_df = df[df[class1_col].astype(str).str.strip().str.lower() == target_class.lower()]
            print(f"Found {len(class_df)} cards in class '{target_class}' to analyze.")
            
            all_text = []
            session = requests.Session()
            session.headers.update({"User-Agent": "CheepCardsApp/1.0", "Accept": "application/json"})
            search_url = "https://api.scryfall.com/cards/search"
            
            for idx, row in class_df.iterrows():
                oracle_text = ""
                if text_col and text_col in df.columns:
                    oracle_text = str(row.get(text_col, '')).lower()
                
                if not oracle_text or oracle_text == 'nan':
                    card_name = str(row.get(name_col, '')).strip().split(" // ")[0]
                    if card_name:
                        time.sleep(0.04)
                        resp = self._make_safe_request(session, search_url, {"q": f'! "{card_name}"'})
                        if resp and resp.status_code == 200:
                            data = resp.json()
                            if data.get("data"):
                                oracle_text = data["data"][0].get("oracle_text", "").lower()
                
                if oracle_text:
                    all_text.append(oracle_text)
            
            full_corpus = " ".join(all_text)
            cleaned_corpus = re.sub(r'[^a-z\s]', ' ', full_corpus)
            words = cleaned_corpus.split()
            
            stopwords = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                'with', 'by', 'as', 'of', 'it', 'its', 'is', 'are', 'was', 'were', 
                'this', 'that', 'these', 'those', 'from', 'you', 'your', 'yours', 
                'he', 'him', 'his', 'she', 'her', 'they', 'them', 'their', 'cards', 'card',
                'each', 'controller', 'control', 'mana', 'owner', 'owners'
            }
            
            filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
            
            # Count words and bigrams
            word_counts = Counter(filtered_words)
            bigrams = [f"{filtered_words[i]} {filtered_words[i+1]}" for i in range(len(filtered_words)-1)]
            bigram_counts = Counter(bigrams)
            
            print(f"\n================ TOP {top_n} SINGLE WORDS ================")
            for word, count in word_counts.most_common(top_n):
                print(f"{word}: {count:,}")
                
            print(f"\n================ TOP {top_n} TWO-WORD PHRASES ================")
            for bigram, count in bigram_counts.most_common(top_n):
                print(f"{bigram}: {count:,}")
                
            return True
            
        except Exception as e:
            print(f"Error during text analysis: {e}")
            return False

    def filter_removal_strict_only(self):
        """
        Final precision cleanup with corrected tag query syntax:
        1. Local Text Whitelist -> Stays 'Removal'
        2. Scryfall Removal Function -> Stays 'Removal'
        3. Scryfall Counterspell Function -> Stays 'Removal'
        4. Graveyard Hate / Sweeps -> Stays 'Removal' (Checked before Board Wipe)
        5. Scryfall Impulse Draw Tag -> Changes to 'Draw1'
        6. Scryfall Red Draw Search -> Changes to 'Draw1'
        7. Scryfall Board Wipe Check -> Changes to 'Board Wipe'
        8. Network Failsafe / Drops to 'N/A'
        """
        try:
            self._create_timestamped_backup()
            print("Running final ordered pipeline with syntax fix...")
            df = pd.read_excel(self.file_path, engine="openpyxl")
            
            name_col = next((c for c in df.columns if c.strip().lower() in ['name', 'card_name', 'title']), 'Name')
            class1_col = next((c for c in df.columns if c.strip().lower() in ['class_1', 'class1']), 'Class 1')
            rank_col = next((c for c in df.columns if c.strip().lower() in ['rank', 'card_rank', 'ranking']), None)
            text_col = next((c for c in df.columns if c.strip().lower() in ['text', 'oracle_text']), 'Text')
            
            session = requests.Session()
            session.headers.update({
                "User-Agent": "CheepCardsApp/1.0",
                "Accept": "application/json"
            })
            search_url = "https://api.scryfall.com/cards/search"
            
            skipped_ranked = 0
            kept_via_text = 0
            kept_via_scryfall_api = 0
            moved_to_draw1 = 0
            moved_to_boardwipe = 0
            updated_to_na = 0
            
            approved_patterns = [
                r"target\b.*\bcreature",
                r"deals\b.*\bdamage",
                r"destroy\b.*\btarget",
                r"damage\b.*\btarget",
                r"sacrifice\b.*\bcreature",
                r"exile\b.*\btarget",
                r"counter\b.*\btarget",
                r"target\b.*\bartifact",
                r"return\b.*\btarget",
                r"enchant\b.*\b(creature|permanent)",
                r"exile\b.*\b(top|cards)\b.*\bplay",
                r"exile\b.*\bgraveyards"
            ]
            
            for idx, row in df.iterrows():
                c1 = str(row.get(class1_col, '')).strip()
                if c1.lower() != 'removal':
                    continue
                    
                if rank_col and rank_col in df.columns:
                    rank_val = row.get(rank_col)
                    if pd.notna(rank_val) and str(rank_val).strip() != '':
                        skipped_ranked += 1
                        continue
                        
                card_name = row.get(name_col)
                if pd.isna(card_name) or not str(card_name).strip():
                    continue
                    
                clean_name = str(card_name).strip().split(" // ")[0].strip()
                print(f"Processing: {clean_name}...", end="\r")
                
                time.sleep(0.15)
                
                oracle_text = ""
                if text_col and text_col in df.columns:
                    oracle_text = str(row.get(text_col, '')).lower()
                
                if not oracle_text or oracle_text == 'nan':
                    resp = self._make_safe_request(session, search_url, {"q": f'! "{clean_name}"'})
                    if resp and resp.status_code == 200:
                        data = resp.json()
                        cards_found = data.get("data", [])
                        if cards_found:
                            oracle_text = cards_found[0].get("oracle_text", "").lower()
                
                # Step 1: Local text whitelist match
                matched_text = any(re.search(pattern, oracle_text) for pattern in approved_patterns)
                
                if matched_text:
                    kept_via_text += 1
                else:
                    # Step 2: Scryfall removal function check -> Stays Removal
                    time.sleep(0.15)
                    rem_resp = self._make_safe_request(session, search_url, {"q": f'!"{clean_name}" function:removal'})
                    if rem_resp and rem_resp.status_code == 200 and len(rem_resp.json().get("data", [])) > 0:
                        kept_via_scryfall_api += 1
                        continue
                    
                    # Step 3: Scryfall counterspell function check -> Stays Removal
                    time.sleep(0.15)
                    cnt_resp = self._make_safe_request(session, search_url, {"q": f'!"{clean_name}" function:counterspell'})
                    if cnt_resp and cnt_resp.status_code == 200 and len(cnt_resp.json().get("data", [])) > 0:
                        kept_via_scryfall_api += 1
                        continue
                        
                    # Step 4: Scryfall Graveyard Hate check -> Stays Removal
                    time.sleep(0.15)
                    gy_resp = self._make_safe_request(session, search_url, {"q": f'!"{clean_name}" otag:sweeper-graveyard'})
                    if gy_resp and gy_resp.status_code == 200 and len(gy_resp.json().get("data", [])) > 0:
                        kept_via_scryfall_api += 1
                        continue
                        
                    # Step 5: Scryfall Impulse Draw tag check -> Draw1
                    time.sleep(0.15)
                    imp_resp = self._make_safe_request(session, search_url, {"q": f'!"{clean_name}" otag:impulsive-draw'})
                    if imp_resp and imp_resp.status_code == 200 and len(imp_resp.json().get("data", [])) > 0:
                        df.at[idx, class1_col] = "Draw1"
                        moved_to_draw1 += 1
                        print(f"\n[Impulse Draw -> Draw1] {clean_name}")
                        continue
                        
                    # Step 6: Scryfall General Draw check -> Draw1
                    time.sleep(0.15)
                    draw_resp = self._make_safe_request(session, search_url, {"q": f'!"{clean_name}" o:draw c:r'})
                    if draw_resp and draw_resp.status_code == 200 and len(draw_resp.json().get("data", [])) > 0:
                        df.at[idx, class1_col] = "Draw1"
                        moved_to_draw1 += 1
                        print(f"\n[Red Draw -> Draw1] {clean_name}")
                        continue
                        
                    # Step 7: Scryfall Board Wipe check -> Board Wipe (Fixed query syntax)
                    time.sleep(0.15)
                    bw_resp = self._make_safe_request(session, search_url, {"q": f'"{clean_name}" otag:boardwipe'})
                    if bw_resp and bw_resp.status_code == 200 and len(bw_resp.json().get("data", [])) > 0:
                        df.at[idx, class1_col] = "Board Wipe"
                        moved_to_boardwipe += 1
                        print(f"\n[Board Wipe -> Board Wipe] {clean_name}")
                        continue
                        
                    # Step 8 Failsafe
                    api_had_error = (rem_resp is None or cnt_resp is None or gy_resp is None or imp_resp is None or draw_resp is None or bw_resp is None)
                    if api_had_error:
                        kept_via_text += 1
                    else:
                        df.at[idx, class1_col] = "N/A"
                        updated_to_na += 1
                        print(f"\n[N/A] {clean_name} (Verified non-removal by all systems)")
                        
            df.to_excel(self.file_path, index=False, engine="openpyxl")
            print(f"\n--- [FILTER COMPLETE] Skipped: {skipped_ranked} | Kept Removal: {kept_via_text + kept_via_scryfall_api} | Draw1: {moved_to_draw1} | Board Wipes: {moved_to_boardwipe} | Changed to N/A: {updated_to_na} ---")
            self.load_cards()
            return True
            
        except Exception as e:
            print(f"Error during ordered pipeline filter: {e}")
            return False

    def update_and_sweep_sheet(self) -> bool:
        """
        Lightweight weekly maintenance: Updates prices and set names for existing cards only,
        and automatically sweeps out illegal cards or 404s (like Arena A- cards or playtests).
        Does NOT add any new cards to the spreadsheet.
        """
        try:
            self._create_timestamped_backup()
            
            print("Safely reading spreadsheet data for weekly maintenance...")
            df = pd.read_excel(self.file_path, engine="openpyxl")
            
            name_col = next((c for c in df.columns if c.strip().lower() in ['name', 'card_name', 'title']), 'Name')
            set_col = next((c for c in df.columns if c.strip().lower() in ['set name', 'set', 'set_name']), 'Set')
            price_col = next((c for c in df.columns if c.strip().lower() in ['price', 'usd']), 'Price')
            
            session = requests.Session()
            session.headers.update({
                "User-Agent": "CheepCardsApp/1.0",
                "Accept": "application/json"
            })
            search_url = "https://api.scryfall.com/cards/search"
            exact_url = "https://api.scryfall.com/cards/named"
            
            total_cards = len(df)
            print(f"Starting maintenance sweep and price update for {total_cards} cards...")
            rows_to_drop = []
            updated_count = 0

            for index, (idx, row_data) in enumerate(df.iterrows(), 1):
                card_name = row_data.get(name_col)
                if pd.isna(card_name) or not str(card_name).strip():
                    continue
                
                clean_name = str(card_name).strip().split(" // ")[0].strip()
                print(f"[{index}/{total_cards}] Checking: {clean_name}...", end="\r")
                
                time.sleep(0.08)
                
                query_param = f'! "{clean_name}" legal:commander'
                resp = self._make_safe_request(session, search_url, {"q": query_param})
                
                card_json = None
                if resp and resp.status_code == 200:
                    search_data = resp.json()
                    cards_found = search_data.get("data", [])
                    if cards_found:
                        card_json = cards_found[0]
                
                # Fallback: Exact match check for unindexed new cards, 
                # but explicitly block cards that are banned in Commander (e.g., Balance)
                if not card_json:
                    fallback_resp = self._make_safe_request(session, exact_url, {"exact": clean_name})
                    if fallback_resp and fallback_resp.status_code == 200:
                        temp_json = fallback_resp.json()
                        legalities = temp_json.get("legalities", {})
                        if legalities.get("commander") != "banned":
                            card_json = temp_json

                if card_json:
                    live_set_name = card_json.get("set_name", "")
                    live_price = card_json.get("prices", {}).get("usd")
                    
                    if live_set_name and set_col in df.columns:
                        df.at[idx, set_col] = str(live_set_name)
                    if live_price is not None and price_col in df.columns:
                        try:
                            df.at[idx, price_col] = float(live_price)
                        except ValueError:
                            pass
                    updated_count += 1
                else:
                    rows_to_drop.append(idx)
                    print(f"❌ Removing illegal/404 card: {clean_name}")

            if rows_to_drop:
                df = df.drop(rows_to_drop)

            df = self.apply_class_judgement(df)
            df.to_excel(self.file_path, index=False, engine="openpyxl")
            
            print(f"\n--- [MAINTENANCE SUCCESS] Updated {updated_count} cards, removed {len(rows_to_drop)} invalid/illegal cards ---")
            
            self.load_cards()
            return True
            
        except Exception as main_err:
            print(f"Critical execution error during maintenance: {main_err}")
            return False

    def sync_sheet_with_api(self, target_cards_to_check=None) -> bool:
        """
        Full powerhouse workflow (used when adding new sets):
        1. Timestamped backup
        2 & 3. Precise match check -> update price/set/date if found, add card if not found
        4. Commander legality sweep & removal
        5. Class Judgement
        6. Complete notification
        """
        try:
            self._create_timestamped_backup()
            
            print("Safely reading spreadsheet data for full sync...")
            df = pd.read_excel(self.file_path, engine="openpyxl")
            
            name_col = next((c for c in df.columns if c.strip().lower() in ['name', 'card_name', 'title']), 'Name')
            set_col = next((c for c in df.columns if c.strip().lower() in ['set name', 'set', 'set_name']), 'Set')
            price_col = next((c for c in df.columns if c.strip().lower() in ['price', 'usd']), 'Price')
            date_col = next((c for c in df.columns if c.strip().lower() in ['date', 'date added', 'date_added', 'added_date']), 'Date')
            mana_col = next((c for c in df.columns if c.strip().lower() in ['mana_cost', 'mana']), 'Mana Cost')
            type_col = next((c for c in df.columns if c.strip().lower() in ['type', 'card_type']), 'Type')
            rarity_col = next((c for c in df.columns if c.strip().lower() in ['rarity']), 'Rarity')
            text_col = next((c for c in df.columns if c.strip().lower() in ['text', 'oracle_text']), 'Text')
            
            if date_col not in df.columns:
                df['Date'] = ""
                date_col = 'Date'
            else:
                df[date_col] = df[date_col].astype(str).replace(['nan', 'None', 'NAT'], '')

            headers = {
                "User-Agent": "CheepCardsApp/1.0",
                "Accept": "application/json"
            }
            
            cards_to_process = df[name_col].dropna().tolist()
            if target_cards_to_check:
                cards_to_process = list(set(cards_to_process + target_cards_to_check))

            total_cards = len(cards_to_process)
            print(f"Starting live database synchronization for {total_cards} cards...")
            new_rows_buffer = []
            updated_count = 0
            today_str = datetime.now().strftime("%Y-%m-%d")

            for index, raw_card_name in enumerate(cards_to_process, 1):
                if not str(raw_card_name).strip():
                    continue
                
                clean_name = str(raw_card_name).strip().split(" // ")[0].strip()
                print(f"[{index}/{total_cards}] Checking: {clean_name}...", end="\r")
                
                url = "https://api.scryfall.com/cards/named"
                params = {"exact": clean_name}
                
                try:
                    time.sleep(0.08)
                    response = requests.get(url, headers=headers, params=params, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        legalities = data.get("legalities", {})
                        
                        if legalities.get("commander") != "legal":
                            continue
                            
                        live_set_name = data.get("set_name", "")
                        live_price = data.get("prices", {}).get("usd")
                        mana_cost = data.get("mana_cost", "{0}")
                        card_type = data.get("type_line", "")
                        rarity = data.get("rarity", "common").capitalize()
                        oracle_text = data.get("oracle_text", "")
                        color_identity = "".join([f"{{{c}}}" for c in data.get("color_identity", [])]) or "{COLORLESS}"

                        matching_rows = df[df[name_col].astype(str).str.strip().str.lower() == clean_name.lower()]
                        
                        if not matching_rows.empty:
                            idx = matching_rows.index[0]
                            if live_set_name:
                                df.at[idx, set_col] = str(live_set_name)
                            if live_price is not None:
                                try:
                                    df.at[idx, price_col] = float(live_price)
                                except ValueError:
                                    pass
                            
                            existing_date = str(df.at[idx, date_col]).strip()
                            if not existing_date or existing_date.lower() in ['nan', 'none', '']:
                                df.at[idx, date_col] = today_str
                                
                            updated_count += 1
                        else:
                            new_row = {
                                name_col: data.get("name", clean_name),
                                "Identity": color_identity,
                                mana_col: mana_cost,
                                price_col: float(live_price) if live_price else 0.0,
                                type_col: card_type,
                                rarity_col: rarity,
                                text_col: oracle_text,
                                set_col: live_set_name,
                                date_col: today_str,
                                "Ranking 1": "none",
                                "Ranking 2": "none"
                            }
                            new_rows_buffer.append(new_row)
                            print(f"➕ Adding new card with timestamp {today_str}: {clean_name}")

                    elif response.status_code == 404:
                        print(f"⚠️ Card '{clean_name}' not found precisely on Scryfall.")
                except Exception as api_err:
                    print(f"API error for '{clean_name}': {api_err}")

            if new_rows_buffer:
                new_df = pd.DataFrame(new_rows_buffer)
                df = pd.concat([df, new_df], ignore_index=True)

            print("🧹 Running Commander legality check sweep across all sheet cards...")
            rows_to_drop = []
            search_url = "https://api.scryfall.com/cards/search"
            
            for idx, row_data in df.iterrows():
                card_name = row_data.get(name_col)
                if pd.isna(card_name):
                    continue
                check_name = str(card_name).strip().split(" // ")[0].strip()
                try:
                    time.sleep(0.08)
                    query_param = f'! "{check_name}" legal:commander'
                    resp = requests.get(search_url, headers=headers, params={"q": query_param}, timeout=4)
                    
                    if resp.status_code == 200:
                        continue
                    elif resp.status_code == 404:
                        rows_to_drop.append(idx)
                        print(f"❌ Removing illegal or unverified card from sheet: {check_name}")
                except Exception as sweep_err:
                    print(f"Sweep error for {check_name}: {sweep_err}")

            if rows_to_drop:
                df = df.drop(rows_to_drop)

            df = self.apply_class_judgement(df)

            df.to_excel(self.file_path, index=False, engine="openpyxl")
            
            print("\n--- [SUCCESS] complete ---")
            
            self.load_cards()
            return True
            
        except Exception as main_err:
            print(f"Critical execution error during sync: {main_err}")
            return False
        
if __name__ == "__main__":
    manager = ExcelManager()
    # Use update_and_sweep_sheet() for weekly price & legality updates without adding cards
    # Use sync_sheet_with_api() when you want to scan for and append new cards
    manager.update_and_sweep_sheet()