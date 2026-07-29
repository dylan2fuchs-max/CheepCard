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

    def clean_identity_search(self, user_input: str) -> str:
        """Converts a simple letter like 'g' into the format '{G}' used in Excel."""
        clean_input = user_input.strip().upper()
    
        # If they just typed 'G', wrap it in curly braces
        if len(clean_input) == 1 and clean_input in "WUBRG":
            return f"{{{clean_input}}}"
        
        return clean_input

    def find_cards_by_value(self, column_name: str, target_value) -> list:
        """
        Searches the Excel file by loading the sheet and scanning matching rows.
        Automatically checks both Class 1 and Class 2 if a 'class' search is requested.
        """
        matched_cards = []
        
        # 1. Read the full spreadsheet safely
        df = pd.read_excel(self.file_path, engine="openpyxl")
        
        # 2. Clean column headers to prevent spacing bugs
        df.columns = df.columns.str.strip()
        
        # 3. Check if we need a dual-class search
        clean_col = column_name.strip().lower()
        clean_val = str(target_value).strip().lower()
        
        if clean_col in ["class", "class 1", "class 2"]:
            match_condition_1 = df["Class 1"].astype(str).str.strip().str.lower() == clean_val
            match_condition_2 = df["Class 2"].astype(str).str.strip().str.lower() == clean_val
            matches = df[match_condition_1 | match_condition_2]
        elif isinstance(target_value, (int, float)):
            matches = df[df[column_name] >= target_value]
        else:
            matches = df[df[column_name].astype(str).str.strip().str.lower() == clean_val]
            
        # 4. Stream your custom row matches into Card objects
        for idx, row in matches.iterrows():
            excel_row_num = int(idx) + 2
            
            card = Card(
                name=row.get("Name"),
                identity=row.get("Idenity"),      
                mana_cost=row.get("Mana Cost"),
                price=row.get("Price"),
                
                ranking_1=row.get("Ranking 1"),     
                ranking_2=row.get("Ranking 2"),     
                
                card_class_1=row.get("Class 1"),    
                card_class_2=row.get("Class 2"),    
                
                rarity=row.get("Rarity")
            )
            card.excel_row_num = excel_row_num
            matched_cards.append(card)
            
        return matched_cards

    def edit_card_value(self, excel_row_num: int, column_letter: str, new_value) -> bool:
        """Edits a specific single cell using its exact row number."""
        try:
            wb = openpyxl.load_workbook(self.filename)
            sheet = wb.active
            sheet[f"{column_letter}{excel_row_num}"].value = new_value
            wb.save(self.filename)
            return True
        except Exception as e:
            print(f"Error saving to Excel: {e}")
            return False

    def sync_sheet_with_api(self) -> bool:
        """
        Reads the spreadsheet, fetches live set names and USD prices 
        from the Scryfall API based on card names, and updates columns B, E, and K.
        Handles double-faced split cards and skips rows that are already updated.
        """
        import requests
        import time
        from datetime import datetime

        try:
            wb = openpyxl.load_workbook(self.filename)
            sheet = wb.active
            
            # Layout Mapping
            SET_COL = "B"        # Set Name Column
            PRICE_COL = "E"      # Price Column
            TIMESTAMP_COL = "K"  # Timestamp Column
            
            # Write a header for the timestamp column if it doesn't exist
            if sheet[f"{TIMESTAMP_COL}1"].value is None:
                sheet[f"{TIMESTAMP_COL}1"].value = "Last Updated"
            
            headers = {
                "User-Agent": "CheepCardApp/1.0 (Contact: local_dev)",
                "Accept": "application/json"
            }
            
            print("Starting live API synchronization with Scryfall...")

            for row in range(2, sheet.max_row + 1):
                raw_card_name = sheet[f"A{row}"].value
                existing_timestamp = sheet[f"{TIMESTAMP_COL}{row}"].value
                
                # OPTIMIZATION: Skip rows that already successfully updated on your last run
                if existing_timestamp is not None:
                    continue
                
                if not raw_card_name:
                    continue
                
                # FIX: Extract just the front face name for double-faced/split cards
                raw_string = str(raw_card_name).strip()
                if " // " in raw_string:
                    clean_name = raw_string.split(" // ")[0].strip()
                else:
                    clean_name = raw_string
                
                url = "https://scryfall.com"
                params = {"exact": clean_name}
                
                try:
                    response = requests.get(url, headers=headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        live_set_name = data.get("set_name")
                        live_price = data.get("prices", {}).get("usd")
                        
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        if live_set_name:
                            sheet[f"{SET_COL}{row}"].value = live_set_name
                            
                        if live_price:
                            sheet[f"{PRICE_COL}{row}"].value = float(live_price)
                            
                        sheet[f"{TIMESTAMP_COL}{row}"].value = current_time
                            
                        print(f"Row {row}: Fixed & Updated '{clean_name}' -> Set: {live_set_name}, Price: ${live_price}")
                    else:
                        try:
                            err_details = response.json().get("details", "No detailed error message.")
                        except:
                            err_details = response.text
                        print(f"Row {row}: Failed for '{clean_name}' | Status {response.status_code} | Details: {err_details}")
                        
                except Exception as api_err:
                    print(f"Row {row}: Network connection error for '{clean_name}': {api_err}")
                
                time.sleep(0.1)

            wb.save(self.filename)
            print("Spreadsheet successfully cleaned and fully updated!")
            return True
            
        except Exception as e:
            print(f"Error executing API update: {e}")
            return False

