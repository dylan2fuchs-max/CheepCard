import sys
import os
import pandas as pd
from collections import Counter
import re

# Add the parent directory (CheepCards root) to Python's search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Card_Filter import Card

class CardProfiler:
    def __init__(self, file_path="../Magic Card Data Base Current View.xlsx"):
        self.file_path = file_path
        self.df = pd.read_excel(self.file_path, engine="openpyxl")
        
        # Convert every Excel row into your validated Card object
        self.cards = []
        for _, row in self.df.iterrows():
            row_dict = row.to_dict()
            
            card_obj = Card(
                name=row_dict.get('Name') or row_dict.get('name'),
                identity=row_dict.get('Colors') or row_dict.get('Identity') or row_dict.get('identity'),
                mana_cost=row_dict.get('Mana Value') or row_dict.get('Mana Cost') or row_dict.get('mana_cost'),
                price=row_dict.get('Price', 0.0),
                ranking_1=row_dict.get('Ranking 1') or row_dict.get('Rank 1') or row_dict.get('ranking_1'),
                ranking_2=row_dict.get('Ranking 2') or row_dict.get('Rank 2') or row_dict.get('ranking_2'),
                card_class_1=row_dict.get('Class 1') or row_dict.get('Card Class 1') or row_dict.get('card_class_1'),
                card_class_2=row_dict.get('Class 2') or row_dict.get('Card Class 2') or row_dict.get('card_class_2'),
                rarity=row_dict.get('Rarity', 'Common'),
                image_url=row_dict.get('Image URL', ''),
                oracle_text=row_dict.get('Text') or row_dict.get('Oracle Text') or row_dict.get('oracle_text')
            )
            
            card_obj.raw_type = str(row_dict.get('Type') or row_dict.get('Type Line') or '')
            card_obj.raw_mana_val = row_dict.get('Mana Value') or row_dict.get('Mana Cost') or row_dict.get('CMC') or 0
            self.cards.append(card_obj)
            
        # Isolate hand-reviewed cards (strictly excluding temporary machine-tags ending in 'm' like DrawM)
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

    def _extract_numeric_mana(self, raw_val):
        """Safely parses numbers from raw mana values or MTG cost strings like '{2}{G}'."""
        if pd.isna(raw_val):
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
        """Extracts mana production traits from a land's oracle text."""
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
            if rank == 'default':
                rank_cards = class_cards
            else:
                rank_cards = [
                    c for c in class_cards 
                    if c.ranking_1_word == rank or c.ranking_2_word == rank
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

        print(f"\n" + "#"*55)
        print(f" 🌟 GRAND CLASS SUMMARY: {target_class.upper()} (Pooled Total >= 10)")
        print(f"#"*55)

        grand_color_groups = {}
        for c in class_cards:
            ident = c.identity if c.identity else "{COLORLESS}"
            if ident not in grand_color_groups:
                grand_color_groups[ident] = []
            grand_color_groups[ident].append(c)

        displayed_count = 0
        skipped_groups = []

        for color_label, color_sub_list in grand_color_groups.items():
            if len(color_sub_list) >= 10:
                self._print_grand_color_stats(color_sub_list, color_label)
                displayed_count += 1
            else:
                skipped_groups.append(f"{color_label} ({len(color_sub_list)} cards)")

        if skipped_groups:
            print(f"\n    [Notice] Excluded low-sample groups (<10 total cards): {', '.join(skipped_groups)}")

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
        print(f"      * Avg Mana Value: {avg_mana}")
        print(f"      * Top Types:      {type_counts}")
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
    try:
        profiler = CardProfiler("../Magic Card Data Base Current View.xlsx")
        
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