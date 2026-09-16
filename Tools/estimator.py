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
        # Inherits data loading, cleaning, and the strict unranked-card filter from CardProfiler
        super().__init__(file_path)
        
        # Define unreviewed target cards for estimation
        self.unreviewed_cards = [
            c for c in self.cards 
            if (c.card_class_1 in ['none', 'nan', ''] and c.card_class_2 in ['none', 'nan', ''])
        ]
        
        # Dynamically discover all active classes available in your reviewed data
        # Dynamically discover all active classes, excluding machine-tagged 'M' suffixes and typos
        self.known_classes = set()
        for c in self.reviewed_cards:
            c1 = str(c.card_class_1).strip().lower()
            c2 = str(c.card_class_2).strip().lower()
            
            # Only add classes if they don't end in 'm' (blocking DrawM, RampM, etc.)
            if c1 and c1 not in ['none', 'nan', ''] and not c1.endswith('m'):
                self.known_classes.add(c1)
            if c2 and c2 not in ['none', 'nan', ''] and not c2.endswith('m'):
                self.known_classes.add(c2)

    def _get_top_phrases(self, card_sub_list, top_n=15):
        """Reuses the bi-gram/tri-gram phrase extraction logic from the profiler."""
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

    def estimate_card(self, card: Card):
        card_identity = card.identity if card.identity else "{COLORLESS}"
        card_text = card.oracle_text.lower() if card.oracle_text else ""
        card_mana = self._extract_numeric_mana(card.raw_mana_val)
        card_type_line = str(card.raw_type).lower() if hasattr(card, 'raw_type') else ""
        
        # ==========================================
        # 1. STRUCTURAL RULE: LANDS
        # ==========================================
        if 'land' in card_type_line:
            best_class = "Land"
        else:
            # ==========================================
            # 2. COLOR-FIRST CLASS COMPATIBILITY MATCH
            # ==========================================
            class_scores = Counter()

            for target_class in self.known_classes:
                # Get all reviewed cards serving this class
                class_pool = [c for c in self.reviewed_cards if c.serves_purpose(target_class)]
                if not class_pool:
                    continue

                # STRICT COLOR NARROWING: Only keep results matching this exact color combination
                color_matched_pool = [
                    c for c in class_pool 
                    if (c.identity if c.identity else "{COLORLESS}") == card_identity
                ]
                
                # If there are no cards of this color in this class, skip or give 0 score
                if not color_matched_pool:
                    continue

                score = 0.0
                
                # Compare similarity using top phrases from this color-matched class pool
                top_phrases = self._get_top_phrases(color_matched_pool, top_n=15)
                phrase_hits = sum(1 for phrase in top_phrases if phrase in card_text)
                score += phrase_hits * 3.0
                
                # Factor mana cost proximity within this color-matched pool
                pool_manas = [self._extract_numeric_mana(c.raw_mana_val) for c in color_matched_pool]
                pool_manas = [m for m in pool_manas if m is not None]
                if pool_manas and card_mana is not None:
                    avg_pool_mana = sum(pool_manas) / len(pool_manas)
                    if abs(card_mana - avg_pool_mana) <= 1.5:
                        score += 2.0

                class_scores[target_class] = score

            if not class_scores:
                return {"class": "N/A", "rank": "N/A"}

            # Determine the class with the highest similarity percentage/score
            top_class, _ = class_scores.most_common(1)[0]
            best_class = top_class.capitalize()

        # ==========================================
        # 3. FINAL RANK REVIEW (SIMILARITY MATCHING)
        # ==========================================
        # Get all reviewed cards for the winning class matching the card's color
        winning_class_pool = [
            c for c in self.reviewed_cards 
            if c.serves_purpose(best_class.lower()) and 
               ((c.identity if c.identity else "{COLORLESS}") == card_identity)
        ]
        
        if not winning_class_pool:
            return {"class": best_class, "rank": "N/A"}

        # Discover all unique ranks present in this filtered color/class pool
        class_ranks = set()
        for c in winning_class_pool:
            if c.ranking_1_word and c.ranking_1_word not in ['none', 'nan', '']: 
                class_ranks.add(c.ranking_1_word.capitalize())
            if c.ranking_2_word and c.ranking_2_word not in ['none', 'nan', '']: 
                class_ranks.add(c.ranking_2_word.capitalize())

        # Review each rank's sub-pool to find which one is most similar to the card
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
            
            # Check phrase similarity against this rank's specific pool
            r_phrases = self._get_top_phrases(rank_pool, top_n=10)
            r_hits = sum(1 for p in r_phrases if p in card_text)
            r_score += r_hits * 2.5
            
            # Check mana proximity against this rank's pool
            r_manas = [self._extract_numeric_mana(c.raw_mana_val) for c in rank_pool]
            r_manas = [m for m in r_manas if m is not None]
            if r_manas and card_mana is not None:
                avg_r_mana = sum(r_manas) / len(r_manas)
                if abs(card_mana - avg_r_mana) <= 1.0:
                    r_score += 1.5

            rank_scores[rank] = r_score

        if rank_scores:
            best_rank = rank_scores.most_common(1)[0][0]
        else:
            best_rank = "N/A"

        return {"class": best_class, "rank": best_rank}

    def run_estimation_sweep(self):
        print(f"\n========================================")
        print(f"   HIERARCHICAL DNA ESTIMATOR - SWEEP")
        print(f"========================================")
        print(f" * Validated Ground-Truth Cards: {len(self.reviewed_cards)}")
        print(f" * Unreviewed Target Cards:      {len(self.unreviewed_cards)}")
        print(f" * Active Classes Recognized:    {[c.capitalize() for c in self.known_classes]}")
        
        if not self.unreviewed_cards:
            print("\n[Notice] No unreviewed cards found in the dataset to estimate.")
            return

        print(f"\nRunning DNA estimation sweep across unreviewed cards...")
        
        results = []
        stats = {"fully_classified": 0, "class_only": 0, "unclassified": 0}

        for card in self.unreviewed_cards:
            pred = self.estimate_card(card)
            results.append((card, pred))
            
            if pred["class"] != "N/A" and pred["rank"] != "N/A":
                stats["fully_classified"] += 1
            elif pred["class"] != "N/A":
                stats["class_only"] += 1
            else:
                stats["unclassified"] += 1

        print(f"\n--- SWEEP SUMMARY ---")
        print(f" * Fully Classified (Class + Rank): {stats['fully_classified']}")
        print(f" * Partially Classified (Class Only): {stats['class_only']}")
        print(f" * Unclassified (N/A):             {stats['unclassified']}")
        
        print(f"\n--- SAMPLE PREDICTIONS ---")
        for card, pred in results[:15]:
            print(f" • {card.name} [{card.identity}] ➔ Class: {pred['class']} | Rank: {pred['rank']}")

    def autofill_database(self, target_class_filter=None, output_path=None):
        """
        Laser-focused autofill: ONLY targets cards already marked with the target class 
        (e.g., Draw) that are missing their ranks. Ignores completely blank cards.
        Tags processed cards with an 'M' suffix (e.g., DrawM) for human auditing.
        """
        if output_path is None:
            output_path = self.file_path

        print(f"\n========================================")
        print(f" 📦 MATOR TARGETED RANK FILLER - STARTING")
        if target_class_filter:
            print(f" 🎯 Target Class: [{target_class_filter.capitalize()}] (Missing Ranks Only)")
        print(f"========================================")
        
        updated_count = 0
        na_count = 0
        skipped_count = 0
        
        for idx, row in self.df.iterrows():
            c1 = str(row.get('Class 1') or row.get('Card Class 1') or '')
            c2 = str(row.get('Class 2') or row.get('Card Class 2') or '')
            r1 = str(row.get('Ranking 1') or row.get('Rank 1') or '')
            r2 = str(row.get('Ranking 2') or row.get('Rank 2') or '')
            
            target = target_class_filter.lower() if target_class_filter else ""
            
            # Define accepted targets (including the database typo)
            accepted_targets = [target]
            if target == "removal":
                accepted_targets.append("remvoal")
            
            # Safe trailing 'm' cleaner: only strips an 'm' if it's at the very end 
            # (leaving internal letters like the 'm' in re-m-o-v-a-l untouched)
            def clean_class(val):
                s = str(val).strip().lower()
                if s.endswith('m'):
                    return s[:-1]
                return s
            
            c1_clean = clean_class(c1)
            c2_clean = clean_class(c2)
            
            # 1. SCOPE: Must match the target class (or typo)
            is_in_target_class = (c1_clean in accepted_targets or c2_clean in accepted_targets)
            if not is_in_target_class:
                skipped_count += 1
                continue
            
            # 2. SAFETY: Skip if it already has a rank
            has_existing_rank = (r1.lower() not in ['none', 'nan', '']) or (r2.lower() not in ['none', 'nan', ''])
            if has_existing_rank:
                skipped_count += 1
                continue

            # 3. FULL JUDGMENT: Pass the card to estimate_card, which checks ALL known classes
            card_obj = self.cards[idx]
            prediction = self.estimate_card(card_obj)
            
            pred_class = prediction['class'] # Mator's true winner across all classes
            pred_rank = prediction['rank']

            if pred_class != "N/A" and pred_rank != "N/A":
                # Use Mator's actual judged class with the M-suffix (e.g., RemovalM, or even 
                # something else if Mator determines it fits another class better!)
                temp_class = f"{pred_class.capitalize()}M"
                self.df.at[idx, 'Class 1'] = temp_class
                self.df.at[idx, 'Ranking 1'] = pred_rank
                
                updated_count += 1
                print(f" ✨ [Judged & Tagged] {card_obj.name:<25} ➔ Class: {temp_class:<12} | Rank: {pred_rank}")
            else:
                # Fallback if Mator cannot classify it
                self.df.at[idx, 'Class 1'] = f"{target_class_filter.capitalize()}M"
                self.df.at[idx, 'Ranking 1'] = "N/A"
                na_count += 1
                print(f" 🛡️ [N/A Stamp] {card_obj.name:<25} (Could not determine classification)")

        # Save changes back to Excel
        try:
            self.df.to_excel(output_path, index=False)
            print(f"\n========================================")
            print(f" [Success] Targeted batch complete!")
            print(f" * Successfully Updated & Tagged: {updated_count}")
            print(f" * Explicitly Stamped N/A: {na_count}")
            print(f" * Skipped (Already Ranked / Other Class): {skipped_count}")
            print(f" * Saved to: {output_path}")
            print(f"========================================")
        except Exception as e:
            print(f"\n[Error] Failed to save Excel file: {e}")

if __name__ == "__main__":
    estimator = CardEstimator()
    
    # 🎯 Runs ONLY on existing Draw cards that are missing their ranks
    # estimator.autofill_database(target_class_filter="Removal")

if __name__ == "__main__":
    estimator = CardEstimator()
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
            
        # Search for the card (case-insensitive substring match)
        matches = [c for c in estimator.cards if c.name and card_name.lower() in c.name.lower()]
        
        if not matches:
            print(f"❌ Could not find any card matching '{card_name}' in the database.")
            continue
            
        for match in matches:
            print(f"\n--------------------------------------------------")
            print(f" Card Found: {match.name} [{match.identity}] (Mana: {match.raw_mana_val})")
            print(f"   * Actual Spreadsheet Data -> Class: {match.card_class_1} | Rank: {match.ranking_1_word}")
            
            # Run the DNA Estimator
            prediction = estimator.estimate_card(match)
            print(f"   * 🧬 DNA Estimator Guess  -> Class: {prediction['class']} | Rank: {prediction['rank']}")
            print(f"--------------------------------------------------")