"""
Common helper functions.
"""
from datetime import datetime


def time_ago(dt):
    """Convert datetime to '2 hours ago' format."""
    if not dt:
        return 'Unknown'
    
    diff = datetime.utcnow() - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f'{mins} min{"s" if mins > 1 else ""} ago'
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f'{hours} hour{"s" if hours > 1 else ""} ago'
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f'{days} day{"s" if days > 1 else ""} ago'
    else:
        return dt.strftime('%b %d, %Y')


def format_salary(min_sal, max_sal, currency='PKR'):
    """Format salary range."""
    if not min_sal and not max_sal:
        return 'Negotiable'
    if min_sal and max_sal:
        return f'{currency} {min_sal:,} - {max_sal:,}'
    if min_sal:
        return f'{currency} {min_sal:,}+'
    return f'Up to {currency} {max_sal:,}'
