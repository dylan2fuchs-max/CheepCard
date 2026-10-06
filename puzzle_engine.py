import random
import urllib.parse
from datetime import datetime

# Handcrafted Master Templates utilizing your Starters, Extenders, Switches, and Goals formula
PUZZLE_POOL = [
    {
        "title": "Yawgmoth's Will Storm Line",
        "difficulty": "easy",
        "description": "Generate explosive black mana using rituals and lotus petals, cast Yawgmoth's Will to replay your graveyard, and finish with Tendrils of Agony.",
        "hand": ["Swamp", "Lotus Petal", "Dark Ritual", "Cabal Ritual", "Mishra's Bauble", "Yawgmoth's Will", "Tendrils of Agony"],
        "roles": {
            "Starters": ["Swamp"],
            "Extenders": ["Lotus Petal", "Dark Ritual", "Cabal Ritual"],
            "Switches": ["Mishra's Bauble", "Yawgmoth's Will"],
            "Goals": ["Tendrils of Agony"]
        },
        "rules": {
            "slots": [
                ["Swamp", "Lotus Petal", "Mishra's Bauble"],
                ["Swamp", "Lotus Petal", "Dark Ritual", "Mishra's Bauble"],
                ["Swamp", "Lotus Petal", "Dark Ritual", "Cabal Ritual", "Mishra's Bauble"],
                ["Swamp", "Lotus Petal", "Dark Ritual", "Cabal Ritual", "Mishra's Bauble", "Yawgmoth's Will"],
                ["Swamp", "Lotus Petal", "Dark Ritual", "Cabal Ritual", "Mishra's Bauble", "Yawgmoth's Will"],
                ["Yawgmoth's Will", "Lotus Petal", "Mishra's Bauble"],
                ["Tendrils of Agony"]
            ],
            "must_be_before": [
                ["Yawgmoth's Will", "Tendrils of Agony"]
            ]
        }
    },
    {
        "title": "Start your Engines",
        "difficulty": "easy",
        "description": "Create a loop using Isochron Scepter to power ourselves to victory.",
        "hand": ["Plains", "Sol Ring", "Mana Vault", "Isochron Scepter", "Dramatic Reversal", "Prismite", "Shorikai, Genesis Engine"],
        "roles": {
            "Starters": ["Plains"],
            "Extenders": ["Sol Ring", "Mana Vault"],
            "Switches": ["Isochron Scepter", "Dramatic Reversal", "Prismite"],
            "Goals": ["Shorikai, Genesis Engine"]
        },
        "rules": {
            "slots": [
                ["Plains"],
                ["Sol Ring", "Mana Vault"],
                ["Sol Ring", "Mana Vault"],
                ["Isochron Scepter"],
                ["Dramatic Reversal"],
                ["Prismite"],
                ["Shorikai, Genesis Engine"]
            ]
        }
    },
    {
        "title": "Graveyard Surge",
        "difficulty": "easy",
        "description": "Set up your mana sources and creatures before executing your reanimation sequencing.",
        "hand": ["Swamp", "Dark Ritual", "Lightning Greaves", "Reanimate", "Raven's Crime", "Griselbrand", "Lotus Petal"],
        "roles": {
            "Starters": ["Swamp"],
            "Extenders": ["Dark Ritual", "Lightning Greaves", "Lotus Petal"],
            "Switches": ["Raven's Crime", "Reanimate"],
            "Goals": ["Griselbrand"]
        },
        "rules": {
            "slots": [
                ["Swamp", "Lotus Petal"],
                ["Lotus Petal", "Dark Ritual", "Raven's Crime"],
                ["Lotus Petal", "Dark Ritual", "Raven's Crime", "Lightning Greaves"],
                ["Lotus Petal", "Dark Ritual", "Raven's Crime", "Lightning Greaves", "Reanimate"],
                ["Lotus Petal", "Dark Ritual", "Raven's Crime", "Lightning Greaves", "Griselbrand", "Reanimate"],
                ["Lotus Petal", "Raven's Crime", "Lightning Greaves", "Griselbrand", "Reanimate"],
                ["Reanimate", "Lightning Greaves", "Griselbrand"]
            ],
            "must_be_before": [
                ["Dark Ritual", "Lightning Greaves"],
                ["Raven's Crime", "Griselbrand"],
                ["Raven's Crime", "Reanimate"]
            ]
        }
    },
    {
        "title": "Spectacle Burn",
        "difficulty": "medium",
        "description": "Fire off Lightning Bolt to enable Spectacle for Light Up the Stage, then chain fast red rituals into a storm finish with Grapeshot.",
        "hand": ["Mountain", "Rite of Flame", "Simian Spirit Guide", "Lightning Bolt", "Light Up the Stage", "Pyretic Ritual", "Grapeshot"],
        "roles": {
            "Starters": ["Mountain"],
            "Extenders": ["Rite of Flame", "Simian Spirit Guide", "Pyretic Ritual"],
            "Switches": ["Lightning Bolt", "Light Up the Stage"],
            "Goals": ["Grapeshot"]
        },
        "rules": {
            "slots": [
                ["Mountain", "Simian Spirit Guide"],
                ["Mountain", "Rite of Flame", "Simian Spirit Guide"],
                ["Mountain", "Rite of Flame", "Simian Spirit Guide", "Lightning Bolt", "Pyretic Ritual"],
                ["Mountain", "Rite of Flame", "Simian Spirit Guide", "Lightning Bolt", "Pyretic Ritual"],
                ["Mountain", "Rite of Flame", "Simian Spirit Guide", "Lightning Bolt", "Light Up the Stage", "Pyretic Ritual"],
                ["Mountain", "Rite of Flame", "Simian Spirit Guide", "Light Up the Stage"],
                ["Grapeshot"]
            ],
            "must_be_before": [
                ["Lightning Bolt", "Light Up the Stage"]
            ]
        }
    },
    {
        "title": "Black Freeze",
        "difficulty": "medium",
        "description": "Navigate your mana and triggers to maximize Brain Freeze storm count using Deathgreeter and ritual generation.",
        "hand": ["Deathgreeter", "Swamp", "Sol Ring", "Chromatic Star", "Dark Ritual", "Brain Freeze", "Blood Pet"],
        "roles": {
            "Starters": ["Swamp"],
            "Extenders": ["Sol Ring", "Dark Ritual", "Blood Pet"],
            "Switches": ["Chromatic Star", "Deathgreeter"],
            "Goals": ["Brain Freeze"]
        },
        "rules": {
            "slots": [
                ["Swamp"],
                ["Dark Ritual"],
                ["Sol Ring", "Deathgreeter"],
                ["Deathgreeter", "Blood Pet", "Sol Ring", "Chromatic Star"],
                ["Deathgreeter", "Blood Pet", "Sol Ring", "Chromatic Star"],
                ["Chromatic Star", "Blood Pet"],
                ["Brain Freeze"]
            ],
            "must_be_before": [
                ["Sol Ring", "Chromatic Star"],
                ["Deathgreeter", "Blood Pet"]
            ],
            "must_be_last": "Brain Freeze"
        }
    },
    {
        "title": "Here Comes the Aliens",
        "difficulty": "medium",
        "description": "Ramp fast using rituals, mana generation, and life payment with Treasonous Ogre to cast Emrakul, the World Anew.",
        "hand": ["Mountain", "Elvish Spirit Guide", "Pyretic Ritual", "Ruby Medallion", "Desperate Ritual", "Treasonous Ogre", "Emrakul, the World Anew"],
        "roles": {
            "Starters": ["Mountain"],
            "Extenders": ["Elvish Spirit Guide", "Pyretic Ritual", "Desperate Ritual", "Ruby Medallion"],
            "Switches": ["Treasonous Ogre"],
            "Goals": ["Emrakul, the World Anew"]
        },
        "rules": {
            "slots": [
                ["Mountain"],
                ["Elvish Spirit Guide"],
                ["Desperate Ritual", "Pyretic Ritual"],
                ["Ruby Medallion"],
                ["Desperate Ritual", "Pyretic Ritual"],
                ["Treasonous Ogre"],
                ["Emrakul, the World Anew"]
            ]
        }
    },
    {
        "title": "Nexus Vault",
        "difficulty": "medium",
        "description": "Deploy your resources to channel a Nexus of Fate finish.",
        "hand": ["Island", "Sol Ring", "Mana Vault", "Arcane Signet", "Mox Opal", "Turnabout", "Nexus of Fate"],
        "roles": {
            "Starters": ["Island"],
            "Extenders": ["Sol Ring", "Mana Vault", "Arcane Signet"],
            "Switches": ["Mox Opal", "Turnabout"],
            "Goals": ["Nexus of Fate"]
        },
        "rules": {
            "slots": [
                ["Island"],
                ["Sol Ring", "Mana Vault"],
                ["Sol Ring", "Mana Vault"],
                ["Arcane Signet"],
                ["Mox Opal"],
                ["Turnabout"],
                ["Nexus of Fate"]
            ]
        }
    },
    {
        "title": "Rainbow Road Runner",
        "difficulty": "medium",
        "description": "Brew your skills to prep our birdy for the storm to come",
        "hand": ["Island", "Chrome Mox", "Birds of Paradise", "Trained Jackal", "Lightning Greaves", "Sol Ring", "Rain of Blades"],
        "roles": {
            "Starters": ["Island", "Chrome Mox"],
            "Extenders": ["Lightning Greaves", "Sol Ring"],
            "Switches": ["Birds of Paradise", "Trained Jackal"],
            "Goals": ["Rain of Blades"]
        },
        "rules": {
            "slots": [
                ["Island", "Chrome Mox"],
                ["Island", "Chrome Mox", "Birds of Paradise", "Trained Jackal", "Sol Ring"],
                ["Island", "Chrome Mox", "Birds of Paradise", "Trained Jackal", "Lightning Greaves", "Sol Ring"],
                ["Island", "Chrome Mox", "Birds of Paradise", "Trained Jackal", "Lightning Greaves", "Sol Ring"],
                ["Trained Jackal", "Birds of Paradise", "Lightning Greaves", "Sol Ring"],
                ["Birds of Paradise", "Lightning Greaves"],
                ["Rain of Blades"]
            ],
            "must_be_before": [
                ["Island", "Sol Ring"],
                ["Sol Ring", "Lightning Greaves"],
                ["Trained Jackal", "Birds of Paradise"],
                ["Chrome Mox", "Trained Jackal"],
                ["Birds of Paradise", "Rain of Blades"]
            ]
        }
    },
    {
        "title": "Hungry Crab",
        "difficulty": "hard",
        "description": "Sequence your land drops, extra exploration effects, and mill triggers to power up your board state.",
        "hand": ["Lotus Petal", "Hedron Crab", "Forest", "Exploration", "Island", "Energy Tap", "Gingerbrute"],
        "roles": {
            "Starters": ["Forest", "Island"],
            "Extenders": ["Lotus Petal", "Exploration"],
            "Switches": ["Energy Tap", "Hedron Crab"],
            "Goals": ["Gingerbrute"]
        },
        "rules": {
            "slots": [
                ["Lotus Petal"],
                ["Hedron Crab"],
                ["Forest"],
                ["Exploration"],
                ["Island"],
                ["Energy Tap"],
                ["Gingerbrute"]
            ]
        }
    },
    {
        "title": "Life Cascade",
        "difficulty": "hard",
        "description": "Set up a ladder of life gain chain to maximize your life total.",
        "hand": ["Ancient Tomb", "Sol Ring", "Mana Vault", "Lotus Petal", "Three Bowls of Porridge", "Aetherflux Reservoir", "Helm of Awakening"],
        "roles": {
            "Starters": ["Ancient Tomb"],
            "Extenders": ["Sol Ring", "Mana Vault", "Lotus Petal"],
            "Switches": ["Helm of Awakening", "Three Bowls of Porridge"],
            "Goals": ["Aetherflux Reservoir"]
        },
        "rules": {
            "slots": [
                ["Ancient Tomb"],
                ["Helm of Awakening"],
                ["Mana Vault"],
                ["Aetherflux Reservoir"],
                ["Sol Ring", "Lotus Petal"],
                ["Sol Ring", "Lotus Petal"],
                ["Three Bowls of Porridge"]
            ]
        }
    },
    {
        "title": "Petal for Life and Death",
        "difficulty": "hard",
        "description": "Create your wondrous world, just to snap it all out of existence and leave behind a single petal.",
        "hand": ["Volcanic Island", "Lotus Petal", "Enter the Unknown", "Snap", "Underworld Breach", "Forest", "Zuran Orb"],
        "roles": {
            "Starters": ["Volcanic Island", "Lotus Petal", "Forest"],
            "Extenders": ["Enter the Unknown"],
            "Switches": ["Snap", "Zuran Orb"],
            "Goals": ["Underworld Breach"]
        },
        "rules": {
            "slots": [
                ["Volcanic Island", "Forest", "Lotus Petal"],
                ["Enter the Unknown", "Volcanic Island", "Forest", "Lotus Petal"],
                ["Enter the Unknown", "Volcanic Island", "Forest", "Lotus Petal"],
                ["Enter the Unknown", "Volcanic Island", "Forest", "Lotus Petal"],
                ["Snap"],
                ["Zuran Orb", "Underworld Breach"],
                ["Underworld Breach", "Zuran Orb"]
            ],
            "must_be_before": [
                ["Lotus Petal", "Snap"],
                ["Volcanic Island", "Snap"]
            ]
        }
    },
    {
        "title": "All Manaful Mage",
        "difficulty": "hard",
        "description": "With Jodah, Archmage Eternal on the field and five mana (one of each color) available, orchestrate your artifact tools and massive mana payloads into a game-ending Fireball.",
        "hand": ["Chromatic Orrery", "Manifold Key", "Apex of Power", "Leyline Immersion", "Spellbook", "Krark-Clan Ironworks", "Fireball"],
        "roles": {
            "Starters": ["Leyline Immersion"],
            "Extenders": ["Chromatic Orrery", "Krark-Clan Ironworks"],
            "Switches": ["Manifold Key", "Spellbook"],
            "Goals": ["Apex of Power", "Fireball"]
        },
        "rules": {
            "slots": [
                ["Chromatic Orrery", "Spellbook", "Leyline Immersion"],
                ["Chromatic Orrery", "Manifold Key", "Spellbook", "Leyline Immersion", "Apex of Power"],
                ["Chromatic Orrery", "Manifold Key", "Spellbook", "Leyline Immersion", "Apex of Power"],
                ["Chromatic Orrery", "Manifold Key", "Spellbook", "Leyline Immersion", "Apex of Power"],
                ["Chromatic Orrery", "Manifold Key", "Spellbook", "Leyline Immersion", "Apex of Power"],
                ["Krark-Clan Ironworks"],
                ["Fireball"]
            ],
            "must_be_before": [
                ["Chromatic Orrery", "Manifold Key"],
                ["Chromatic Orrery", "Apex of Power"]    
            ]
        }
    }
]
# The Secret Bonus Level (Unlocked via Speedrun)
BONUS_LEVEL = {
    "title": "Lands? Where we are going we dont Need lands!",
    "difficulty": "medium",
    "description": "Navigate the toxic enviroment with out using lands for tapped mana",
    "hand": ["Mox Diamond", "Culling the Weak", "Rograkh, Son of Rohgahh", "Rain of Filth", "Plains", "Island", "Phyrexian Obliterator"],
    "roles": {
        "Starters": ["Mox Diamond"],
        "Extenders": ["Culling the Weak", "Rain of Filth"],
        "Switches": ["Rograkh, Son of Rohgahh", "Plains", "Island"],
        "Goals": ["Phyrexian Obliterator"]
    },
    "rules": {
        "slots": [
            ["Mox Diamond", "Rograkh, Son of Rohgahh"],
            ["Mox Diamond", "Culling the Weak", "Rograkh, Son of Rohgahh", "Rain of Filth", "Plains", "Island"],
            ["Mox Diamond", "Culling the Weak", "Rograkh, Son of Rohgahh", "Rain of Filth", "Plains", "Island"],
            ["Mox Diamond", "Culling the Weak", "Rograkh, Son of Rohgahh", "Rain of Filth", "Plains", "Island"],
            ["Mox Diamond", "Culling the Weak", "Rograkh, Son of Rohgahh", "Rain of Filth", "Plains", "Island"],
            ["Culling the Weak", "Rain of Filth"],
            ["Phyrexian Obliterator"]
        ],
        "must_be_before": [
            ["Rograkh, Son of Rohgahh", "Culling the Weak"],
            ["Mox Diamond", "Plains"],
            ["Mox Diamond", "Island"],
            ["Plains", "Rain of Filth"],
            ["Island", "Rain of Filth"]
        ]
    }   
}

