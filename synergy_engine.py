from pathlib import Path
import pandas as pd
import re
from collections import Counter
from auto_filler_words import AUTO_FILLER_WORDS 

# STRICTLY READ-ONLY REFERENCE PATH
EXCEL_PATH = Path.cwd() / "Magic Card Data Base Current View.xlsx"

PROTECTED_TYPES = {
    'human', 'wizard', 'warrior', 'soldier', 'spirit', 'zombie', 'cleric',
    'elemental', 'elf', 'shaman', 'beast', 'goblin', 'rogue', 'knight',
    'vampire', 'bird', 'dragon', 'druid', 'horror', 'merfolk', 'cat',
    'phyrexian', 'angel', 'giant', 'insect', 'construct', 'scout', 'artificer',
    'demon', 'werewolf', 'wall', 'eldrazi', 'golem', 'dinosaur', 'shapeshifter',
    'pirate', 'ogre', 'berserker', 'sliver', 'snake', 'monk', 'dog',
    'faerie', 'dwarf', 'wurm', 'minotaur', 'ally', 'treefolk', 'archer',
    'drake', 'illusion', 'avatar', 'advisor', 'kor', 'orc', 'wolf',
    'assassin', 'lizard', 'sphinx', 'spider', 'nightmare', 'warlock', 'centaur',
    'elephant', 'noble', 'rat', 'samurai', 'skeleton', 'drone', 'vedalken',
    'kithkin', 'plant', 'hydra', 'spellshaper', 'djinn', 'mutant', 'adventure',
    'fungus', 'god', 'viashino', 'griffin', 'rebel', 'troll', 'devil',
    'rhino', 'kavu', 'serpent', 'dryad', 'ninja', 'boar', 'mercenary',
    'ranger', 'barbarian', 'horse', 'imp', 'minion', 'ooze', 'fox', 'fish', 
    'naga', 'myr', 'frog', 'scarecrow', 'elder', 'bear', 'crab', 'gargoyle', 
    'phoenix', 'shade', 'turtle', 'ape', 'citizen', 'cyclops', 'nomad', 'satyr', 
    'crocodile', 'unicorn', 'bat', 'efreet', 'specter', 'elk', 'kraken', 
    'cephalid', 'jackal', 'moonfolk', 'thrull', 'saga', 'homunculus', 'leviathan', 
    'chimera', 'hellion', 'peasant', 'host', 'pegasus', 'archon', 'gorgon', 
    'gnome', 'incarnation', 'nymph', 'juggernaut', 'ox', 'siren', 'aetherborn', 
    'leech', 'tiefling', 'bard', 'rigger', 'jellyfish', 'ouphe', 'scorpion', 
    'thopter', 'cyborg', 'kobold', 'pilot', 'salamander', 'squirrel', 'whale', 
    'atog', 'basilisk', 'goat', 'lhurgoyf', 'licid', 'manticore', 'monkey', 
    'nightstalker', 'octopus', 'yeti', 'antelope', 'dauthi', 'harpy', 'kirin', 
    'praetor', 'processor', 'spike', 'egg', 'gremlin', 'hag', 'shark', 'slug', 
    'soltari', 'weird', 'camel', 'hippogriff', 'spy', 'worm', 'azra', 'halfling', 
    'homarid', 'metathran', 'wolverine', 'assembly-worker', 'badger', 'beholder',
    'mystic', 'squid', 'thalakos', 'zubera', 'donkey', 'eye', 'gamer', 'hippo',
    'rabbit', 'shrine', 'slith', 'bringer', 'carrier', 'demigod', 'hyena',
    'manticore', 'monger', 'nephilim', 'pangolin', 'villain', 'volver', 'wraith',
    'aurochs', 'beeble', 'clamfolk', 'killbot', 'noggle', 'orgg', 'surrakar',
    'trilobite', 'alicorn', 'brainiac', 'brushwagg', 'child', 'cockatrice',
    'gnoll', 'mole', 'mongoose', 'otter', 'raccoon', 'sheep', 'starfish',
    'autobot', 'bureaucrat', 'cow', 'flagbearer', 'gith', 'lamia', 'lammasu',
    'lobster', 'nautilus', 'pest', 'phelddagrif', 'scientist', 'sponge',
    'townsfolk', 'wombat'
}

