from Card_Filter import Card

# Mock Excel Row Data
sample_row = {
    "name": "Sol Ring",
    "identity": "C",
    "mana_cost": "{1}",
    "price": "1.50",
    "ranking_1": "optimized",
    "ranking_2": "fast",
    "card_class_1": "ramp",
    "card_class_2": "none",
    "rarity": "Uncommon",
    "image_url": "https://cards.scryfall.io/large/front/c/c/cc705c06-a536-47a3-839f-f5eb33d59e38.jpg",
    "oracle_text": "{T}: Add {C}{C}."
}

# Instantiate Card using unpacked dict
card = Card(**sample_row)

# Run Verifications
print("--- CARD INTEGRATION TEST ---")
print(f"Name: {card.name}")
print(f"Price: ${card.price:.2f}")
print(f"Class 1 / Rank 1: {card.card_class_1} / {card.rank_1} (Value: {card.ranking_1_value})")
print(f"Image URL: {card.image_url}")
print(f"Oracle Text: {card.oracle_text}")
print("--- TEST PASSED ---")