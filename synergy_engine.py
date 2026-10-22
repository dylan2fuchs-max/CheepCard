import re
import logging
from collections import Counter
from auto_filler_words import AUTO_FILLER_WORDS
from Card_Filter import Card
from theme_engine import ThemeEngine

logger = logging.getLogger('cheepcards')

try:
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

    filler_words = AUTO_FILLER_WORDS
    theme_engine = ThemeEngine()

    core_pools = {
        "Card Draw": set(),
        "Ramp": set(),
        "Land": set(),
        "Removal": set(),
        "Board Wipes": set()
    }

    theme_card_pools = {theme: set() for theme in theme_engine.theme_rules.keys()}
    raw_theme_pool = []
    
    # Use clean lookup keys for assignments
    def clean_key(name):
        return re.sub(r'[^a-z0-9]', '', str(name).lower())

    card_assignments = {clean_key(card): [] for card in deck_list if card.strip()}
    creature_type_pool = []
    card_creature_type_assignments = {clean_key(card): [] for card in deck_list if card.strip()}

    for card_name in deck_list:
        clean_input_name = re.sub(r'^\d+x?\s*', '', str(card_name)).strip().lower()
        if not clean_input_name:
            continue
            
        matched_card_obj = None
        actual_name = clean_input_name.title()
        
        if clean_input_name in card_db_map:
            matched_card_obj = card_db_map[clean_input_name]
            actual_name = matched_card_obj.name.title()
        else:
            for db_name, c_obj in card_db_map.items():
                if clean_input_name in db_name or db_name in clean_input_name:
                    matched_card_obj = c_obj
                    actual_name = db_name.title()
                    break

        if not matched_card_obj:
            continue

        rules_text = matched_card_obj.oracle_text.lower() if matched_card_obj.oracle_text else ""
        current_card_type = matched_card_obj.raw_type.lower() if matched_card_obj.raw_type else ""
        
        # 1. Check Card_Filter classes
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

        # 2. Extract Creature Subtypes automatically from official type lines (everything after em-dash)
        if current_card_type:
            parts = re.split(r'[—–-]', current_card_type, maxsplit=1)
            if len(parts) > 1:
                subtype_part = parts[1].strip()
                subtypes = re.findall(r'\b[a-zA-Z]+\b', subtype_part)
                for sub_type in subtypes:
                    sub_lower = sub_type.lower()
                    if sub_lower not in {'legendary', 'world', 'ongoing', 'snow', 'artifact', 'creature', 'enchantment', 'land', 'planeswalker'}:
                        creature_type_pool.append(sub_lower)
                        ck = clean_key(actual_name)
                        if sub_lower not in card_creature_type_assignments.setdefault(ck, []):
                            card_creature_type_assignments[ck].append(sub_lower)

        # 3. Process ThemeEngine Rules
        for theme in theme_card_pools.keys():
            if theme_engine.evaluate_card_for_theme(theme, rules_text, current_card_type):
                theme_card_pools[theme].add(actual_name)

        # 4. Fallback dynamic word mining
        clean_text = re.sub(r'[^\w\s{}]', ' ', rules_text)
        words = [w for w in clean_text.split() if len(w) > 2]
        for word in set(words):
            if word not in filler_words and word not in PROTECTED_TYPES:
                raw_theme_pool.append(word)
                ck = clean_key(actual_name)
                card_assignments.setdefault(ck, []).append(word)

    MIN_MATCHES = 10
    theme_counts = Counter(raw_theme_pool)
    valid_themes = {theme: count for theme, count in theme_counts.items() if count >= MIN_MATCHES}
   
    MIN_CREATURE_MATCHES = 8
    creature_type_counts = Counter(creature_type_pool)
    valid_creature_types = {type_name: count for type_name, count in creature_type_counts.items() if count >= MIN_CREATURE_MATCHES}

    output = []
    
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
    
    top_creature_types = sorted(valid_creature_types.items(), key=lambda item: item[1], reverse=True)[:3]

    for type_name, count in top_creature_types:
        matching_cards = []
        for card in deck_list:
            clean_c_input = re.sub(r'^\d+x?\s*', '', str(card)).strip().lower()
            db_obj = card_db_map.get(clean_c_input)
            c_disp = db_obj.name.title() if db_obj else clean_c_input.title()
            ck = clean_key(c_disp)
            if type_name in card_creature_type_assignments.get(ck, []):
                if c_disp not in matching_cards:
                    matching_cards.append(c_disp)
                
        output.append({
            "theme": f"👾 {type_name.capitalize()} (Creature Subtype)",
            "count": len(matching_cards),
            "percentage": f"{round((len(matching_cards) / deck_size) * 100, 2)}%",
            "cards": ", ".join(sorted(matching_cards))
        })

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
    
    # Build clean card_theme_mapping using clean_key()
    card_theme_mapping = {}

    for cat_name, cards_set in core_pools.items():
        for card in cards_set:
            k = clean_key(card)
            if k:
                if k not in card_theme_mapping:
                    card_theme_mapping[k] = []
                if cat_name not in card_theme_mapping[k]:
                    card_theme_mapping[k].append(cat_name)

    for type_name, count in top_creature_types:
        theme_display = f"{type_name.capitalize()} (Creature Subtype)"
        for card in deck_list:
            clean_c_input = re.sub(r'^\d+x?\s*', '', str(card)).strip().lower()
            db_obj = card_db_map.get(clean_c_input)
            c_name = db_obj.name.title() if db_obj else clean_c_input.title()
            k = clean_key(c_name)
            if type_name in card_creature_type_assignments.get(k, []):
                if k not in card_theme_mapping:
                    card_theme_mapping[k] = []
                if theme_display not in card_theme_mapping[k]:
                    card_theme_mapping[k].append(theme_display)

    for theme, cards_set in theme_card_pools.items():
        if len(cards_set) >= 8:
            for card in cards_set:
                k = clean_key(card)
                if k:
                    if k not in card_theme_mapping:
                        card_theme_mapping[k] = []
                    if theme not in card_theme_mapping[k]:
                        card_theme_mapping[k].append(theme)

    return {
        "deck_size": deck_size, 
        "themes": output,
        "card_theme_mapping": card_theme_mapping
    }