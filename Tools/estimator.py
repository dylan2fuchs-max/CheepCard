import sys
import os
import pandas as pd
from collections import Counter
import re

# Add parent directory to path to import Card_Filter and CardProfiler
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Card_Filter import Card
from profiler import CardProfiler

class CardEstimator(CardProfiler):
    def __init__(self, file_path="../Magic Card Data Base Current View.xlsx"):
        super().__init__(file_path)
        
        self.unreviewed_cards = [
            c for c in self.cards 
            if (c.card_class_1 in ['none', 'nan', ''] and c.card_class_2 in ['none', 'nan', ''])
        ]
        
        self.known_classes = set()
        for c in self.reviewed_cards:
            c1 = str(c.card_class_1).strip().lower()
            c2 = str(c.card_class_2).strip().lower()
            
            if c1 and c1 not in ['none', 'nan', ''] and not c1.endswith('m'):
                self.known_classes.add(c1)
            if c2 and c2 not in ['none', 'nan', ''] and not c2.endswith('m'):
                self.known_classes.add(c2)

    def _get_top_phrases(self, card_sub_list, top_n=15):
        all_phrases = []
        stopwords = {'to', 'the', 'a', 'of', 'and', 'card', 'cards', 'target', 'that', 'it', 'you', 'your', 'with', 'on', 'as', 'by', 'at', 'an', 'each', 'from', 'this', 'or', 'in', 'is', 'for'}
        
        for c in card_sub_list:
            if c.oracle_text:
                words = re.findall(r'\b[a-zA-Z]{3,}\b', c.oracle_text.lower())
                filtered_words = [w if w not in stopwords else "_" for w in words]
                for i in range(len(filtered_words) - 1):
                    p2 = f"{filtered_words[i]} {filtered_words[i+1]}"
                    if "_" not in p2: all_phrases.append(p2)
                for i in range(len(filtered_words) - 2):
                    p3 = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
                    if "_" not in p3: all_phrases.append(p3)
        return [phrase for phrase, count in Counter(all_phrases).most_common(top_n)]

    def passes_sanity_check(self, type_line, oracle_text, target_class):
        target = str(target_class).lower()
        t_line = str(type_line).lower()
        o_text = str(oracle_text).lower()
        
        if target == 'land':
            return 'land' in t_line
            
        elif target == 'draw':
            return 'draw card' in o_text or 'draw ' in o_text or 'exile the top' in o_text
            
        elif target == 'boardwipe':
            return ('destroy all' in o_text or 'exile all' in o_text or 'each creature' in o_text or 'damage to each' in o_text)
            
        elif target == 'removal':
            has_destroy = bool(re.search(r'destroy\s+(target|each|chosen)', o_text))
            has_exile = bool(re.search(r'exile\s+(target|each|chosen)', o_text))
            has_fight = 'fight target' in o_text or ' fights ' in o_text
            has_counter = 'counter target' in o_text
            has_burn = bool(re.search(r'deals?\s+\d+\s+damage\s+to\s+(target|any)', o_text))
            
            has_safe_sacrifice = False
            if 'sacrifice' in o_text:
                if re.search(r'(sacrifice\s+a\s+(creature|permanent|planeswalker|nonland))|(target\s+player\s+sacrifices)', o_text):
                    if not re.search(r'sacrifice\s+(this|a)\s+(token|treasure|artifact|food|blood)', o_text):
                        has_safe_sacrifice = True

            return has_destroy or has_exile or has_fight or has_counter or has_burn or has_safe_sacrifice
            
        elif target == 'ramp':
            has_add_mana = bool(re.search(r'\badd\s+[{[a-zA-Z]', o_text)) or 'add one mana' in o_text
            has_search_land = 'search your library' in o_text and ('land' in o_text or 'basic' in o_text)
            has_treasure = 'treasure token' in o_text or 'create a treasure' in o_text
            has_extra_land = 'additional land' in o_text or 'play an additional' in o_text
            
            return has_add_mana or has_search_land or has_treasure or has_extra_land
            
        return True

    def estimate_card(self, card: Card):
        card_identity = card.identity if card.identity else "{COLORLESS}"
        card_text = card.oracle_text.lower() if card.oracle_text else ""
        card_mana = self._extract_numeric_mana(card.raw_mana_val)
        card_type_line = str(card.raw_type).lower() if hasattr(card, 'raw_type') else ""
        
        class_scores = Counter()

        for target_class in self.known_classes:
            if not self.passes_sanity_check(card_type_line, card_text, target_class):
                continue

            class_pool = [c for c in self.reviewed_cards if c.serves_purpose(target_class)]
            if not class_pool:
                continue

            color_matched_pool = [
                c for c in class_pool 
                if (c.identity if c.identity else "{COLORLESS}") == card_identity
            ]
            
            if not color_matched_pool:
                continue

            score = 0.0
            top_phrases = self._get_top_phrases(color_matched_pool, top_n=15)
            phrase_hits = sum(1 for phrase in top_phrases if phrase in card_text)
            score += phrase_hits * 3.0
            
            pool_manas = [self._extract_numeric_mana(c.raw_mana_val) for c in color_matched_pool]
            pool_manas = [m for m in pool_manas if m is not None]
            if pool_manas and card_mana is not None:
                avg_pool_mana = sum(pool_manas) / len(pool_manas)
                if abs(card_mana - avg_pool_mana) <= 1.5:
                    score += 2.0

            class_scores[target_class] = score

        if not class_scores:
            return {"class": "N/A", "rank": "N/A"}

        top_class, _ = class_scores.most_common(1)[0]
        best_class = top_class.capitalize()

        winning_class_pool = [
            c for c in self.reviewed_cards 
            if c.serves_purpose(best_class.lower()) and 
               ((c.identity if c.identity else "{COLORLESS}") == card_identity)
        ]
        
        if not winning_class_pool:
            return {"class": best_class, "rank": "N/A"}

        class_ranks = set()
        for c in winning_class_pool:
            if c.ranking_1_word and c.ranking_1_word not in ['none', 'nan', '']: 
                class_ranks.add(c.ranking_1_word.capitalize())
            if c.ranking_2_word and c.ranking_2_word not in ['none', 'nan', '']: 
                class_ranks.add(c.ranking_2_word.capitalize())

        rank_scores = Counter()
        for rank in class_ranks:
            rank_pool = [
                c for c in winning_class_pool 
                if (c.ranking_1_word and c.ranking_1_word.capitalize() == rank) or 
                   (c.ranking_2_word and c.ranking_2_word.capitalize() == rank)
            ]
            if not rank_pool:
                continue

            r_score = 0.0
            r_phrases = self._get_top_phrases(rank_pool, top_n=10)
            r_hits = sum(1 for p in r_phrases if p in card_text)
            r_score += r_hits * 2.5
            
            r_manas = [self._extract_numeric_mana(c.raw_mana_val) for c in rank_pool]
            r_manas = [m for m in r_manas if m is not None]
            if r_manas and card_mana is not None:
                avg_r_mana = sum(r_manas) / len(r_manas)
                if abs(card_mana - avg_r_mana) <= 1.0:
                    r_score += 1.5

            rank_scores[rank] = r_score

        best_rank = rank_scores.most_common(1)[0][0] if rank_scores else "N/A"
        return {"class": best_class, "rank": best_rank}

    def export_triage_report(self, target_class_filter="Removal", output_filename="Mator_Triage_Report.xlsx"):
        """
        Exports a fully sorted triage report comparing current assigned classes 
        against Mator's independent class and rank suggestions.
        """
        print(f"\n========================================")
        print(f" 🚀 GENERATING SORTED TRIAGE REPORT")
        print(f" 🎯 Target Filter: [{target_class_filter.capitalize()}]")
        print(f"========================================")
        
        triage_records = []
        
        def clean_class(val):
            s = str(val).strip().lower()
            if s.endswith('m'):
                return s[:-1]
            return s

        for idx, row in self.df.iterrows():
            c1 = str(row.get('Class 1') or row.get('Card Class 1') or '')
            c2 = str(row.get('Class 2') or row.get('Card Class 2') or '')
            r1 = str(row.get('Ranking 1') or row.get('Rank 1') or '')
            r2 = str(row.get('Ranking 2') or row.get('Rank 2') or '')
            
            c1_clean = clean_class(c1)
            c2_clean = clean_class(c2)
            
            target = target_class_filter.lower()
            accepted_targets = [target]
            if target == "removal":
                accepted_targets.append("remvoal")
                
            # Must match the target class filter
            if c1_clean not in accepted_targets and c2_clean not in accepted_targets:
                continue
                
            # 🌟 Must be missing an existing rank
            has_existing_rank = (r1.lower() not in ['none', 'nan', '']) or (r2.lower() not in ['none', 'nan', ''])
            if has_existing_rank:
                continue
                
            card_obj = self.cards[idx]
            t_line = str(row.get('Type') or row.get('Card Type') or '')
            
            # Run Mator's estimation engine to see its suggested class & rank
            prediction = self.estimate_card(card_obj)
            
            assigned_display = c1 if c1 not in ['none', 'nan', ''] else c2
            existing_rank = r1 if r1 not in ['none', 'nan', ''] else r2
            
            triage_records.append({
                'Index': idx,
                'Card Name': card_obj.name,
                'Color Identity': card_obj.identity if card_obj.identity else "{COLORLESS}",
                'Mana Cost': card_obj.raw_mana_val,
                'Card Type': t_line,
                'Assigned Class': assigned_display,
                'Mator Suggested Class': prediction['class'],  # Shows if Mator wants to change it to N/A, Draw, etc.
                'Existing Rank': existing_rank if existing_rank else "MISSING",
                'Mator Suggested Rank': prediction['rank'],
                'Oracle Text': card_obj.oracle_text
            })
            
        triage_df = pd.DataFrame(triage_records)
        
        # 📊 MULTI-LEVEL SORTING: Color -> Suggested Class -> Suggested Rank -> Card Name
        if not triage_df.empty:
            triage_df = triage_df.sort_values(
                by=['Color Identity', 'Mator Suggested Class', 'Mator Suggested Rank', 'Card Name'], 
                ascending=[True, True, True, True]
            )
        
        # Write to independent Excel sheet without touching the master database
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            triage_df.to_excel(writer, sheet_name='Triage_Report', index=False)
            
        print(f"\n[Success] Sorted triage report successfully created!")
        print(f"📁 Cards Processed & Exported: {len(triage_df)}")
        print(f"📁 New File Saved: {output_filename}")
        print(f"🛡️ Master Database left completely untouched.")

    def autofill_database(self, target_class_filter=None, output_path=None):
        if output_path is None:
            output_path = self.file_path

        print(f"\n========================================")
        print(f" 📦 MATOR INTERACTIVE SWEEP - STARTING")
        if target_class_filter:
            print(f" 🎯 Target Class Filter: [{target_class_filter.capitalize()}]")
        print(f"========================================")
        
        updated_count = 0
        na_count = 0
        
        class_shortcuts = {
            'r': 'Removal',
            'd': 'Draw',
            'b': 'Boardwipe',
            'a': 'Ramp',
            'l': 'Land'
        }
        
        eligible_indices = []
        for idx, row in self.df.iterrows():
            c1 = str(row.get('Class 1') or row.get('Card Class 1') or '')
            c2 = str(row.get('Class 2') or row.get('Card Class 2') or '')
            r1 = str(row.get('Ranking 1') or row.get('Rank 1') or '')
            r2 = str(row.get('Ranking 2') or row.get('Rank 2') or '')
            
            target = target_class_filter.lower() if target_class_filter else ""
            
            def clean_class(val):
                s = str(val).strip().lower()
                if s.endswith('m'):
                    return s[:-1]
                return s
            
            c1_clean = clean_class(c1)
            c2_clean = clean_class(c2)
            
            if target:
                accepted_targets = [target]
                if target == "removal":
                    accepted_targets.append("remvoal")
                if c1_clean not in accepted_targets and c2_clean not in accepted_targets:
                    continue
            else:
                if c1_clean not in ['none', 'nan', ''] or c2_clean not in ['none', 'nan', '']:
                    continue
            
            has_existing_rank = (r1.lower() not in ['none', 'nan', '']) or (r2.lower() not in ['none', 'nan', ''])
            if has_existing_rank:
                continue
                
            eligible_indices.append(idx)
            
        total_remaining = len(eligible_indices)
        print(f" 📋 Total Target Cards in Queue: {total_remaining}\n")

        for idx in eligible_indices:
            row = self.df.loc[idx]
            target = target_class_filter.lower() if target_class_filter else ""
            
            t_line = str(row.get('Type') or row.get('Card Type') or '')
            o_text = str(row.get('Oracle Text') or row.get('Text') or '')
            check_target = target if target else str(row.get('Class 1', '')).strip().lower()
            
            if check_target and not self.passes_sanity_check(t_line, o_text, check_target):
                self.df.at[idx, 'Class 1'] = "N/A"
                self.df.at[idx, 'Ranking 1'] = "N/A"
                na_count += 1
                total_remaining -= 1
                continue

            card_obj = self.cards[idx]
            prediction = self.estimate_card(card_obj)
            
            pred_class = prediction['class']
            pred_rank = prediction['rank']

            print(f"\n--------------------------------------------------")
            print(f" ⏳ Remaining Cards in Queue: {total_remaining}")
            print(f" Card: {card_obj.name} [{card_obj.identity}] (Mana: {card_obj.raw_mana_val})")
            print(f" Text: {card_obj.oracle_text}")
            print(f" 🤖 Mator Suggests ➔ Class: {pred_class} | Rank: {pred_rank}")
            print(f"--------------------------------------------------")
            
            while True:
                choice = input("Options: [y] Yes | [n] N/A | [R]emoval | [D]raw | [B]oardwipe | [A]ramp | [l]and | [S]ave & Stop: ").strip().lower()
                
                if choice == 's':
                    print("\n💾 [Save & Stop] Saving current progress to Excel and exiting sweep.")
                    self.df.to_excel(output_path, index=False)
                    return
                elif choice == 'y':
                    final_class = pred_class
                    final_rank = pred_rank
                    break
                elif choice == 'n':
                    final_class = "N/A"
                    final_rank = "N/A"
                    break
                elif choice in class_shortcuts:
                    final_class = class_shortcuts[choice]
                    final_rank = pred_rank
                    break
                else:
                    print("❌ Invalid option. Please press y, n, r, d, b, a, l, or s.")

            if final_class != "N/A":
                tagged_class = f"{final_class}M"
                self.df.at[idx, 'Class 1'] = tagged_class
                self.df.at[idx, 'Ranking 1'] = final_rank
                updated_count += 1
                print(f" ✨ [Accepted & Tagged] {card_obj.name} ➔ Class: {tagged_class} | Rank: {final_rank}")
                
                card_obj.card_class_1 = tagged_class
                card_obj.ranking_1_word = final_rank
                self.reviewed_cards.append(card_obj)
            else:
                self.df.at[idx, 'Class 1'] = "N/A"
                self.df.at[idx, 'Ranking 1'] = "N/A"
                na_count += 1
                print(f" 🛡️ [Marked N/A] {card_obj.name}")
                
            total_remaining -= 1

        try:
            self.df.to_excel(output_path, index=False)
            print(f"\n========================================")
            print(f" 🎉 [Success] Interactive batch complete!")
            print(f" * Updated & Tagged: {updated_count}")
            print(f" * Marked N/A: {na_count}")
            print(f" * Saved to: {output_path}")
            print(f"========================================")
        except Exception as e:
            print(f"\n[Error] Failed to save Excel file: {e}")

