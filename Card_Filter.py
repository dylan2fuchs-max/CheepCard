import pandas as pd
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Card(db.Model):
    __tablename__ = 'cards'

    id = db.Column(db.Integer, primary_key=True)
    
    VALID_CLASSES = ["draw", "ramp", "removal", "board wipe", "land", "none", "nan", ""]
    VALID_RANKINGS = ["optimized", "fast", "average", "medium", "passive", "low", "fat", "none", "nan", ""]
    
    RANKING_VALUES = {
        "optimized": 5, "fast": 4, "average": 3, "medium": 3,
        "passive": 2, "low": 1, "fat": 1, "none": 0, "nan": 0, "": 0
    }

    # Database Columns
    _name = db.Column("name", db.String(150), unique=True, index=True, nullable=False)
    _identity = db.Column("identity", db.String(20), index=True)
    _mana_cost = db.Column("mana_cost", db.String(50))
    _raw_type = db.Column("raw_type", db.String(150))  # 🌟 Added raw_type column
    _price = db.Column("price", db.Float, default=0.00)
    
    _card_class_1 = db.Column("card_class_1", db.String(50), index=True)
    _card_class_2 = db.Column("card_class_2", db.String(50))
    
    _ranking_1_word = db.Column("ranking_1_word", db.String(50))
    _ranking_2_word = db.Column("ranking_2_word", db.String(50))
    
    _rarity = db.Column("rarity", db.String(50), default="Common")
    _image_url = db.Column("image_url", db.Text)
    _oracle_text = db.Column("oracle_text", db.Text)

    def __init__(self, name: str = "Unknown Card", identity: str = "{COLORLESS}", mana_cost: str = "{0}", 
                 price: float = 0.00, ranking_1="none", ranking_2="none", 
                 card_class_1="none", card_class_2="none", rarity: str = "Common",
                 image_url: str = "", oracle_text: str = "", raw_type: str = "", **kwargs):
        
        self.name = str(name).strip() if name and not pd.isna(name) else "Unknown Card"
        
        raw_id = str(identity).strip().upper() if identity and not pd.isna(identity) else "{COLORLESS}"
        if len(raw_id) == 1 and raw_id in "WUBRG":
            self.identity = f"{{{raw_id}}}"
        else:
            self.identity = raw_id
            
        self.mana_cost = str(mana_cost).strip() if mana_cost and not pd.isna(mana_cost) else "{0}"
        self.raw_type = str(raw_type).strip() if raw_type and not pd.isna(raw_type) else ""

        try:
            clean_price = float(str(price).replace('$', '').strip())
            self.price = max(0.00, clean_price)
        except (ValueError, TypeError):
            self.price = 0.00
            
        c1 = str(card_class_1).strip().lower() if not pd.isna(card_class_1) else "none"
        c2 = str(card_class_2).strip().lower() if not pd.isna(card_class_2) else "none"
        
        self.card_class_1 = c1 if c1 and c1 != "nan" else "none"
        self.card_class_2 = c2 if c2 and c2 != "nan" else "none"

        r1 = str(ranking_1).strip().lower() if not pd.isna(ranking_1) else "none"
        r2 = str(ranking_2).strip().lower() if not pd.isna(ranking_2) else "none"
        
        self.ranking_1_word = r1 if (r1 in self.VALID_RANKINGS or (r1 and r1 != "nan")) else "none"
        self.ranking_2_word = r2 if (r2 in self.VALID_RANKINGS or (r2 and r2 != "nan")) else "none"
        
        self.rarity = str(rarity).strip().capitalize() if rarity and not pd.isna(rarity) else "Common"
        
        clean_img = str(image_url).strip() if image_url and not pd.isna(image_url) else ""
        self.image_url = clean_img if clean_img.startswith(("http://", "https://", "/", "static/")) else ""
            
        self.oracle_text = str(oracle_text).strip() if oracle_text and not pd.isna(oracle_text) else ""
        self.excel_row_num = kwargs.get("excel_row_num", None)

    # --- Property Aliases for Backward Compatibility ---
    @property
    def name(self): return self._name
    @name.setter
    def name(self, val): self._name = val

    @property
    def identity(self): return self._identity
    @identity.setter
    def identity(self, val): self._identity = val

    @property
    def mana_cost(self): return self._mana_cost
    @mana_cost.setter
    def mana_cost(self, val): self._mana_cost = val

    @property
    def raw_mana_val(self): return self._mana_cost

    @property
    def raw_type(self): return self._raw_type
    @raw_type.setter
    def raw_type(self, val): self._raw_type = val

    @property
    def price(self): return self._price
    @price.setter
    def price(self, val): self._price = val

    @property
    def card_class_1(self): return self._card_class_1
    @card_class_1.setter
    def card_class_1(self, val): self._card_class_1 = val

    @property
    def card_class_2(self): return self._card_class_2
    @card_class_2.setter
    def card_class_2(self, val): self._card_class_2 = val

    @property
    def class_1(self): return self._card_class_1
    @property
    def class_2(self): return self._card_class_2

    @property
    def ranking_1_word(self): return self._ranking_1_word
    @ranking_1_word.setter
    def ranking_1_word(self, val): self._ranking_1_word = val

    @property
    def ranking_2_word(self): return self._ranking_2_word
    @ranking_2_word.setter
    def ranking_2_word(self, val): self._ranking_2_word = val

    @property
    def ranking_1(self): return self._ranking_1_word
    @property
    def ranking_2(self): return self._ranking_2_word
    @property
    def rank_1(self): return self._ranking_1_word
    @property
    def rank_2(self): return self._ranking_2_word

    @property
    def ranking_1_value(self):
        return self.RANKING_VALUES.get(self._ranking_1_word, 1 if self._ranking_1_word != "none" else 0)

    @property
    def ranking_2_value(self):
        return self.RANKING_VALUES.get(self._ranking_2_word, 1 if self._ranking_2_word != "none" else 0)

    @property
    def rank_1_val(self): return self.ranking_1_value
    @property
    def rank_2_val(self): return self.ranking_2_value

    @property
    def rarity(self): return self._rarity
    @rarity.setter
    def rarity(self, val): self._rarity = val

    @property
    def image_url(self): return self._image_url
    @image_url.setter
    def image_url(self, val): self._image_url = val

    @property
    def img_url(self): return self._image_url

    @property
    def oracle_text(self): return self._oracle_text
    @oracle_text.setter
    def oracle_text(self, val): self._oracle_text = val

    @property
    def text(self): return self._oracle_text

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
            "raw_type": self.raw_type,
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





