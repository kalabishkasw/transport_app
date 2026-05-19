"""
контекст-процесор для двомовності публічного порталу.
підставляє у шаблони змінну `T` (словник перекладів) та `LANG`.
"""

from .i18n import SUPPORTED_LANGUAGES, get_translations


def i18n(request):
    lang = request.session.get('portal_lang', 'uk')
    if lang not in dict(SUPPORTED_LANGUAGES):
        lang = 'uk'
    return {
        'T': get_translations(lang),
        'LANG': lang,
        'LANGS': SUPPORTED_LANGUAGES,
    }