def run_synergy_analysis(deck_list: list) -> dict:
    """
    STRICTLY READ-ONLY ARCHITECTURE ENGINE.
    Evaluates card text loops in memory. Contains ZERO file-write mechanisms.
    """
    if not EXCEL_PATH.exists():
        return {"error": "Spreadsheet database file not found."}
        
    # Read the sheet safely in memory
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df.columns = df.columns.str.strip()
    
    text_col = "Text" if "Text" in df.columns else "Rules Text"
    type_col = "Type" if "Type" in df.columns else "Card Type"
    
    # Build two reference dictionaries mapping card names to their text and type configurations
    card_text_map = {}
    card_type_map = {}
    
    for _, row in df.iterrows():
        name = str(row.get("Name", "")).strip().lower()
        rules_text = str(row.get(text_col, "")).lower() if pd.notna(row.get(text_col)) else ""
        card_type = str(row.get(type_col, "")).lower() if pd.notna(row.get(type_col)) else ""
        
        if name:
            card_text_map[name] = rules_text
            card_type_map[name] = card_type

    # 1. EXPANDED AGGRESSIVE FILLER LIST
    filler_words = AUTO_FILLER_WORDS

    deck_size = len(deck_list)
    if deck_size == 0:
        return {}

    # Setup tracking variables for our primary website dashboard pillars
    core_categories = {
        "Card Draw": {"keywords": ["draw", "draws", "drawing"], "exclude_type": None, "cards": set()},
        "Ramp & Land Velocity": {"keywords": ["ramp", "add one mana", "additional land", "basic land card, put it onto the battlefield", "put land", "add {w}", "add {g}", "add {r}", "add {u}", "add {b}", "add {c}"], "exclude_type": "land", "cards": set()},
    }

    raw_theme_pool = []
    card_assignments = {card.strip(): [] for card in deck_list if card.strip()}
    
    # Track physical creature types directly from your type column map
    creature_type_pool = []
    card_creature_type_assignments = {card.strip(): [] for card in deck_list if card.strip()}

    for card_name in deck_list:
        raw_string = str(card_name).strip().lower()
        if not raw_string:
            continue
            
        rules_text = ""
        current_card_type = ""
        actual_name_in_excel = card_name.strip()
        
        if raw_string in card_text_map:
            rules_text = card_text_map[raw_string]
            current_card_type = card_type_map[raw_string]
        else:
            for excel_name, text_content in card_text_map.items():
                if raw_string in excel_name or excel_name in raw_string:
                    rules_text = text_content
                    current_card_type = card_type_map[excel_name]
                    actual_name_in_excel = excel_name.title()
                    break

        if not rules_text:
            continue

        # 1. PROCESS CORE THEMES
        for cat_name, tracking in core_categories.items():
            exclude_param = tracking.get("exclude_type")
            if exclude_param and exclude_param in current_card_type:
                continue
            for kw in tracking.get("keywords", []):
                if kw in rules_text:
                    tracking["cards"].add(actual_name_in_excel)

        # 2. READ CREATURE TYPE SUBTYPES DIRECTLY FROM SPREADSHEET TYPE COLUMN
        clean_types = re.sub(r'[^\w\s]', ' ', current_card_type)
        for sub_type in clean_types.split():
            # If the word in the type column is in our list, track it as an explicit creature type match
            if sub_type in PROTECTED_TYPES:
                creature_type_pool.append(sub_type)
                card_creature_type_assignments[card_name.strip()].append(sub_type)

        # 3. PROCESS THE REMAINING DYNAMIC THEMES
        clean_text = re.sub(r'[^\w\s{}]', ' ', rules_text)
        words = [w for w in clean_text.split() if len(w) > 2]

        for word in set(words):
            if word not in filler_words and word not in PROTECTED_TYPES:
                raw_theme_pool.append(word)
                card_assignments[card_name.strip()].append(word)

    # Calculate dynamic themes and creature types that appear at least 4 times
    MIN_MATCHES = 4
    
    theme_counts = Counter(raw_theme_pool)
    valid_themes = {theme: count for theme, count in theme_counts.items() if count >= MIN_MATCHES}
    
    creature_type_counts = Counter(creature_type_pool)
    valid_creature_types = {type_name: count for type_name, count in creature_type_counts.items() if count >= MIN_MATCHES}

    output = []
    
    # 1. Append custom categories to the top of the table report
    for cat_name, tracking in core_categories.items():
        count = len(tracking["cards"])
        if count > 0:
            percentage = round((count / deck_size) * 100, 2)
            output.append({
                "theme": f"📊 {cat_name}",
                "count": count,
                "percentage": f"{percentage}%",
                "cards": ", ".join(sorted(list(tracking["cards"])))
            })

    # 2. Append the True Creature Type matches next with our FUN MEME ALIEN SYMBOL
    for type_name, count in sorted(valid_creature_types.items(), key=lambda item: item, reverse=True):
        percentage = round((count / deck_size) * 100, 2)
        matching_cards = []
        for card in deck_list:
            if type_name in card_creature_type_assignments.get(card.strip(), []):
                matching_cards.append(card.strip())
                
        output.append({
            "theme": f"👾 {type_name.capitalize()} (Creature Subtype)",
            "count": count,
            "percentage": f"{percentage}%",
            "cards": ", ".join(matching_cards)
        })

    # 3. Append the secondary organic word topics underneath
    for theme, count in sorted(valid_themes.items(), key=lambda item: item, reverse=True):
        if theme in ["draw", "life", "land", "lands"]:
            continue
            
        percentage = round((count / deck_size) * 100, 2)
        matching_cards = []
        for card in deck_list:
            if theme in card_assignments.get(card.strip(), []):
                matching_cards.append(card.strip())
                
        output.append({
            "theme": theme.capitalize(),
            "count": count,
            "percentage": f"{percentage}%",
            "cards": ", ".join(matching_cards)
        })
        
    return {"deck_size": deck_size, "themes": output}


