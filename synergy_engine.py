import re
import logging
from collections import Counter
from auto_filler_words import AUTO_FILLER_WORDS
from Card_Filter import Card
from theme_engine import ThemeEngine

logger = logging.getLogger('cheepcards')

# Example usage in a login route or database block:
try:
    # Your database or logic here...
    logger.info("Database initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize database: %s", e)

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
    'townsfolk', 'wombat', 'vehicles', 'defender', 'hero', 'spacecraft',
    'necron', 'mounts', 'daleks', 'Time Lord', 'Astarte', 'Cybermen',
    'Symbiote',
}

def run_synergy_analysis(deck_list: list) -> dict:
    """
    POSTGRESQL-BACKED SYNERGY ENGINE.
    Evaluates card text loops in memory by querying SQLAlchemy instead of Excel files.
    """
    deck_size = len(deck_list)
    if deck_size == 0:
        return {}

    # Build reference maps directly from PostgreSQL via SQLAlchemy
    card_text_map = {}
    card_type_map = {}
    
    try:
        db_cards = Card.query.all()
        for c in db_cards:
            name = c.name.strip().lower()
            rules_text = c.oracle_text.lower() if c.oracle_text else ""
            card_type = c.raw_type.lower() if c.raw_type else ""
            if name:
                card_text_map[name] = rules_text
                card_type_map[name] = card_type
    except Exception as e:
        print(f"[Synergy Engine Error] Failed to fetch cards from database: {e}")
        return {"error": "Could not retrieve card data from database."}

    if not card_text_map:
        return {"error": "Card database is empty."}

    # 1. EXPANDED AGGRESSIVE FILLER LIST
    filler_words = AUTO_FILLER_WORDS

    core_categories = {
        "Card Draw": {
            "keywords": ["draw", "draws", "drawing"],
            "regex_patterns": [],
            "exclude_type": None,
            "cards": set(),
        },
        "Ramp & Land Velocity": {
            "keywords": [
                "ramp",
                "additional land",
                "basic land card, put it onto the battlefield",
                "put land",
            ],
            "regex_patterns": [
                r"\badd\s+(?:\{[wubrgc0-9xyz/]+\}|\bone\s+mana\b)",
                r"\bput\s+.*?land.*?\bonto the battlefield\b",
            ],
            "exclude_type": "land",
            "cards": set(),
        },
    }

    theme_engine = ThemeEngine()
    theme_card_pools = {theme: set() for theme in theme_engine.theme_rules.keys()}

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

            matched = False
            for kw in tracking.get("keywords", []):
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, rules_text, re.IGNORECASE):
                    tracking["cards"].add(actual_name_in_excel)
                    matched = True
                    break

            if not matched:
                for reg in tracking.get("regex_patterns", []):
                    if re.search(reg, rules_text, re.IGNORECASE):
                        tracking["cards"].add(actual_name_in_excel)
                        break

        # 2. READ CREATURE TYPE SUBTYPES DIRECTLY FROM TYPE COLUMN
        clean_types = re.sub(r'[^\w\s]', ' ', current_card_type)
        for sub_type in clean_types.split():
            if sub_type in PROTECTED_TYPES:
                creature_type_pool.append(sub_type)
                card_creature_type_assignments[card_name.strip()].append(sub_type)

        # 3. PROCESS THE REMAINING DYNAMIC THEMES
        clean_text = re.sub(r'[^\w\s{}]', ' ', rules_text)
        words = [w for w in clean_text.split() if len(w) > 2]

        for theme in theme_card_pools.keys():
            if theme_engine.evaluate_card_for_theme(theme, rules_text, current_card_type):
                theme_card_pools[theme].add(actual_name_in_excel)

        for word in set(words):
            if word not in filler_words and word not in PROTECTED_TYPES:
                raw_theme_pool.append(word)
                card_assignments[card_name.strip()].append(word)

    MIN_MATCHES = 5
    
    theme_counts = Counter(raw_theme_pool)
    valid_themes = {theme: count for theme, count in theme_counts.items() if count >= MIN_MATCHES}
   
    creature_type_counts = Counter(creature_type_pool)
    valid_creature_types = {type_name: count for type_name, count in creature_type_counts.items() if count >= MIN_MATCHES}

    output = []
    
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

    for type_name, count in sorted(valid_creature_types.items(), key=lambda item: item[1], reverse=True):
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

    major_themes_formatted = []
    for theme, cards_set in theme_card_pools.items():
        count = len(cards_set)
        if count >= 8:
            percentage = round((count / deck_size) * 100, 2)
            matching_cards = sorted(list(cards_set))
            
            major_themes_formatted.append({
                "theme": f"🔮 {theme}",
                "count": count,
                "percentage": f"{percentage}%",
                "cards": ", ".join(matching_cards)
            })
            
    for theme_data in sorted(major_themes_formatted, key=lambda x: x["count"], reverse=True):
        output.append(theme_data)

    for theme, count in sorted(valid_themes.items(), key=lambda item: item[1], reverse=True):
        if theme in ["draw", "land", "lands"]:
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


