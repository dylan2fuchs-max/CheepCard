import sys
import os
import re
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Card_Filter import Card

class CardProfiler:
    def __init__(self, file_path=None):
        # Load all cards from PostgreSQL database via SQLAlchemy
        self.cards = []
        self.load_cards_from_db()
        
        # Isolate hand-reviewed cards
        self.reviewed_cards = [
            c for c in self.cards 
            if (
                (c.card_class_1 and str(c.card_class_1).lower() not in ['none', 'nan', ''] and not str(c.card_class_1).lower().endswith('m')) or
                (c.card_class_2 and str(c.card_class_2).lower() not in ['none', 'nan', ''] and not str(c.card_class_2).lower().endswith('m'))
            )
            and (
                (c.ranking_1_word and str(c.ranking_1_word).lower() not in ['none', 'nan', '']) or 
                (c.ranking_2_word and str(c.ranking_2_word).lower() not in ['none', 'nan', ''])
            )
        ]

    def load_cards_from_db(self):
        """Fetches all cards from the database."""
        try:
            self.cards = Card.query.all()
            print(f"[Profiler] Loaded {len(self.cards)} cards from PostgreSQL database.")
        except Exception as e:
            print(f"[Profiler Error] Could not query database: {e}")
            self.cards = []

    def _extract_numeric_mana(self, raw_val):
        if raw_val is None:
            return None
        try:
            return float(raw_val)
        except (ValueError, TypeError):
            pass
            
        val_str = str(raw_val)
        bracket_numbers = re.findall(r'\{(\d+)\}', val_str)
        if bracket_numbers:
            return float(sum(int(n) for n in bracket_numbers))
            
        all_digits = re.findall(r'\d+', val_str)
        if all_digits:
            return float(all_digits[0])
            
        return None

    def _get_land_mana_profile(self, card):
        text = card.oracle_text.lower() if card.oracle_text else ""
        traits = []
        if "any color" in text:
            traits.append("any_color")
        if "sacrifice" in text:
            traits.append("sac")
        if "enters the battlefield tapped" in text or "enters the battlefield, tapped" in text:
            traits.append("tapped")
        else:
            traits.append("untapped")
            
        for symbol in ['{w}', '{u}', '{b}', '{r}', '{g}', '{c}']:
            if symbol in text:
                traits.append(symbol)
        return traits

    def _get_ramp_profile(self, card):
        text = card.oracle_text.lower() if card.oracle_text else ""
        traits = []
        if "add" in text:
            traits.append("produces_mana")
        if "search your library" in text and ("land" in text or "basic" in text):
            traits.append("land_search")
        if "treasure" in text:
            traits.append("treasure_generation")
        if "additional land" in text or "play an additional" in text:
            traits.append("extra_land_drop")
            
        for symbol in ['{w}', '{u}', '{b}', '{r}', '{g}', '{c}']:
            if symbol in text:
                traits.append(f"produces_{symbol}")
        return traits

    def generate_granular_profiles(self, target_class):
        clean_target = target_class.strip().lower()
        class_cards = [c for c in self.reviewed_cards if c.serves_purpose(clean_target)]
        
        if not class_cards:
            print(f"\n[Notice] No cards found for Class: '{target_class}'")
            return

        all_ranks = set()
        for c in class_cards:
            if c.ranking_1_word and c.ranking_1_word not in ['none', 'nan', '']:
                all_ranks.add(c.ranking_1_word)
            if c.ranking_2_word and c.ranking_2_word not in ['none', 'nan', '']:
                all_ranks.add(c.ranking_2_word)
        
        if not all_ranks:
            all_ranks = ['default']

        for rank in sorted(list(all_ranks)):
            rank_cards = class_cards if rank == 'default' else [
                c for c in class_cards if c.ranking_1_word == rank or c.ranking_2_word == rank
            ]
            
            if not rank_cards:
                continue

            color_groups = {}
            for c in rank_cards:
                ident = c.identity if c.identity else "{COLORLESS}"
                if ident not in color_groups:
                    color_groups[ident] = []
                color_groups[ident].append(c)

            valid_rank_groups = {k: v for k, v in color_groups.items() if len(v) >= 10}
            if not valid_rank_groups:
                continue

            print(f"\n==================================================")
            print(f" CLASS: {target_class.upper()} | RANK: {rank.upper()}")
            print(f"==================================================")

            for color_label, color_sub_list in valid_rank_groups.items():
                self._print_color_stats(color_sub_list, color_label)

    def _print_color_stats(self, color_sub_list, color_label):
        count = len(color_sub_list)
        if count == 0:
            return

        manas = [self._extract_numeric_mana(c.raw_mana_val) for c in color_sub_list]
        manas = [m for m in manas if m is not None]
        avg_mana = round(sum(manas) / len(manas), 2) if manas else "N/A"

        all_types = []
        for c in color_sub_list:
            t_line = getattr(c, 'raw_type', '')
            for base_t in ['Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment', 'Land', 'Planeswalker']:
                if base_t.lower() in t_line.lower():
                    all_types.append(base_t)
        type_counts = dict(Counter(all_types).most_common(4))

        all_phrases = []
        stopwords = {'to', 'the', 'a', 'of', 'and', 'card', 'cards', 'target', 'that', 'it', 'you', 'your', 'with', 'on', 'as', 'by', 'at', 'an', 'each', 'from', 'this', 'or', 'in', 'is', 'for'}
        
        for c in color_sub_list:
            if c.oracle_text:
                words = re.findall(r'\b[a-zA-Z]{3,}\b', c.oracle_text.lower())
                filtered_words = [w if w not in stopwords else "_" for w in words]
                for i in range(len(filtered_words) - 1):
                    p2 = f"{filtered_words[i]} {filtered_words[i+1]}"
                    if "_" not in p2: all_phrases.append(p2)
                for i in range(len(filtered_words) - 2):
                    p3 = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
                    if "_" not in p3: all_phrases.append(p3)

        common_phrases = [phrase for phrase, count in Counter(all_phrases).most_common(5)]

        print(f"    ----------------------------------------------")
        print(f"    -> Color Group: {color_label} (Cards: {count})")
        print(f"      * Avg Mana Value:      {avg_mana}")
        print(f"      * Top Types:       {type_counts}")
        print(f"      * Common Phrases: {common_phrases}")

    def _print_grand_color_stats(self, color_sub_list, color_label):
        count = len(color_sub_list)
        if count == 0:
            return

        manas = [self._extract_numeric_mana(c.raw_mana_val) for c in color_sub_list]
        manas = [m for m in manas if m is not None]
        avg_mana = round(sum(manas) / len(manas), 2) if manas else "N/A"

        all_types = []
        for c in color_sub_list:
            t_line = getattr(c, 'raw_type', '')
            for base_t in ['Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment', 'Land', 'Planeswalker']:
                if base_t.lower() in t_line.lower():
                    all_types.append(base_t)
        type_counts = dict(Counter(all_types).most_common(4))

        all_phrases = []
        stopwords = {'to', 'the', 'a', 'of', 'and', 'card', 'cards', 'target', 'that', 'it', 'you', 'your', 'with', 'on', 'as', 'by', 'at', 'an', 'each', 'from', 'this', 'or', 'in', 'is', 'for'}
        
        for c in color_sub_list:
            if c.oracle_text:
                words = re.findall(r'\b[a-zA-Z]{3,}\b', c.oracle_text.lower())
                filtered_words = [w if w not in stopwords else "_" for w in words]
                for i in range(len(filtered_words) - 1):
                    p2 = f"{filtered_words[i]} {filtered_words[i+1]}"
                    if "_" not in p2: all_phrases.append(p2)
                for i in range(len(filtered_words) - 2):
                    p3 = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
                    if "_" not in p3: all_phrases.append(p3)

        common_phrases = [phrase for phrase, count in Counter(all_phrases).most_common(5)]

        print(f"\n    [MASTER COLOR DEFINITION] -> {color_label}")
        print(f"      * Total Cards in Pool: {count}")
        print(f"      * Overall Avg Mana:    {avg_mana}")
        print(f"      * Dominant Types:      {type_counts}")
        print(f"      * Core Key Phrases:    {common_phrases}")

if __name__ == "__main__":
    from app import app, db  # Import your Flask app instance
    
    with app.app_context():
        try:
            profiler = CardProfiler()
            
            print("\n========================================")
            print("   GRANULAR PROFILER + PRECISION SUMMARY")
            print("========================================")
            
            while True:
                try:
                    target_class = input("\nEnter class to evaluate (e.g., Removal, Ramp, Draw, Land, Board Wipe) or type 'exit': ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nExiting profiler. Have a great day!")
                    break
                    
                if target_class.lower() == 'exit':
                    print("Exiting profiler. Have a great day!")
                    break
                    
                if not target_class:
                    continue
                    
                profiler.generate_granular_profiles(target_class=target_class)
                
        except Exception as e:
            print(f"❌ Error initializing profiler: {e}")