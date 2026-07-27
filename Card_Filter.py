import pandas as pd

class Card:
    # Valid pools to check individual entries against
    VALID_CLASSES = ["draw", "ramp", "removal", "boardwipe", "land", "none", "nan", ""]
    VALID_RANKINGS = ["optimized", "fast", "average", "passive", "low", "none", "nan", ""]
    
    RANKING_VALUES = {
        "optimized": 5, "fast": 4, "average": 3, "passive": 2, "low": 1, "none": 0, "nan": 0
    }

    def __init__(self, name: str, identity: str, mana_cost: str, price: float, 
                 ranking_1, ranking_2, card_class_1, card_class_2, rarity: str):
        
        # 1. Validate Name
        self.name = str(name).strip() if name and not pd.isna(name) else "Unknown Card"
        
        # 2. Validate Identity formatting (Ensure it has braces if it's a raw letter)
        raw_id = str(identity).strip().upper() if identity and not pd.isna(identity) else "{COLORLESS}"
        if len(raw_id) == 1 and raw_id in "WUBRG":
            self.identity = f"{{{raw_id}}}"
        else:
            self.identity = raw_id
            
        self.mana_cost = str(mana_cost).strip() if mana_cost and not pd.isna(mana_cost) else "{0}"
        
        # 3. Limit / Validate Price (Force it to a positive number, fallback to 0.00)
        try:
            clean_price = float(str(price).replace('$', '').strip())
            self.price = max(0.00, clean_price) # Limits price so it can never be negative
        except (ValueError, TypeError):
            self.price = 0.00 # Fallback for corrupted or empty price fields
            
        # 4. Limit / Validate Classes
        c1 = str(card_class_1).strip().lower() if not pd.isna(card_class_1) else "none"
        c2 = str(card_class_2).strip().lower() if not pd.isna(card_class_2) else "none"
        
        self.card_class_1 = c1 if c1 in self.VALID_CLASSES else "none"
        self.card_class_2 = c2 if c2 in self.VALID_CLASSES else "none"
        
        if c1 not in self.VALID_CLASSES and c1 != "none":
            print(f"⚠️ Warning: Card '{self.name}' has invalid Class 1: '{card_class_1}'. Set to 'none'.")

        # 5. Limit / Validate Rankings
        r1 = str(ranking_1).strip().lower() if not pd.isna(ranking_1) else "none"
        r2 = str(ranking_2).strip().lower() if not pd.isna(ranking_2) else "none"
        
        self.ranking_1_word = r1 if r1 in self.VALID_RANKINGS else "none"
        self.ranking_2_word = r2 if r2 in self.VALID_RANKINGS else "none"
        
        if r1 not in self.VALID_RANKINGS and r1 != "none":
            print(f"⚠️ Warning: Card '{self.name}' has invalid Ranking 1: '{ranking_1}'. Set to 'none'.")

        # Assign numerical values safely using our pool
        self.ranking_1_value = self.RANKING_VALUES.get(self.ranking_1_word, 0)
        self.ranking_2_value = self.RANKING_VALUES.get(self.ranking_2_word, 0)
        
        self.rarity = str(rarity).strip().capitalize() if rarity and not pd.isna(rarity) else "Common"


    def serves_purpose(self, purpose: str) -> bool:
        """Checks if the card fits a role across either Class 1 or Class 2."""
        clean_purpose = purpose.strip().lower()
        return self.card_class_1 == clean_purpose or self.card_class_2 == clean_purpose

    def get_max_speed(self) -> int:
        """Returns the highest numerical ranking value this card holds."""
        return max(self.ranking_1_value, self.ranking_2_value)
    
    def is_perfect_pair(self) -> bool:
        """Returns True if Ranking 1 is 'Optimized' and Class 1 is 'Draw'."""
        # Clean up strings to prevent mismatch bugs
        is_optimized = str(self.ranking_1_word).strip().lower() == "optimized"
        is_draw = str(self.card_class_1).strip().lower() == "draw"
        
        return is_optimized and is_draw




