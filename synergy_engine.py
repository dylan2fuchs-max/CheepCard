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
    Evaluates card text loops in memory by querying SQLAlchemy and separating core categories.
    """
    deck_size = len(deck_list)
    if deck_size == 0:
        return {}

    card_db_map = {}
    
    try:
        db_cards = Card.query.all()
        for c in db_cards:
            name = c.name.strip().lower()
            if name:
                card_db_map[name] = c
    except Exception as e:
        print(f"[Synergy Engine Error] Failed to fetch cards from database: {e}")
        return {"error": "Could not retrieve card data from database."}

    if not card_db_map:
        return {"error": "Card database is empty."}

    # 1. EXPANDED AGGRESSIVE FILLER LIST
    filler_words = AUTO_FILLER_WORDS
    theme_engine = ThemeEngine()

    # Track core category card pools separately
    core_pools = {
        "Card Draw": set(),
        "Ramp": set(),
        "Land": set(),
        "Removal": set(),
        "Board Wipes": set()
    }

    theme_card_pools = {theme: set() for theme in theme_engine.theme_rules.keys()}
    raw_theme_pool = []
    card_assignments = {card.strip(): [] for card in deck_list if card.strip()}
    
    creature_type_pool = []
    card_creature_type_assignments = {card.strip(): [] for card in deck_list if card.strip()}
    card_theme_mapping = {}

    for card_name in deck_list:
        raw_string = str(card_name).strip().lower()
        if not raw_string:
            continue
            
        matched_card_obj = None
        actual_name = card_name.strip()
        
        if raw_string in card_db_map:
            matched_card_obj = card_db_map[raw_string]
            actual_name = matched_card_obj.name.title()
        else:
            for db_name, c_obj in card_db_map.items():
                if raw_string in db_name or db_name in raw_string:
                    matched_card_obj = c_obj
                    actual_name = db_name.title()
                    break

        if not matched_card_obj:
            continue

        rules_text = matched_card_obj.oracle_text.lower() if matched_card_obj.oracle_text else ""
        current_card_type = matched_card_obj.raw_type.lower() if matched_card_obj.raw_type else ""
        
        # 1. Check Card_Filter classes (card_class_1, card_class_2)
        c1 = matched_card_obj.card_class_1.lower()
        c2 = matched_card_obj.card_class_2.lower()
        
        assigned_classes = [c1, c2]
        
        if "draw" in assigned_classes or matched_card_obj.serves_purpose("draw"):
            core_pools["Card Draw"].add(actual_name)
        if "ramp" in assigned_classes or matched_card_obj.serves_purpose("ramp"):
            core_pools["Ramp"].add(actual_name)
        if "land" in assigned_classes or matched_card_obj.serves_purpose("land") or "land" in current_card_type:
            core_pools["Land"].add(actual_name)
        if "removal" in assigned_classes or matched_card_obj.serves_purpose("removal"):
            core_pools["Removal"].add(actual_name)
        if "board wipe" in assigned_classes or matched_card_obj.serves_purpose("board wipe"):
            core_pools["Board Wipes"].add(actual_name)

        # 2. Extract Creature Subtypes (e.g., Party, Wizard, Cleric, Rogue, Warrior)
        clean_types = re.sub(r'[^\w\s]', ' ', current_card_type)
        for sub_type in clean_types.split():
            sub_lower = sub_type.lower()
            if sub_lower in PROTECTED_TYPES:
                creature_type_pool.append(sub_lower)
                card_creature_type_assignments[card_name.strip()].append(sub_lower)

        # 3. Process ThemeEngine Rules
        card_themes_matched = []
        for theme in theme_card_pools.keys():
            if theme_engine.evaluate_card_for_theme(theme, rules_text, current_card_type):
                theme_card_pools[theme].add(actual_name)
                card_themes_matched.append(theme)

        # Also register core classes as themes for export mapping
        for c_name, p_set in core_pools.items():
            if actual_name in p_set:
                card_themes_matched.append(c_name)

        card_theme_mapping[actual_name.lower()] = card_themes_matched

        # 4. Fallback dynamic word mining
        clean_text = re.sub(r'[^\w\s{}]', ' ', rules_text)
        words = [w for w in clean_text.split() if len(w) > 2]
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
    
    # Append core categories (Card Draw, Ramp, Land, Removal, Board Wipes)
    for cat_name, cards_set in core_pools.items():
        count = len(cards_set)
        if count > 0:
            percentage = round((count / deck_size) * 100, 2)
            output.append({
                "theme": f"📊 {cat_name}",
                "count": count,
                "percentage": f"{percentage}%",
                "cards": ", ".join(sorted(list(cards_set)))
            })

    # Append valid creature subtypes (e.g. Party members, elves, etc.)
    for type_name, count in sorted(valid_creature_types.items(), key=lambda item: item[1], reverse=True):
        percentage = round((count / deck_size) * 100, 2)
        matching_cards = []
        for card in deck_list:
            if type_name in card_creature_type_assignments.get(card.strip(), []):
                db_obj = card_db_map.get(card.strip().lower())
                card_display_name = db_obj.name.title() if db_obj else card.strip()
                if card_display_name not in matching_cards:
                    matching_cards.append(card_display_name)
                
        output.append({
            "theme": f"👾 {type_name.capitalize()} (Creature Subtype)",
            "count": len(matching_cards),
            "percentage": f"{round((len(matching_cards) / deck_size) * 100, 2)}%",
            "cards": ", ".join(sorted(matching_cards))
        })

    # Append ThemeEngine themes
    major_themes_formatted = []
    for theme, cards_set in theme_card_pools.items():
        count = len(cards_set)
        if count >= 8:
            percentage = round((count / deck_size) * 100, 2)
            major_themes_formatted.append({
                "theme": f"🔮 {theme}",
                "count": count,
                "percentage": f"{percentage}%",
                "cards": ", ".join(sorted(list(cards_set)))
            })
            
    for theme_data in sorted(major_themes_formatted, key=lambda x: x["count"], reverse=True):
        output.append(theme_data)
    
    # After computing all pools in run_synergy_analysis, build card_theme_mapping robustly:
    card_theme_mapping = {}

    def clean_key(name):
        return re.sub(r'[^a-z0-9]', '', str(name).lower())

    # 1. Map Core Pools
    for cat_name, cards_set in core_pools.items():
        for card in cards_set:
            key = card.strip().lower()
            if key not in card_theme_mapping:
                card_theme_mapping[key] = []
            if cat_name not in card_theme_mapping[key]:
                card_theme_mapping[key].append(cat_name)

    # 2. Map Creature Subtypes
    for type_name, count in valid_creature_types.items():
        theme_display = f"{type_name.capitalize()} (Creature Subtype)"
        for card in deck_list:
            if type_name in card_creature_type_assignments.get(card.strip(), []):
                db_obj = card_db_map.get(card.strip().lower())
                card_name = db_obj.name.title() if db_obj else card.strip()
                key = card_name.lower()
                if key not in card_theme_mapping:
                    card_theme_mapping[key] = []
                if theme_display not in card_theme_mapping[key]:
                    card_theme_mapping[key].append(theme_display)

    # 3. Map ThemeEngine Themes (>= 8 count)
    for theme, cards_set in theme_card_pools.items():
        if len(cards_set) >= 8:
            for card in cards_set:
                key = card.strip().lower()
                if key not in card_theme_mapping:
                    card_theme_mapping[key] = []
                if theme not in card_theme_mapping[key]:
                    card_theme_mapping[key].append(theme)

    return {
        "deck_size": deck_size, 
        "themes": output,
        "card_theme_mapping": card_theme_mapping
    }


