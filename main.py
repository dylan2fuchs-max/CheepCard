# main.py
import pandas as pd
from Excel_Manager import ExcelManager

def run_qa_search_engine(manager):
    print("\n=== CheepCard Magic Deck-Building System ===")
    
    # 1. Limit Rule for Mechanic Class
    VALID_CLASSES = ["draw", "ramp", "removal", "boardwipe", "land"]
    while True:
        print("\n Please select a value or card type you need.")
        print(f"Options: {', '.join([c.capitalize() for c in VALID_CLASSES])}")
        target_class = input("Your choice: ").strip().lower()
        
        if target_class in VALID_CLASSES:
            break
        print(f"❌ INVALID CHOICE. Please choose exactly from: {', '.join(VALID_CLASSES)}")

    # 2. Limit Rule for Color Identity
    VALID_COLORS = {"w": "{W}", "u": "{U}", "b": "{B}", "r": "{R}", "g": "{G}"}
    while True:
        print("\n What color identity should these cards have?")
        print("Options: W (White), U (Blue), B (Black), R (Red), G (Green) [Or press Enter for Any]")
        raw_color = input("Your choice: ").strip().lower()
        
        if raw_color == "":  # Force clear None if skipped
            target_color = None
            break
        if raw_color in VALID_COLORS:
            target_color = VALID_COLORS[raw_color]
            break
        print("❌ INVALID COLOR. Please choose W, U, B, R, G, or press Enter.")

    # 3. Limit Rule for Budget Constraints
    while True:
        print("\n Budget: What is the maximum price you want to pay per card?")
        price_input = input("Enter max price (e.g., 2.50 or press Enter for no limit): ").strip()
        
        if not price_input:
            max_price = float('inf')
            break
            
        clean_price = price_input.replace('$', '').strip()
        if clean_price.replace('.', '', 1).isdigit():
            max_price = float(clean_price)
            if max_price >= 0:
                break
        print("❌ INVALID BUDGET. Please enter a valid positive number (e.g., 5.00).")

    # 4. Limit Rule for Priority Choices
    while True:
        print("\n What is your priority rule for determining the 'Best' cards?")
        print("1: Quality First (Sort by highest Ranking, then lowest Price)")
        print("2: Budget First  (Sort by lowest Price, then highest Ranking)")
        priority_choice = input("Select priority (1 or 2): ").strip()
        
        if priority_choice in ["1", "2"]:
            break
        print("❌ INVALID SELECTION. Please enter exactly '1' or '2'.")

    # --- EXECUTION ENGINE ---
    print(f"\nProcessing rules for {target_class.upper()}...")
    
    # 1. Fetch records adaptively from ExcelManager
    if target_class == "land":
        raw_results = manager.find_cards_by_value("Type", "Land")
    else:
        raw_results = manager.find_cards_by_value("Class", target_class)

    # 2. De-duplicate any instances
    unique_cards = {card.name: card for card in raw_results}.values()

    # 3. Apply custom filters (Color & Price)
    filtered_list = []
    color_drops = 0
    price_drops = 0
    
    for card in unique_cards:
        if target_color and str(target_color).strip():
            if card.identity != target_color:
                color_drops += 1
                continue
                
        if card.price > max_price:
            price_drops += 1
            continue
            
        filtered_list.append(card)

    # Clean Diagnostic Report & Debug output
    print(f"\n🔍 DEBUG VALUE: target_color is currently equal to: '{target_color}' (Type: {type(target_color)})")
    print(f"\n[Diagnostic Report]:")
    print(f"-> Total raw cards pulled from Excel: {len(unique_cards)}")
    print(f"-> Cards filtered out by Color mismatch: {color_drops}")
    print(f"-> Cards filtered out by Budget limit: {price_drops}")
    print(f"-> Cards remaining for the Top 10 list: {len(filtered_list)}\n")

    # 4. Apply the Sorting Algorithm based on the User's choice
    if priority_choice == "2":
        filtered_list.sort(key=lambda c: (c.price, -c.ranking_1_value))
    else:
        filtered_list.sort(key=lambda c: (-c.ranking_1_value, c.price))

    # 5. Display the Top 10 Results using list slicing [:10]
    print(f"\n🏆 Top 10 Best '{target_class.capitalize()}' Cards matching your rules:")
    print("=" * 60)
    
    if not filtered_list:
        print("No cards found matching all specified filters.")
    else:
        for idx, card in enumerate(filtered_list[:10], start=1):
            print(f"{idx}. {card.name:<25} Price: ${card.price:<6.2f} | Rank: {card.ranking_1_word.capitalize()}")
            
    print("=" * 60)


def main():
    print("Initializing Magic Card Database...")
    try:
        manager = ExcelManager()
        print("Database loaded successfully!\n")
    except Exception as e:
        print(f"Initialization Error: {e}")
        return

    run_qa_search_engine(manager)

if __name__ == "__main__":
    main()