if __name__ == "__main__":
    estimator = CardEstimator()
    
    # Generate triage report specifically for Removal cards missing ranks
    estimator.export_triage_report(target_class_filter="Removal", output_filename="Mator_Removal_Ranking_Triage.xlsx")
    
    # Interactive CLI Testing Mode
    print(f"\n========================================")
    print(f"   HIERARCHICAL DNA ESTIMATOR - INTERACTIVE")
    print(f"========================================")
    print(f" * Validated Ground-Truth Cards: {len(estimator.reviewed_cards)}")
    print(f" * Total Cards in Database:      {len(estimator.cards)}")
    print(f" * Active Classes Recognized:    {[c.capitalize() for c in estimator.known_classes]}")
    
    while True:
        card_name = input("\nType a card name to estimate (or type 'exit'): ").strip()
        if card_name.lower() == 'exit':
            print("Exiting estimator. Let the games begin next time!")
            break
            
        if not card_name:
            continue
            
        matches = [c for c in estimator.cards if c.name and card_name.lower() in c.name.lower()]
        
        if not matches:
            print(f"❌ Could not find any card matching '{card_name}' in the database.")
            continue
            
        for match in matches:
            print(f"\n--------------------------------------------------")
            print(f" Card Found: {match.name} [{match.identity}] (Mana: {match.raw_mana_val})")
            print(f"   * Actual Spreadsheet Data -> Class: {match.card_class_1} | Rank: {match.ranking_1_word}")
            
            prediction = estimator.estimate_card(match)
            print(f"   * 🧬 DNA Estimator Guess  -> Class: {prediction['class']} | Rank: {prediction['rank']}")
            print(f"--------------------------------------------------")