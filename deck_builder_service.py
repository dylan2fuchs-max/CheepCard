import re
from sqlalchemy import func
from Card_Filter import db, Card


def _get_name_col():
    return getattr(Card, "_name", None) or getattr(Card, "name")


def _get_oracle_col():
    return getattr(Card, "_oracle_text", None) or getattr(Card, "oracle_text")


def parse_deck_lines(card_data: str) -> list[dict]:
    """Parse lines like '1 Sol Ring' or 'Sol Ring' into {'qty': int, 'name': str}."""
    entries = []
    if not card_data:
        return entries

    for raw_line in card_data.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = re.match(r"^(?:(\d+)\s*x?\s+)?(.+)$", line, flags=re.IGNORECASE)
        if match:
            qty = int(match.group(1)) if match.group(1) else 1
            name = match.group(2).strip()
            if name:
                entries.append({"qty": max(1, qty), "name": name})
    return entries


def build_deck_analysis(saved_deck) -> dict:
    """Batch-load matching Card records from PostgreSQL and compute stats & class counts."""
    entries = parse_deck_lines(saved_deck.card_data)
    unique_names = list({e["name"].lower() for e in entries})

    card_lookup = {}
    if unique_names:
        name_col = _get_name_col()
        matched_cards = Card.query.filter(func.lower(name_col).in_(unique_names)).all()
        for card in matched_cards:
            card_lookup[str(getattr(card, "name", "")).strip().lower()] = card

    class_counts = {
        "Ramp": 0,
        "Draw": 0,
        "Removal": 0,
        "Boardwipe": 0,
        "Land": 0,
        "Other": 0,
    }
    total_cards = 0
    total_price = 0.0
    enriched_cards = []

    for entry in entries:
        key = entry["name"].lower()
        card_obj = card_lookup.get(key)
        qty = entry["qty"]
        total_cards += qty

        price = float(getattr(card_obj, "price", 0.0) or 0.0) if card_obj else 0.0
        total_price += price * qty

        c1 = str(getattr(card_obj, "card_class_1", "") or "").strip() if card_obj else ""
        c2 = str(getattr(card_obj, "card_class_2", "") or "").strip() if card_obj else ""
        primary_class = c1 if c1 and c1.lower() != "none" else (c2 if c2 and c2.lower() != "none" else "Other")

        r1_word = str(getattr(card_obj, "ranking_1_word", "") or "").strip() if card_obj else ""
        r2_word = str(getattr(card_obj, "ranking_2_word", "") or "").strip() if card_obj else ""
        rank_word = r1_word if r1_word and r1_word.lower() != "none" else (r2_word if r2_word and r2_word.lower() != "none" else "Unranked")

        matched_bucket = "Other"
        combined_classes = f"{c1} {c2}".lower().replace("board wipe", "boardwipe")
        for bucket in ("Ramp", "Draw", "Removal", "Boardwipe", "Land"):
            if bucket.lower() in combined_classes:
                matched_bucket = bucket
                break
        class_counts[matched_bucket] += qty

        enriched_cards.append({
            "qty": qty,
            "name": getattr(card_obj, "name", entry["name"]) if card_obj else entry["name"],
            "price": price,
            "line_total": round(price * qty, 2),
            "class_label": primary_class.title() if primary_class.lower() != "other" else "Other",
            "bucket": matched_bucket,
            "rank_word": rank_word.title(),
            "mana_cost": getattr(card_obj, "mana_cost", "") if card_obj else "",
            "identity": getattr(card_obj, "identity", "") if card_obj else "",
            "image_url": getattr(card_obj, "image_url", "") if card_obj else "",
            "found_in_db": card_obj is not None,
        })

    return {
        "cards": enriched_cards,
        "total_cards": total_cards,
        "total_price": round(total_price, 2),
        "class_counts": class_counts,
    }


def search_deck_candidates(
    target_class: str = "",
    color: str = "",
    max_price: float | None = None,
    rank_filter: str = "",
    keyword: str = "",
    limit: int = 24,
) -> list[dict]:
    """Query Card rows by class, color identity, price cap, rank, or keyword for adding/swapping."""
    query = Card.query

    if target_class and target_class.lower() != "all":
        clean_cls = target_class.strip().lower()
        c1_col = getattr(Card, "_card_class_1", None) or getattr(Card, "card_class_1")
        c2_col = getattr(Card, "_card_class_2", None) or getattr(Card, "card_class_2")
        query = query.filter(
            db.or_(
                func.lower(c1_col).contains(clean_cls),
                func.lower(c2_col).contains(clean_cls),
            )
        )

    if keyword:
        kw = keyword.strip().lower()
        name_col = _get_name_col()
        oracle_col = _get_oracle_col()
        query = query.filter(
            db.or_(
                func.lower(name_col).contains(kw),
                func.lower(oracle_col).contains(kw),
            )
        )

    candidates = query.limit(200).all()
    results = []

    for card in candidates:
        price = float(getattr(card, "price", 0.0) or 0.0)
        if max_price is not None and price > max_price:
            continue

        r1_word = str(getattr(card, "ranking_1_word", "") or "").strip().lower()
        r2_word = str(getattr(card, "ranking_2_word", "") or "").strip().lower()
        rank_word = r1_word if r1_word and r1_word != "none" else r2_word

        if rank_filter and rank_filter.lower() != "all":
            if rank_word != rank_filter.strip().lower():
                continue

        if color and color.upper() != "ALL":
            identity = str(getattr(card, "identity", "") or "").upper()
            clean_colors = [ch for ch in identity if ch in "WUBRG"]
            if color.upper() == "C":
                if len(clean_colors) > 0:
                    continue
            elif color.upper() not in clean_colors:
                continue

        c1 = str(getattr(card, "card_class_1", "") or "").strip()
        results.append({
            "name": getattr(card, "name", ""),
            "price": price,
            "class_label": c1.title() if c1 and c1.lower() != "none" else "General",
            "rank_word": rank_word.title() if rank_word else "Unranked",
            "mana_cost": getattr(card, "mana_cost", ""),
            "identity": getattr(card, "identity", ""),
            "image_url": getattr(card, "image_url", ""),
        })

        if len(results) >= limit:
            break

    return results