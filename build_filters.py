import pandas as pd
from pathlib import Path
import re
from collections import Counter

# READ-ONLY INPUT
EXCEL_PATH = Path.cwd() / "Magic Card Data Base Current View.xlsx"
OUTPUT_FILE = Path.cwd() / "auto_filler_words.py"

def generate_automated_filler_file():
    if not EXCEL_PATH.exists():
        print(f"Error: Could not find your spreadsheet at {EXCEL_PATH}")
        return

    print("Reading spreadsheet rules text...")
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df.columns = df.columns.str.strip()
    text_col = "Text" if "Text" in df.columns else "Rules Text"
    
    all_words = []
    for _, row in df.iterrows():
        rules_text = str(row.get(text_col, "")).lower()
        if pd.isna(row.get(text_col)) or not rules_text.strip():
            continue
        clean_text = re.sub(r'[^\w\s{}]', ' ', rules_text)
        all_words.extend(clean_text.split())

    # Grab the top 1000 most common tokens across your entire sheet
    word_counts = Counter(all_words)
    top_tokens = [word for word, count in word_counts.most_common(1000)]

    # Explicitly list the strategic gameplay themes you WANT TO KEEP on your dashboard
    # The script will make sure these NEVER get added to the filler list
    themes_to_keep = {
        'flying', 'haste', 'trample', 'vigilance', 'lifelink', 'menace', 'flash', 
        'reach', 'deathtouch', 'indestructible', 'scry', 'mill', 'flashback', 
        'defender', 'token', 'tokens', 'artifact', 'artifacts', 'enchantment',
        'enchantments', 'sorcery', 'instant', 'planeswalker', 'legendary',
        'equipment', 'aura', 'treasure', 'vehicle', 'human', 'wizard', 'warrior', 'soldier', 'spirit', 'zombie', 'cleric',
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

    # Clean the token list using rules
    final_fillers = []
    for word in top_tokens:
        # 1. Skip core tracking pillars to let them stay in your top bars
        if word in ['draw', 'life', 'land', 'lands']:
            continue
        # 2. Skip real strategic gameplay keywords
        if word in themes_to_keep:
            continue
        # 3. Skip pure numeric strings (like '1', '2', '3')
        if word.isdigit():
            continue
            
        final_fillers.append(word)

    # Automatically format and write the python file onto your disk
    print(f"Writing {len(final_fillers)} optimized grammar filters to file...")
    with open(OUTPUT_FILE, "w") as f:
        f.write("# AUTOMATICALLY GENERATED DATABASE GRAMMAR FILTER LIST\n")
        f.write("AUTO_FILLER_WORDS = {\n")
        for i, word in enumerate(sorted(final_fillers)):
            f.write(f"    '{word}',")
            if (i + 1) % 8 == 0:  # Format nicely into rows of 8 words
                f.write("\n")
        if len(final_fillers) % 8 != 0:
            f.write("\n")
        f.write("}\n")

    print(f"\n[SUCCESS] Formatted filter dictionary securely saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_automated_filler_file()



