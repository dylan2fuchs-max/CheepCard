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

def clean_key(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower())

def run_synergy_analysis(deck_list: list) -> dict:
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
    
    def get_clean_card_key(c_str):
        name_only = re.sub(r'^\d+x?\s*', '', str(c_str)).strip()
        return re.sub(r'[^a-z0-9]', '', name_only.lower())

    card_assignments = {clean_key(card): [] for card in deck_list if card.strip()}
    creature_type_pool = []
    card_creature_type_assignments = {get_clean_card_key(card): [] for card in deck_list if card.strip()}

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
        current_card_type = str(matched_card_obj.raw_type).lower() if matched_card_obj.raw_type else ""

        combined_text_for_types = f"{current_card_type} {rules_text}"
        
        subtypes_source = current_card_type
        if '—' in current_card_type:
            subtypes_source = current_card_type.split('—')[-1]
        elif '-' in current_card_type:
            subtypes_source = current_card_type.split('-')[-1]

        subtypes = set(re.findall(r'\b[a-zA-Z]+\b', subtypes_source))
        
        if "skeleton" in combined_text_for_types:
            subtypes.add("skeleton")

        exclude_type_words = {
            'legendary', 'world', 'ongoing', 'snow', 'artifact', 'creature', 
            'enchantment', 'land', 'planeswalker', 'instant', 'sorcery', 
            'token', 'equipment', 'aura', 'vehicle', 'tribal', 'kindred', 'basic',
            'battle', 'conspiracy', 'phenomenon', 'plane', 'scheme', 'card'
        }
        
        ck = get_clean_card_key(actual_name)
        for sub in subtypes:
            sub_lower = sub.lower()
            if len(sub_lower) > 2 and sub_lower not in exclude_type_words:
                creature_type_pool.append(sub_lower)
                if sub_lower not in card_creature_type_assignments.setdefault(ck, []):
                    card_creature_type_assignments[ck].append(sub_lower)
        
        c1 = matched_card_obj.card_class_1.lower() if matched_card_obj.card_class_1 else ""
        c2 = matched_card_obj.card_class_2.lower() if matched_card_obj.card_class_2 else ""
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

        for theme in theme_card_pools.keys():
            if theme_engine.evaluate_card_for_theme(theme, rules_text, current_card_type):
                theme_card_pools[theme].add(actual_name)

        clean_text = re.sub(r'[^\w\s{}]', ' ', rules_text)
        words = [w for w in clean_text.split() if len(w) > 2]
        for word in set(words):
            if word not in filler_words and word not in PROTECTED_TYPES:
                raw_theme_pool.append(word)
                ck = clean_key(actual_name)
                card_assignments.setdefault(ck, []).append(word)

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
    
    creature_type_counts = Counter(creature_type_pool)
    top_creature_types = creature_type_counts.most_common(2)

    for type_name, count in top_creature_types:
        matching_cards = []
        for card in deck_list:
            clean_c_input = re.sub(r'^\d+x?\s*', '', str(card)).strip().lower()
            db_obj = card_db_map.get(clean_c_input)
            c_disp = db_obj.name.title() if db_obj else clean_c_input.title() # <--- Fixed!
            ck = get_clean_card_key(c_disp)
            if type_name in card_creature_type_assignments.get(ck, []):
                if c_disp not in matching_cards:
                    matching_cards.append(c_disp)
                
        if matching_cards:
            output.append({
                "theme": f"👾 {type_name.capitalize()}",
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

    card_theme_mapping = {}

    def get_canonical_name_and_key(card_str):
        clean_input = re.sub(r'^\d+x?\s*', '', str(card_str)).strip().lower()
        db_obj = card_db_map.get(clean_input)
        if not db_obj:
            for db_n, c_obj in card_db_map.items():
                if clean_input in db_n or db_n in clean_input:
                    db_obj = c_obj
                    break
        official_name = db_obj.name.title() if db_obj else clean_input.title()
        return official_name, clean_key(official_name)

    for cat_name, cards_set in core_pools.items():
        theme_display = f"📊 {cat_name}"
        for card in cards_set:
            _, k = get_canonical_name_and_key(card)
            if k:
                if theme_display not in card_theme_mapping.setdefault(k, []):
                    card_theme_mapping[k].append(theme_display)

    for card in deck_list:
        _, k = get_canonical_name_and_key(card)
        if not k:
            continue
        card_theme_mapping.setdefault(k, [])
        assigned_types = card_creature_type_assignments.get(k, [])
        for t in assigned_types:
            theme_display = f"👾 {t.capitalize()}"
            if theme_display not in card_theme_mapping[k]:
                card_theme_mapping[k].append(theme_display)

    for theme, cards_set in theme_card_pools.items():
        if len(cards_set) >= 8:
            theme_display = f"🔮 {theme}" if not theme.startswith("🔮") else theme
            for card in cards_set:
                _, k = get_canonical_name_and_key(card)
                if k:
                    if theme_display not in card_theme_mapping.setdefault(k, []):
                        card_theme_mapping[k].append(theme_display)

    return {
        "deck_size": deck_size, 
        "themes": output,
        "card_theme_mapping": card_theme_mapping
    }

def generate_tagged_export_string(deck_list: list, analysis_result: dict) -> str:
    card_theme_mapping = analysis_result.get("card_theme_mapping", {})
    export_lines = []
    
    for card_str in deck_list:
        if not card_str.strip():
            continue
            
        qty_match = re.match(r'^(\d+x?\s*)', str(card_str))
        qty_prefix = qty_match.group(1) if qty_match else "1 "
        
        raw_name = re.sub(r'^\d+x?\s*', '', str(card_str)).strip()
        card_key = clean_key(raw_name)
        
        assigned_themes = card_theme_mapping.get(card_key, [])
        
        if not assigned_themes:
            for db_k, themes_list in card_theme_mapping.items():
                if card_key in db_k or db_k in card_key:
                    assigned_themes = themes_list
                    break
                    
        clean_tags = []
        for theme in assigned_themes:
            tag_name = re.sub(r'^[📊👾🔮]\s*', '', str(theme)).strip()
            if tag_name and tag_name not in clean_tags:
                clean_tags.append(tag_name)
                
        line = f"{qty_prefix}{raw_name}"
        if clean_tags:
            line += " " + " ".join(clean_tags)
            
        export_lines.append(line)
        
    return "\n".join(export_lines)