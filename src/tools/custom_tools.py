# ==============================================================
# custom_tools.py — Utility Functions
# ==============================================================


def format_order_table(rows: list[dict]) -> str:
    """
    Formats a list of order dicts into a readable text table.

    Args:
        rows (list[dict]): Order records from MySQL.

    Returns:
        str: Formatted table or "no records" message.

    Usage:
        print(format_order_table(result["rows"]))
    """
    if not rows:
        return "⚠️ No orders found."

    lines = []

    for row in rows:

        lines.append(
            f"  Order #{row.get('order_id', '?')} — "
            f"{row.get('product_name', '?')} ({row.get('brand', '?')}) — "
            f"Status: {row.get('order_status', '?').upper()} — "
            f"City: {row.get('city', '?')} — "
            f"Date: {str(row.get('order_date', '?'))[:10]}"
        )

    return "\n".join(lines)


def format_product_table(rows: list[dict]) -> str:
    """
    Formats a list of product dicts into a readable text summary.

    Args:
        rows (list[dict]): Product records from MySQL.

    Returns:
        str: Formatted product list or "not found" message.
    """

    if not rows:
        return "⚠️ No products found."

    lines = []

    for row in rows:

        stock  = row.get("stock_quantity", 0)
        status = row.get("status", "unknown")

        
        if status == "available" and stock > 0:
            avail = f"✅ In stock ({stock} units)"

        elif status == "out_of_stock" or stock == 0:
            avail = "❌ Out of stock"

        else:
            avail = f"⚠️ {status}"

        lines.append(
            f"  {row.get('product_name', '?')} — "
            f"{row.get('brand', '?')} — "
            f"Color: {row.get('color', '?')} — "
            f"Price: {row.get('price', '?')} SAR — "
            f"City: {row.get('city_available', '?')} — "
            f"{avail}"
        )

    return "\n".join(lines)


def detect_language(text: str) -> str:
    """
    Detects whether the text is Arabic or English.
    Simple heuristic — checks Unicode Arabic character range.

    Args:
        text (str): Customer message.

    Returns:
        str: "ar" for Arabic, "en" for English (default).
    """

    arabic_chars = sum(
        1 for c in text
        if "\u0600" <= c <= "\u06FF"
    )

    return "ar" if arabic_chars > len(text) * 0.2 else "en"


def extract_number_from_text(text: str) -> int | None:
    """
    Extracts the first integer number found in text.

    Supports:
        "3"
        "#3"
        "order 3"
        "order #3"
        "طلبي ٣"
        Arabic numerals

    Returns:
        int | None
    """

    import re

    if not text:
        return None

    
    arabic_map = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789"
    )

    normalized = text.translate(arabic_map)

    
    normalized = normalized.replace(",", " ")

    
    match = re.search(r"\d+", normalized)

    if not match:
        return None

    try:
        return int(match.group())

    except Exception:
        return None


def truncate_text(text: str, max_chars: int = 300) -> str:
    """
    Truncates text to a maximum character length.
    Adds "..." if truncated.

    Used to keep complaint text within database limits.

    Args:
        text      (str): The text to truncate.
        max_chars (int): Maximum characters allowed.

    Returns:
        str: Truncated text.
    """

    if not text:
        return ""

    text = str(text).strip()

    if len(text) <= max_chars:
        return text

    return text[:max_chars - 3] + "..."