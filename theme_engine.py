import pandas as pd
import re

class ThemeEngine:
    def __init__(self):
        # 1. Base dictionary for themes with unique, explicit keywords
        self.theme_rules = {
            "Tokens": ["token", "tokens"], "+1/+1 Counters": ["+1/+1"], "Artifacts": ["artifact"],
            "Aggro": ["haste", "attacks", "attacking"], "Lifegain": ["gain life", "lifelink"],
            "Spellslinger": ["instant and sorcery spells", "cast a noncreature", "prowess", "instant or sorcery spell", "cast the copies"],
            "Reanimator": ["from your graveyard", "from a graveyard"],
            "Aristocrats": ["sacrifice", "dies", "whenever a creature dies", "die", "creature you control dies"],
            "Lands Matter": ["whenever a land", "landfall", "you may play an additional land", "earthbend", "return a land", "equal to the number of lands"],
            "Burn": ["damage to any target", "damage to each opponent"],
            "Equipment": ["equipment", "attach"],
            "Enchantress": ["enchantment", "other enchantment", "saga", "sagas", "enchanted", "aura", "auras"], 
            "Voltron": ["aura", "equipment", "equip", "auras"],
            "Treasure": ["treasure token", "create a treasure", "treasures"],
            "Mill": ["into their graveyard", "put into a graveyard", "mill"], "Sacrifice": ["sacrifice"],
            "Wheels": ["discard your hand", "draw seven cards"], "Blink": ["exile target", "return it to the battlefield"],
            "Auras": ["aura", "enchant creature"], "Legends": ["legendary", "historic"], "Discard": ["discard"],
            "Clones": ["copy of target", "enters as a copy"],
            "Card Draw": ["whenever you draw"], "Landfall": ["landfall", "whenever a land enters"],
            "Group Slug": ["each player loses", "each opponent takes"], "Stax": ["players can't", "don't untap"],
            "Storm": ["storm"], "Historic": ["historic"],
            "Infect": ["infect", "poison counter"],
            "Extra Combats": ["additional combat phase", "untap all creatures"],
            "Theft": ["gain control of target", "cast from your opponent"],
            "Self-Mill": ["mill", "top card of your library into your graveyard"],
            "Group Hug": ["each player draws", "each player gains", "whenever a player draws", "player may draw", "opponent draws", "target opponent creates", "each player"],
            "Birthing Pod": ["search your library for a creature card with mana value"],
            "Chaos": ["random", "coin", "flip", "roll"], "Planeswalkers": ["planeswalker"],
            "Forced Combat": ["goad", "attacks each combat if able", "gain control"], "X Spells": ["{X}"],
            "Commander Matters": ["commander", "command zone"], "Exile": ["exile"],
            "Toolbox": ["search your library"], "Cascade": ["cascade"], "-1/-1 Counters": ["-1/-1 counter"],
            "Lifedrain": ["loses life and you gain life", "drain", "lose x", "extort", "each opponent"], "Pillow Fort": ["creatures can't attack you unless"],
            "Hatebears": ["players can't", "activated abilities can't be activated"],
            "Topdeck": ["top card of your library"], "Toughness Matters": ["equal to its toughness", "toughness"],
            "Spell Copy": ["copy target instant", "copy target sorcery"], "Extra Turns": ["take an extra turn"],
            "Stompy": ["trample", "power 4 or greater"], "Energy": ["energy counter", "{E}"], "Dredge": ["dredge"],
            "ETB": ["enters the battlefield", "when enters"], "Self-Damage": ["damage to you", "whenever you lose life", "equal to that card", "amount of life you lose"],
            "Proliferate": ["proliferate"], "Sagas": ["saga"], "Populate": ["populate"],
            "Land Destruction": ["destroy target land", "destroy all land"], "Attack Triggers": ["whenever attacks", "attacks"],
            "Affinity": ["affinity"], "Clues": ["clue", "investigate"], "Monarch": ["the monarch"],
            "Food": ["food token", "create a food", "devour food", "affinity for food"], "Morph": ["morph", "face-down"], "Cycling": ["cycling"],
            "Counterspells": ["counter target spell"], "Deathtouch": ["deathtouch"],
            "Anthems": ["creatures you control get"], "Snow": ["snow"], "Devotion": ["devotion to"],
            "Pingers": ["deals 1 damage to target"], "Politics": ["vote", "choice", "offer"],
            "Tap / Untap": ["tap", "untap"], "Prowess": ["prowess"], "Mutate": ["mutate"],
            "Activated Abilities": [": "], "Rat Colony": ["rat colony", "rat"],
            "Unnatural": ["horror", "alien", "eldrazi"], "Dungeon": ["venture into the dungeon", "dungeon"],
            "Unblockable": ["can't be blocked"], "Ad Nauseam": ["reveal cards from the top of your library"],
            "Modified Creatures": ["modified"], "Zoo": ["domain", "different basic land types"],
            "Triggered Abilities": ["whenever", "when", "at the beginning of"], "Fight": ["fight"],
            "Discover": ["discover"], "Flash": ["flash"], "Flashback": ["flashback"],
            "Sea Creatures": ["kraken", "leviathan", "octopus", "serpent"], "Power": ["power"],
            "Donate": ["target opponent gains control"], "Self-Discard": ["whenever you discard"],
            "Bounce": ["return to its owner's hand"], "Aikido": ["deflect", "redirect", "damage dealt by target"],
            "Counters Matter": ["counter"], "Dragon's Approach": ["dragon's approach"],
            "Cheerios": ["mana value 0", "cost {0}"], "Haste": ["haste"],
            "Party": ["cleric", "rogue", "warrior", "wizard"], "Prison": ["can't attack", "can't cast"],
            "Foretell": ["foretell"], "Sunforger": ["sunforger", "red or white instant"], "Allies": ["ally"],
            "Keywords": ["flying", "first strike", "lifelink", "vigilance", "haste"], "Curses": ["aura curse", "enchant player"],
            "Multicolor Matters": ["multicolor", "gold", "two or more colors"],
            "Impulse Draw": ["exile", "you may play that card this turn"], "Shadowborn Apostles": ["shadowborn apostle"],
            "Earthbending": ["earthbending"], "Modular": ["modular"], "Coin Flip": ["flip a coin"],
            "Scry": ["scry"], "Persistent Petitioners": ["persistent petitioners"],
            "Guildgates": ["gate"], "Madness": ["madness"],
            "Die Roll": ["roll a d20", "roll a die"], "Weenies": ["mana value 2 or less", "power 1 or 2"],
            "Convoke": ["convoke"], "Amass": ["amass"], "Primal Surge": ["primal surge"],
            "Tron": ["urza's mine", "urza's power-plant", "urza's tower"],
            "Land Animation": ["land becomes a creature"], "The Ring": ["the ring tempts you"],
            "Polymorph": ["reveal cards from the top of your library until you reveal a creature"],
            "Fling": ["sacrifice a creature", "deals damage equal to its power"],
            "Kaheera Companion": ["kaheera", "cat", "elemental", "nightmare", "dinosaur", "beast"],
            "Attractions": ["attraction"], "Experience Counters": ["experience counter"],
            "Firebending": ["firebending"], "Surveil": ["surveil"], "Connive": ["connive"],
            "Relentless Rats": ["relentless rats"], "Rad Counters": ["rad counter", "radiation"],
            "Crime": ["commit a crime"], "Blood": ["blood token"], "Charge Counters": ["charge counter"],
            "Suspend": ["suspend"], "Explore": ["explore"], "Power Matters": ["power 4 or greater", "power 3 or greater"],
            "Devoid": ["devoid"], "Annihilator": ["annihilator"], "Myriad": ["myriad"],
            "Enrage": ["whenever is dealt damage"], "Delver": ["instant or sorcery card on top of your library"],
            "Time Counters": ["time counter"], "Deserts": ["desert"], "Adventures": ["adventure"],
            "Hand Size": ["maximum hand size", "each card in your hand", "equal to the number of cards in your hand"],
            "Extra Upkeeps": ["additional upkeep phase", "upkeep step"],
            "Life Exchange": ["exchange life totals"], "Exalted": ["exalted"], "Lessons": ["lesson"],
            "Looting": ["draw a card, then discard a card", "looting"], "Slime Against Humanity": ["slime against humanity"],
            "Airbending": ["airbending"], "Keruga Companion": ["keruga", "mana value 3 or greater"],
            "Obosh Companion": ["obosh", "odd mana value"], "Indestructible": ["indestructible"],
            "Jegantha Companion": ["jegantha"], "Hare Apparent": ["hare apparent"], "Rooms": ["room"],
            "Evoke": ["evoke"], "Waterbending": ["waterbending"],
            "Blue Moon": ["blood moon", "nonbasic lands are islands"], "Freerunning": ["freerunning"],
            "Stoneblade": ["stoneforge mystic"], "Landwalk": ["landwalk"], "Villainous Choice": ["villainous choice"],
            "Illusions": ["illusion", "whenever becomes the target"], "Delirium": ["delirium", "four or more card types"],
            "Offspring": ["offspring"], "Lurrus Companion": ["lurrus", "mana value 2 or less"],
            "Voting": ["vote"], "Turbo Fog": ["prevent all combat damage"],
            "Transform": ["transform"], "Reach": ["reach"],
            "LTB Effects": ["leaves the battlefield", "dies"], "Umori Companion": ["umori"],
            "Spore Counters": ["spore counter"], "Color Hack": ["change the text of target", "color indicator"],
            "Type Hack": ["creature type becomes"], "Day / Night": ["daybound", "nightbound"],
            "Self-Destruct": ["sacrifice this creature at the end step"], "Lure": ["all creatures able to block"],
            "Warp": ["warp"], "Hellbent": ["no cards in hand"], "Plot": ["plot"],
            "Sneak": ["put a creature card from your hand onto the battlefield"],
            "Descend": ["descend", "permanent card in your graveyard"], 
            "Paradox": ["cast from anywhere other than your hand"],
            "Phasing": ["phasing", "phase out"], "Banding": ["banding"], "Battles": ["battle"],
            "Gyruda Companion": ["gyruda", "even mana value"], "Arcane": ["arcane"], "Kicker": ["kicker"],
            "Web-slinging": ["web-slinging"], "Skulk": ["skulk"], "Improvise": ["improvise"],
            "Stun": ["stun counter"], "Towns": ["towns"], "Oil Counters": ["oil counter"],
            "Tempest Hawk": ["tempest hawk"], "Stickers": ["sticker"], "Bobbleheads": ["bobblehead"],
            "Zirda Companion": ["zirda"], "Templar Knights": ["templar knight"], "Craft": ["craft with"],
            "Exploit": ["exploit"], "Bloodthirst": ["bloodthirst"], "Sunburst": ["sunburst"],
            "Mana Rocks": [("artifact", "add")], "Menace": ["menace"], "Clash": ["clash"],
            "Doomsday": ["doomsday"], "Incubate": ["incubate"],
            "Squad": ["squad"], "Caves": ["cave"], "Horsemanship": ["horsemanship"], "Miracles": ["miracle"],
            "Job Select": ["job select"], "Level Up": ["level up"], "Retrace": ["retrace"],
            "Books": ["tome"], "Dandan": ["dandan"], "Planechase": ["planar"], "Dash": ["dash"],
        }
    def evaluate_card_for_theme(self, theme, rules_txt, card_type):
        """Returns True if the card matches the given theme's keywords using exact word boundaries (Handles Strings and Tuples)."""
        keywords = self.theme_rules.get(theme, [])
        
        # Combine rules and type into one searchable string
        text_to_check = str(rules_txt).lower() + " " + str(card_type).lower()
        
        for condition in keywords:
            if isinstance(condition, tuple):
                # AND LOGIC: Every word in the tuple must exist as a standalone word
                if all(bool(re.search(r'\b' + re.escape(word) + r'\b', text_to_check)) for word in condition):
                    return True
            else:
                # OR LOGIC: This specific string must exist as a standalone word
                if bool(re.search(r'\b' + re.escape(condition) + r'\b', text_to_check)):
                    return True
                    
        return False

    def detect_deck_themes(self, card_list, rules_df):
        """Scans processed cards and flags themes with a count >= 8"""
        theme_counts = {theme: 0 for theme in self.theme_rules.keys()}
        
        # Clean rules dataframe indexing for speedy matching
        rules_df.columns = rules_df.columns.str.strip()
        text_col = "Text" if "Text" in rules_df.columns else "Rules Text"
        
        for card in card_list:
            card_name_clean = str(card.name).strip().lower()
            card_type_clean = str(getattr(card, 'type', '')).strip().lower()
            
            # Extract oracle text from your main reference sheet rows
            matched_rows = rules_df[rules_df["Name"].astype(str).str.strip().str.lower() == card_name_clean]
            rules_txt = str(matched_rows.iloc[0].get(text_col, "")).lower() if not matched_rows.empty else ""
            
            # Map items across your configurations by calling your theme evaluation function
            for theme in self.theme_rules.keys():
                if self.evaluate_card_for_theme(theme, rules_txt, card_type_clean):
                    theme_counts[theme] += 1
                    
        # Return all styles hitting the threshold requirement constraint
        return [theme for theme, count in theme_counts.items() if count >= 8]