def build_card_object(card_name):
    clean_name = card_name.split("//")[0].strip()
    encoded_name = urllib.parse.quote(clean_name)
    return {
        "name": card_name,
        "image_url": f"https://api.scryfall.com/cards/named?exact={encoded_name}&format=image"
    }

def generate_puzzle_from_blueprint(blueprint, rng=None):
    if rng is None:
        rng = random.Random()
    hand_names = blueprint["hand"].copy()
    rng.shuffle(hand_names)
    
    formatted_hand = [build_card_object(name) for name in hand_names]
    
    return {
        "title": blueprint["title"],
        "difficulty": blueprint.get("difficulty", "medium"),
        "description": blueprint["description"],
        "hand": formatted_hand,
        "roles": blueprint.get("roles", {}),
        "rules": blueprint["rules"]
    }

def get_all_puzzles():
    rng = random.Random()
    return [generate_puzzle_from_blueprint(bp, rng) for bp in PUZZLE_POOL]

def get_bonus_level_puzzle():
    return generate_puzzle_from_blueprint(BONUS_LEVEL)

def get_daily_puzzle():
    """Generates today's official daily puzzle (same seed for all users worldwide)."""
    today_seed = datetime.now().strftime("%Y-%m-%d")
    rng = random.Random(today_seed)
    blueprint = rng.choice(PUZZLE_POOL)
    puzzle = generate_puzzle_from_blueprint(blueprint, rng)
    puzzle["title"] = f"Daily: {blueprint['title']} ({today_seed})"
    puzzle["mode"] = "daily"
    return puzzle

