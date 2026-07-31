from Card_Filter import Card
from pathlib import Path
import pandas as pd
import openpyxl

class ExcelManager:
    def __init__(self, filename: str = "Magic Card Data Base Current View.xlsx"):
        self.filename = filename
        self.file_path = Path.cwd() / filename
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Could not find spreadsheet at: {self.file_path}")

    def find_cards_by_value(self, column_name: str, target_value) -> list:
        matched_cards = []
        df = pd.read_excel(self.file_path, engine="openpyxl")
        df.columns = df.columns.str.strip()
        matches = df[df[column_name].astype(str).str.strip().str.lower() == str(target_value).strip().lower()]
            
        for idx, row in matches.iterrows():
            card = Card(
                name=row.get("Name"), identity=row.get("Idenity"),      
                mana_cost=row.get("Mana Cost"), price=row.get("Price"),
                ranking_1=row.get("Ranking 1"), ranking_2=row.get("Ranking 2"),     
                card_class_1=row.get("Class 1"), card_class_2=row.get("Class 2"),    
                rarity=row.get("Rarity")
            )
            card.excel_row_num = int(idx) + 2
            matched_cards.append(card)
        return matched_cards

    def sync_sheet_with_api(self) -> bool:
        """Fetches live set names and USD prices via official Scryfall Fuzzy API."""
        import requests
        import time
        from datetime import datetime
        try:
            print("Safely reading spreadsheet data...")
            df = pd.read_excel(self.file_path, engine="openpyxl")
            df.columns = df.columns.str.strip()
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            print("Starting live database synchronization...")
            updated_any = False

            for idx, row_data in df.iterrows():
                excel_row = int(idx) + 2
                raw_card_name = row_data.get("Name")
                existing_set = row_data.get("Set Name") if "Set Name" in df.columns else row_data.get("Set")
                existing_price = row_data.get("Price")
                
                has_valid_set = pd.notna(existing_set) and str(existing_set).strip() != ""
                has_valid_price = pd.notna(existing_price) and existing_price != 0 and existing_price != 0.0
                
                # If BOTH the price and set are already filled, skip this row instantly
                if has_valid_set and has_valid_price:
                    continue
                
                if pd.isna(raw_card_name) or not str(raw_card_name).strip():
                    continue
                
                # --- FIXED STRING HANDLING ---
                raw_string = str(raw_card_name).strip()
                if " // " in raw_string:
                    clean_name = raw_string.split(" // ")[0].strip()
                else:
                    clean_name = raw_string
                
                url = "https://api.scryfall.com/cards/named"
                params = {"fuzzy": clean_name}
                try:
                    time.sleep(0.25) 
                    response = requests.get(url, headers=headers, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        live_set_name = data.get("set_name")
                        live_price = data.get("prices", {}).get("usd")
                        
                        if live_set_name: 
                            df.at[idx, "Set Name" if "Set Name" in df.columns else "Set"] = str(live_set_name)
                        if live_price: 
                            df.at[idx, "Price"] = float(live_price)
                            print(f"Row {excel_row}: Successfully Recovered '{clean_name}' -> Set: {live_set_name}, Price: ${live_price}")
                        else:
                            print(f"Row {excel_row}: Found '{clean_name}', but no USD price available.")
                        updated_any = True
                    else:
                        print(f"Row {excel_row}: API returned status {response.status_code} for '{clean_name}'")
                except Exception as row_err:
                    print(f"Error on row {excel_row} for '{clean_name}': {row_err}")
                
                if updated_any and excel_row % 50 == 0:
                    df.to_excel(self.file_path, index=False)

            if updated_any:
                df.to_excel(self.file_path, index=False)
                print("\n--- [SUCCESS] DATABASE SYNCHRONIZATION COMPLETED ---")
            return True
        except Exception as main_err:
            print(f"Critical execution error: {main_err}")
            return False

