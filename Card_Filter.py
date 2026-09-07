import pandas as pd

class Card:
    VALID_CLASSES = ["draw", "ramp", "removal", "boardwipe", "land", "none", "nan", ""]
    
    # 1. Added 'fat' and custom words to valid rankings list
    VALID_RANKINGS = ["optimized", "fast", "average", "medium", "passive", "low", "fat", "none", "nan", ""]
    
    # 2. Assign numeric weights for sorting (e.g. fat = 1 or passive rank)
    RANKING_VALUES = {
        "optimized": 5, 
        "fast": 4, 
        "average": 3, 
        "medium": 3,
        "passive": 2, 
        "low": 1, 
        "fat": 1,
        "none": 0, 
        "nan": 0,
        "": 0
    }

    def __init__(self, name: str = "Unknown Card", identity: str = "{COLORLESS}", mana_cost: str = "{0}", 
                 price: float = 0.00, ranking_1="none", ranking_2="none", 
                 card_class_1="none", card_class_2="none", rarity: str = "Common",
                 image_url: str = "", oracle_text: str = "", **kwargs):
        
        # 1. Validate Name
        self.name = str(name).strip() if name and not pd.isna(name) else "Unknown Card"
        
        # 2. Validate Identity formatting
        raw_id = str(identity).strip().upper() if identity and not pd.isna(identity) else "{COLORLESS}"
        if len(raw_id) == 1 and raw_id in "WUBRG":
            self.identity = f"{{{raw_id}}}"
        else:
            self.identity = raw_id
            
        self.mana_cost = str(mana_cost).strip() if mana_cost and not pd.isna(mana_cost) else "{0}"

        # 3. Validate Price
        try:
            clean_price = float(str(price).replace('$', '').strip())
            self.price = max(0.00, clean_price)
        except (ValueError, TypeError):
            self.price = 0.00
            
        # 4. Classes (Preserves values while converting invalid/empty to 'none')
        c1 = str(card_class_1).strip().lower() if not pd.isna(card_class_1) else "none"
        c2 = str(card_class_2).strip().lower() if not pd.isna(card_class_2) else "none"
        
        self.card_class_1 = c1 if c1 and c1 != "nan" else "none"
        self.card_class_2 = c2 if c2 and c2 != "nan" else "none"
        
        # UI Template Aliases
        self.class_1 = self.card_class_1  
        self.class_2 = self.card_class_2  

        # 5. Rankings
        r1 = str(ranking_1).strip().lower() if not pd.isna(ranking_1) else "none"
        r2 = str(ranking_2).strip().lower() if not pd.isna(ranking_2) else "none"
        
        # 🌟 PRESERVE SPREADSHEET WORD: If r1 is valid text, keep it directly
        self.ranking_1_word = r1 if (r1 in self.VALID_RANKINGS or (r1 and r1 != "nan")) else "none"
        self.ranking_2_word = r2 if (r2 in self.VALID_RANKINGS or (r2 and r2 != "nan")) else "none"
        
        self.ranking_1 = self.ranking_1_word  
        self.ranking_2 = self.ranking_2_word
        self.rank_1 = self.ranking_1_word     
        self.rank_2 = self.ranking_2_word     

        # Assign numerical values safely (fallback default 1 for unknown text ranks)
        self.ranking_1_value = self.RANKING_VALUES.get(self.ranking_1_word, 1 if self.ranking_1_word != "none" else 0)
        self.ranking_2_value = self.RANKING_VALUES.get(self.ranking_2_word, 1 if self.ranking_2_word != "none" else 0)
        self.rank_1_val = self.ranking_1_value
        self.rank_2_val = self.ranking_2_value
        
        self.rarity = str(rarity).strip().capitalize() if rarity and not pd.isna(rarity) else "Common"
        
        # 6. Image URL Parsing
        clean_img = str(image_url).strip() if image_url and not pd.isna(image_url) else ""
        if clean_img.startswith(("http://", "https://", "/", "static/")):
            self.image_url = clean_img
        else:
            self.image_url = ""
            
        self.img_url = self.image_url
        
        # 7. Oracle Rules Text
        clean_text = str(oracle_text).strip() if oracle_text and not pd.isna(oracle_text) else ""
        self.oracle_text = clean_text
        self.text = clean_text
        
        self.excel_row_num = kwargs.get("excel_row_num", None)

    def serves_purpose(self, purpose: str) -> bool:
        clean_purpose = purpose.strip().lower()
        return self.card_class_1 == clean_purpose or self.card_class_2 == clean_purpose

    def get_max_speed(self) -> int:
        return max(self.ranking_1_value, self.ranking_2_value)
    
    def is_perfect_pair(self) -> bool:
        is_optimized = str(self.ranking_1_word).strip().lower() == "optimized"
        is_draw = str(self.card_class_1).strip().lower() == "draw"
        return is_optimized and is_draw

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "identity": self.identity,
            "mana_cost": self.mana_cost,
            "price": self.price,
            "card_class_1": self.card_class_1,
            "card_class_2": self.card_class_2,
            "ranking_1": self.ranking_1_word,
            "ranking_2": self.ranking_2_word,
            "ranking_1_value": self.ranking_1_value,
            "ranking_2_value": self.ranking_2_value,
            "rarity": self.rarity,
            "image_url": self.image_url,
            "oracle_text": self.oracle_text
        }





