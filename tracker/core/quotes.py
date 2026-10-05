"""
Curated motivational quotes, grouped by theme. Static data - no DB table needed for v1.
"""

QUOTES = {
    "group_success": [
        {"text": "If you want to go fast, go alone. If you want to go far, go together.", "author": "African proverb"},
        {"text": "Talent wins games, but teamwork and intelligence win championships.", "author": "Michael Jordan"},
        {"text": "None of us is as smart as all of us.", "author": "Ken Blanchard"},
        {"text": "Coming together is a beginning, staying together is progress, working together is success.", "author": "Henry Ford"},
    ],
    "progress_tracking": [
        {"text": "What gets measured gets managed.", "author": "Peter Drucker"},
        {"text": "Progress is impossible without change.", "author": "George Bernard Shaw"},
        {"text": "You don't have to see the whole staircase, just take the first step.", "author": "Martin Luther King Jr."},
        {"text": "Small daily improvements are the key to staggering long-term results.", "author": "James Clear"},
    ],
    "time_management": [
        {"text": "The bad news is time flies. The good news is you're the pilot.", "author": "Michael Altshuler"},
        {"text": "Until we can manage time, we can manage nothing else.", "author": "Peter Drucker"},
        {"text": "It's not that we have too little time, but more that we lose a lot of it.", "author": "Seneca"},
    ],
    "helping_others": [
        {"text": "Alone we can do so little; together we can do so much.", "author": "Helen Keller"},
        {"text": "No one has ever become poor by giving.", "author": "Anne Frank"},
        {"text": "The best way to find yourself is to lose yourself in the service of others.", "author": "Mahatma Gandhi"},
        {"text": "Asking for help is not a sign of weakness, it's a sign of strength.", "author": "Unknown"},
    ],
}

ALL_THEMES = list(QUOTES.keys())


def get_quotes(theme: str = None):
    if theme and theme in QUOTES:
        return QUOTES[theme]
    if theme:
        return []
    # no theme given: one per theme, for a rotating banner
    return [items[0] for items in QUOTES.values()]
