from Card_Filter import Card
from pathlib import Path
import pandas as pd
import openpyxl

# Assuming Card is imported from your models file:
# from models import Card

class ExcelManager:
    def __init__(self, filename: str = "Magic Card Data Base Current View.xlsx"):
        self.filename = filename
        self.file_path = Path.cwd() / filename
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Could not find spreadsheet at: {self.file_path}")

    def clean_identity_search(user_input: str) -> str:
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
            # Match if the target value is found in EITHER Class 1 OR Class 2
            match_condition_1 = df["Class 1"].astype(str).str.strip().str.lower() == clean_val
            match_condition_2 = df["Class 2"].astype(str).str.strip().str.lower() == clean_val
            matches = df[match_condition_1 | match_condition_2]
        elif isinstance(target_value, (int, float)):
            # Handle numeric columns normally (like Price or Ranking numbers)
            matches = df[df[column_name] >= target_value]
        else:
            # Handle standard single text columns (like Rarity or Idenity)
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
        """
        Edits a specific single cell using its exact row number.
        This updates the spreadsheet without reading or writing any other data.
        """
        try:
            wb = openpyxl.load_workbook(self.filename)
            sheet = wb.active
            
            # Change only the target cell
            sheet[f"{column_letter}{excel_row_num}"].value = new_value
            
            wb.save(self.filename)
            return True
        except Exception as e:
            print(f"Error saving to Excel: {e}")
            return False
