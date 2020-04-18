from django import template

from ..music_handler.interpret import KEYS

register = template.Library()

@register.filter
def num2chord(value):
    try:
        return KEYS[int(value) % 12]
    except Exception:
        return value
