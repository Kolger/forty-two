import gettext
from fortytwo.settings import Settings

lang = gettext.translation('fortytwo', localedir='locales', languages=[Settings.LANGUAGE])
_ = lang.gettext