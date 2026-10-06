import sys
import os
import pandas as pd

# Add the parent directory (CheepCards root) to Python's search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db
from Card_Filter import Card

def sync_excel_to_postgres(excel_path="../Magic Card Data Base Current View.xlsx"):
    print(f"📖 Reading spreadsheet from: {os.path.abspath(excel_path)}")
    
    if not os.path.exists(excel_path):
        print(f"❌ Error: Could not find Excel file at {os.path.abspath(excel_path)}")
        return

    df = pd.read_excel(excel_path, engine="openpyxl")
    df = df.fillna("")
    
    print(f"🔄 Processing {len(df)} cards into PostgreSQL...")
    
    with app.app_context():
        # Creates the 'cards' table in PostgreSQL if it doesn't exist yet
        db.create_all()
        
        success_count = 0
        update_count = 0
        
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            name = str(row_dict.get('Name') or row_dict.get('name') or "").strip()
            if not name:
                continue
                
            identity = str(row_dict.get('Colors') or row_dict.get('Identity') or row_dict.get('identity') or "{COLORLESS}")
            mana_cost = str(row_dict.get('Mana Value') or row_dict.get('Mana Cost') or row_dict.get('mana_cost') or "{0}")
            raw_type = str(row_dict.get('Type') or row_dict.get('Type Line') or '')
            price = row_dict.get('Price', 0.0)
            
            c1 = str(row_dict.get('Class 1') or row_dict.get('Card Class 1') or 'none')
            c2 = str(row_dict.get('Class 2') or row_dict.get('Card Class 2') or 'none')
            r1 = str(row_dict.get('Ranking 1') or row_dict.get('Rank 1') or 'none')
            r2 = str(row_dict.get('Ranking 2') or row_dict.get('Rank 2') or 'none')
            rarity = str(row_dict.get('Rarity', 'Common'))
            image_url = str(row_dict.get('Image URL', ''))
            oracle_text = str(row_dict.get('Text') or row_dict.get('Oracle Text') or '')
            
            # Check if card already exists in database by name
            existing_card = Card.query.filter_by(_name=name).first()
            
            if existing_card:
                existing_card.identity = identity
                existing_card.mana_cost = mana_cost
                existing_card.raw_type = raw_type
                existing_card.price = price
                existing_card.card_class_1 = c1
                existing_card.card_class_2 = c2
                existing_card.ranking_1_word = r1
                existing_card.ranking_2_word = r2
                existing_card.rarity = rarity
                existing_card.image_url = image_url
                existing_card.oracle_text = oracle_text
                update_count += 1
            else:
                new_card = Card(
                    name=name,
                    identity=identity,
                    mana_cost=mana_cost,
                    price=price,
                    ranking_1=r1,
                    ranking_2=r2,
                    card_class_1=c1,
                    card_class_2=c2,
                    rarity=rarity,
                    image_url=image_url,
                    oracle_text=oracle_text
                )
                new_card.raw_type = raw_type
                db.session.add(new_card)
                success_count += 1
                
        db.session.commit()
        print(f"🎉 Sync Complete! Inserted {success_count} new cards, updated {update_count} existing cards.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Optional: Automatically seed from your uploaded excel file on startup if database is empty
        if Card.query.count() == 0:
            print("Database is empty. Seeding from Excel...")
            # Call your import logic here if desired