def get_random_puzzle():
    rng = random.Random()
    blueprint = rng.choice(PUZZLE_POOL)
    puzzle = generate_puzzle_from_blueprint(blueprint, rng)
    puzzle["title"] = f"Practice: {blueprint['title']}"
    puzzle["mode"] = "practice"
    return puzzle

# INSIDE puzzle_engine.py
def generate_puzzle_from_blueprint(blueprint, rng=None):
    if rng is None:
        rng = random.Random()
    hand_names = blueprint["hand"].copy()
    
    # 🎲 THIS SHUFFLE ENSURES HAND CARDS ARE RANDOMIZED EVERY TIME
    rng.shuffle(hand_names)
    
    formatted_hand = [build_card_object(name) for name in hand_names]
    
    return {
        "title": blueprint["title"],
        "difficulty": blueprint.get("difficulty", "medium"),
        "description": blueprint["description"],
        "hand": formatted_hand,
        "roles": blueprint.get("roles", {}),
        "rules": blueprint["rules"]
    }

def validate_user_sequence(user_sequence, rules):
    # 🌟 Safely extract card names whether the frontend sends strings, dicts, or objects
    cleaned_sequence = []
    for card in user_sequence:
        if isinstance(card, dict):
            name = card.get('name') or card.get('Name') or str(card)
        elif hasattr(card, 'name'):
            name = card.name
        else:
            name = str(card)
        cleaned_sequence.append(name.strip())

    print(f"DEBUG - Cleaned User Sequence: {cleaned_sequence}") # Check your Render logs for this!

    if len(cleaned_sequence) != 7:
        return {"success": False, "message": "You must place all 7 cards into sequence slots!"}

    slot_rules = rules.get("slots")
    if slot_rules:
        for i, allowed_cards in enumerate(slot_rules):
            card_in_slot = cleaned_sequence[i]
            # Clean allowed rule cards too
            cleaned_allowed = [str(c).strip() for c in allowed_cards]
            
            if card_in_slot not in cleaned_allowed:
                slot_num = i + 1
                expected_str = " / ".join(cleaned_allowed)
                return {
                    "success": False,
                    "message": f"Placement Error in Slot {slot_num}: '{card_in_slot}' cannot be played here. Expected: [{expected_str}]"
                }

    must_be_before = rules.get("must_be_before", [])
    for card_a, card_b in must_be_before:
        clean_a, clean_b = str(card_a).strip(), str(card_b).strip()
        if clean_a in cleaned_sequence and clean_b in cleaned_sequence:
            if cleaned_sequence.index(clean_a) > cleaned_sequence.index(clean_b):
                return {
                    "success": False,
                    "message": f"Sequencing Error: '{clean_a}' must be played before '{clean_b}'!"
                }

    must_be_last = rules.get("must_be_last")
    if must_be_last:
        clean_last = str(must_be_last).strip()
        if cleaned_sequence[-1] != clean_last:
            return {
                "success": False, 
                "message": f"Optimal Line Failed: '{clean_last}' must be cast last in slot 7!"
            }

    return {
        "success": True, 
        "message": "🎉 Optimal sequence achieved! Maximum storm count reached and triggers aligned correctly."
    }