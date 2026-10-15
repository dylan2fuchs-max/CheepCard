import os
import shutil
from datetime import datetime
import pandas as pd
import urllib.parse
import requests
import time
import re
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
    
    def _extract_oracle_text(self, card_data):
        """Safely extracts oracle text for single-faced, adventure, or multi-faced cards."""
        if card_data.get("oracle_text"):
            return card_data.get("oracle_text")
        
        if "card_faces" in card_data:
            faces_text = []
            for face in card_data["card_faces"]:
                name = face.get("name", "")
                text = face.get("oracle_text", "")
                if name and text:
                    faces_text.append(f"{name}\n{text}")
                elif text:
                    faces_text.append(text)
            return "\n---\n".join(faces_text)
            
        return ""

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

                r1_clean = r1.strip().lower()
                r2_clean = r2.strip().lower()
                
                r1_val = RANK_MAP.get(r1_clean, 0)
                r2_val = RANK_MAP.get(r2_clean, 0)
                
                r1_word = r1.capitalize() if r1.lower() != "none" else "None"
                r2_word = r2.capitalize() if r2.lower() != "none" else "None"

                card_type = get_row_val(row, "type", "card_type", default="")
                rarity = get_row_val(row, "rarity", default="Common")
                oracle_text = get_row_val(row, "text", "oracle_text", default="")

                clean_name = card_name.split("//")[0].strip()
                encoded_name = urllib.parse.quote(clean_name)
                img_url = f"https://api.scryfall.com/cards/named?exact={encoded_name}&format=image"

                card_data = {
                    "name": card_name,
                    "identity": get_row_val(row, "identity", default="{COLORLESS}"),
                    "mana_cost": mana_cost,
                    "price": price,
                    "ranking_1": r1,
                    "ranking_2": r2,
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
        if not os.path.exists(self.file_path):
            return None
        
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

    def update_all_card_prices(self) -> bool:
        try:
            self._create_timestamped_backup()
            
            print("Safely reading spreadsheet data for price updates...")
            df = pd.read_excel(self.file_path, engine="openpyxl")
            
            df.columns = (
                df.columns.astype(str)
                .str.replace('\xa0', ' ', regex=False)
                .str.strip()
                .str.lower()
                .str.replace(r'\s+', '_', regex=True)
            )
            
            name_col = next((c for c in df.columns if c.strip().lower() in ['name', 'card_name', 'title']), 'name')
            price_col = next((c for c in df.columns if c.strip().lower() in ['price', 'usd']), 'price')
            
            session = requests.Session()
            session.headers.update({
                "User-Agent": "CheepCardsApp/1.0",
                "Accept": "application/json"
            })
            exact_url = "https://api.scryfall.com/cards/named"
            search_url = "https://api.scryfall.com/cards/search"
            
            total_cards = len(df)
            print(f"Starting price-only update for {total_cards} cards...")
            updated_count = 0

            for index, (idx, row_data) in enumerate(df.iterrows(), 1):
                card_name = row_data.get(name_col)
                if pd.isna(card_name) or not str(card_name).strip():
                    continue
                
                clean_name = str(card_name).strip().split(" // ")[0].strip()
                # Normalize all quote variations so Scryfall accepts them
                clean_name = clean_name.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
                print(f"[{index}/{total_cards}] Updating price for: {clean_name}...", end="\r")
                
                time.sleep(0.13)
                
                # 1. Try exact match first
                resp = self._make_safe_request(session, exact_url, {"exact": clean_name})
                card_json = None
                
                if resp and resp.status_code == 200:
                    card_json = resp.json()
                else:
                    # 2. Fallback to Scryfall search API with quotes for cards with special punctuation/apostrophes
                    fallback_resp = self._make_safe_request(session, search_url, {"q": f'! "{clean_name}"'})
                    if fallback_resp and fallback_resp.status_code == 200:
                        search_data = fallback_resp.json()
                        if search_data.get("data"):
                            card_json = search_data["data"][0]
                
                if card_json:
                    live_price = card_json.get("prices", {}).get("usd")
                    if live_price is not None and price_col in df.columns:
                        try:
                            df.at[idx, price_col] = float(live_price)
                            updated_count += 1
                        except ValueError:
                            pass
                else:
                    print(f"\n⚠️ Could not fetch price for '{clean_name}'")

            df.to_excel(self.file_path, index=False, engine="openpyxl")
            print(f"\n--- [PRICE UPDATE SUCCESS] Successfully updated prices for {updated_count} cards! ---")
            
            self.load_cards()
            return True
            
        except Exception as err:
            print(f"Critical error during price update: {err}")
            return False

    def apply_class_judgement(self, df):
        """Class Judgement check assigning classes based on Oracle text keywords if empty."""
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

    def import_hobbit_and_reality_fracture_only(self) -> bool:
        """
        1. Creates a timestamped backup copy.
        2. Handles robust multi-page Scryfall pagination for new sets 
           ('The Hobbit', 'Reality Fracture', and precons).
        3. Assigns today's date and applies class judgement. Skips global price updates.
        """
        try:
            self._create_timestamped_backup()
            print("Safely reading spreadsheet data...")
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

            today_str = datetime.now().strftime("%Y-%m-%d")
            existing_names = {str(n).strip().lower() for n in df[name_col].dropna().tolist()}
            
            sets_to_fetch = ["set:hob", "set:fra", "set:frc"]
            new_cards_buffer = []
            
            print("\n--- STEP 1: IMPORTING THE HOBBIT & REALITY FRACTURE SETS ---")
            for query_set in sets_to_fetch:
                print(f"Fetching cards from Scryfall for {query_set}...")
                url = f"https://api.scryfall.com/cards/search?q={query_set}"
                
                while url:
                    res = requests.get(url, headers={"User-Agent": "CheepCardsApp/1.0", "Accept": "application/json"})
                    if res.status_code != 200:
                        print(f"⚠️ Error fetching {query_set}: Status {res.status_code}")
                        break
                    
                    data = res.json()
                    for card in data.get("data", []):
                        full_name = card.get("name", "")
                        clean_name = full_name.split(" // ")[0].strip()
                        
                        if clean_name.lower() in existing_names:
                            continue
                        
                        live_price = card.get("prices", {}).get("usd")
                        new_row = {
                            name_col: full_name,
                            "Identity": "".join([f"{{{c}}}" for c in card.get("color_identity", [])]) or "{COLORLESS}",
                            mana_col: card.get("mana_cost", "{0}"),
                            price_col: float(live_price) if live_price else 0.0,
                            type_col: card.get("type_line", ""),
                            rarity_col: card.get("rarity", "common").capitalize(),
                            text_col: self._extract_oracle_text(card),
                            set_col: card.get("set_name", ""),
                            date_col: today_str,
                            "Ranking 1": "none",
                            "Ranking 2": "none"
                        }
                        new_cards_buffer.append(new_row)
                        existing_names.add(clean_name.lower())
                        print(f"➕ Bringing in new card: {full_name}")
                        
                    if data.get("has_more"):
                        url = data.get("next_page")
                        time.sleep(0.1)
                    else:
                        break

            if new_cards_buffer:
                new_df = pd.DataFrame(new_cards_buffer)
                df = pd.concat([df, new_df], ignore_index=True)
                print(f"✅ Successfully imported {len(new_cards_buffer)} new cards!")
            else:
                print("ℹ No new cards found to import.")

            df = self.apply_class_judgement(df)
            df.to_excel(self.file_path, index=False, engine="openpyxl")
            print(f"\n--- [SUCCESS] Set import and local sync complete! ---")
            
            self.load_cards()
            return True
            
        except Exception as e:
            print(f"Critical error during set import: {e}")
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
                clean_name = clean_name.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
                print(f"[{index}/{total_cards}] Updating price for: {clean_name}...", end="\r")
                
                time.sleep(0.13)
                
                query_param = f'! "{clean_name}" legal:commander'
                resp = self._make_safe_request(session, search_url, {"q": query_param})
                
                card_json = None
                if resp and resp.status_code == 200:
                    search_data = resp.json()
                    cards_found = search_data.get("data", [])
                    if cards_found:
                        card_json = cards_found[0]
                
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
        Full powerhouse workflow:
        1. Timestamped backup
        2 & 3. Precise match check -> update price/set/date if found, add card if not found
        4. Commander legality sweep & removal
        5. Class Judgement
        """
        try:
            self._create_timestamped_backup()
            
            print("Safely reading spreadsheet data for full sync...")
            df = pd.read_excel(self.file_path, engine="openpyxl")
            
            df.columns = (
                df.columns.astype(str)
                .str.replace('\xa0', ' ', regex=False)
                .str.strip()
                .str.lower()
                .str.replace(r'\s+', '_', regex=True)
            )

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
                
                clean_name = str(card_name).strip().split(" // ")[0].strip()
                clean_name = clean_name.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
                print(f"[{index}/{total_cards}] Updating price for: {clean_name}...", end="\r")
                
                url = "https://api.scryfall.com/cards/named"
                params = {"exact": clean_name}
                
                try:
                    time.sleep(0.13)
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
                        oracle_text = self._extract_oracle_text(data)
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

                            if oracle_text:
                                df.at[idx, text_col] = oracle_text
                            
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
    manager.update_all_card_prices()