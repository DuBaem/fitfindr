"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    # 1. Load all listings
    listings = load_listings()

    # 2. Filter by max_price and size
    filtered = []
    for listing in listings:
        if max_price is not None and listing.get("price", 0) > max_price:
            continue
        if size is not None:
            listing_size = listing.get("size", "").lower()
            if size.lower() not in listing_size:
                continue
        filtered.append(listing)

    # 3. Score each listing by keyword overlap with `description`
    keywords = set(description.lower().split())

    scored = []
    for listing in filtered:
        # Build a corpus of searchable text fields from the listing
        searchable_parts = [
            listing.get("title") or "",
            listing.get("description") or "",
            listing.get("category") or "",
            listing.get("brand") or "",
            " ".join(listing.get("style_tags") or []),
            " ".join(listing.get("colors") or []),
        ]
        
        searchable_text = " ".join(str(part) for part in searchable_parts).lower()
        searchable_words = set(searchable_text.split())

        # Score = number of keyword tokens that appear in the listing's text
        score = len(keywords & searchable_words)

        # 4. Drop listings with a score of 0
        if score > 0:
            scored.append((score, listing))

    # 5. Sort by score descending and return just the listing dicts
    scored.sort(key=lambda x: x[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    # Build a readable summary of the new item
    item_summary = (
        f"Title: {new_item.get('title', 'Unknown')}\n"
        f"Category: {new_item.get('category', 'Unknown')}\n"
        f"Style Tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Brand: {new_item.get('brand', 'Unknown')}\n"
        f"Condition: {new_item.get('condition', 'Unknown')}\n"
        f"Description: {new_item.get('description', 'No description provided')}"
    )

    wardrobe_items = wardrobe.get("items", [])

    # 1. check if the wardrobe is empty
    if not wardrobe_items:
        # 2. Empty wardrobe: general styling advice only
        prompt = (
            "You are a creative thrift fashion stylist.\n\n"
            "A user just found this thrifted item and has no existing wardrobe on record:\n\n"
            f"{item_summary}\n\n"
            "Suggest 1–2 complete outfits they could build around this piece. "
            "Describe the vibe, what types of garments and accessories would pair well, "
            "and any styling tips (tucking, layering, footwear, etc.). "
            "Be specific and enthusiastic — speak like a real stylist, not a product listing."
        )
    else:
        # 3. if not empty: suggest combinations using named wardrobe pieces
        wardrobe_summary = "\n".join(
            f"- {item.get('title', 'Unknown')} "
            f"({item.get('category', '?')}, "
            f"{', '.join(item.get('colors', []))})"
            for item in wardrobe_items
        )

        prompt = (
            "You are a creative thrift fashion stylist.\n\n"
            "A user is considering buying this thrifted item:\n\n"
            f"{item_summary}\n\n"
            "Their current wardrobe includes:\n"
            f"{wardrobe_summary}\n\n"
            "Suggest 1–2 complete outfits that combine the new item with specific pieces "
            "from their wardrobe. Reference wardrobe items by name, describe the overall vibe "
            "of each outfit, and include any practical styling tips (layering, footwear, "
            "accessories, tucking, etc.). Be specific and speak like a real stylist."
        )

    # 4. Call the LLM and return the response string
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        # Fallback string so the workflow does not crash
        return f"Styling service is currently unavailable. General tip: pair '{new_item.get('title', 'this piece')}' with your favorite basics!"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Replace this with your implementation
    # 1. Guard against empty or whitespace-only outfit string
    if not outfit or not outfit.strip():
        return (
            "Could not generate a fit card: outfit data was lost or empty. "
            "Please run suggest_outfit() first and pass its output here."
        )

    client = _get_groq_client()

    # Build compact item context for the caption
    item_name     = new_item.get("title", "this thrifted find")
    item_price    = new_item.get("price", "unknown price")
    item_platform = new_item.get("platform", "a thrift platform")
    item_colors   = ", ".join(new_item.get("colors", []))
    item_style    = ", ".join(new_item.get("style_tags", []))

    prompt = (
        "You are a witty, trend-savvy fashion content creator who writes "
        "Instagram and TikTok OOTD captions.\n\n"
        "Write a 2–4 sentence caption for the outfit below. Rules:\n"
        "- Sound casual and authentic, like a real post — not a product description\n"
        "- Mention the item name, price, and platform exactly once each, naturally\n"
        "- Capture the specific vibe of the outfit (don't just say 'cute' or 'fun')\n"
        "- Vary your phrasing and structure — no two captions should feel the same\n\n"
        f"Thrifted item: {item_name}\n"
        f"Price: ${item_price}\n"
        f"Platform: {item_platform}\n"
        f"Colors: {item_colors}\n"
        f"Style tags: {item_style}\n\n"
        f"Outfit suggestion:\n{outfit}\n\n"
        "Write only the caption — no intro line, no hashtags, no quotation marks."
    )

    # 2. Wrap LLM call in try/except
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,  # Higher temp for caption variety across calls
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return (
            f"Could not generate a fit card due to an API error: {e}. "
            "The outfit suggestion is still available — try again or write your own caption."
        )
