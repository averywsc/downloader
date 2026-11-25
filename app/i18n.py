def N(context, text):
    return text


# 只放 Qt 本地名称不合适的语言
LANGUAGE_TEXTS = {
    "zh_CN": "简体中文 (中国大陆)",
    "zh_TW": "正體中文 (台灣)",
    "yue_HK": "粤语 (香港)",
    "en_US": "English (US)",
    "ja_JP": "日本語 (日本)",
    "ru_RU": "Русский (Россия)",
    "pt_BR": "Português (Brasil)",
    "es_ES": "Español (España)",
    "id_ID": "Bahasa Indonesia",
}


def loadLanguages() -> list[str]:
    from PySide6.QtCore import QDir
    names = QDir(":/i18n").entryList(["gd3.*_*.qm"])
    codes = sorted(name.removeprefix("gd3.").removesuffix(".qm") for name in names)
    # 粤语的设置值是 yue_HK，文件却叫 zh_HK
    return ["yue_HK" if code == "zh_HK" else code for code in codes]


def toLanguageText(code: str) -> str:
    if code in LANGUAGE_TEXTS:
        return LANGUAGE_TEXTS[code]
    from PySide6.QtCore import QLocale
    locale = QLocale(code)
    name = locale.nativeLanguageName()
    return f"{name[:1].upper()}{name[1:]} ({locale.nativeTerritoryName()})"


def toLocalizedError(error) -> str:
    from PySide6.QtCore import QCoreApplication
    text = QCoreApplication.translate("TaskErrors", error.message) or error.message
    return text.format_map(error.params) if error.params else text


N("TaskErrors", 'Process terminated abnormally ({code}): {detail}')
N("TaskErrors", 'Unexpected error: {detail}')
N("TaskErrors", 'Unsupported link')
N("TaskErrors", 'Archive contains unsafe path: {path}')
N("TaskErrors", 'Archive file not found: {path}')
N("TaskErrors", 'Unsupported archive format: {name}')
N("TaskErrors", 'No executables found in archive: {name}')
N("TaskErrors", 'Unable to read checksum file: {path}')
N("TaskErrors", 'Unable to read file: {detail}')
N("TaskErrors", 'Unable to write to folder {folder}: {reason}')
N("TaskErrors", 'SHA256 checksum failure: Expected {expected}, Actual {actual}')
N("TaskErrors", 'Downloaded file not found: {path}')
N("TaskErrors", 'Unable to fetch the latest release for {name}')
N("TaskErrors", 'Unable to fetch {name}/{branch}/{path}')
N("TaskErrors", 'Unable to download {name}/{branch}/{path}')
N("TaskErrors", 'Unable to download {name}/{tag}/{asset}')
N("TaskErrors", 'Unable to fetch PyPI package info: {package}')
N("TaskErrors", '{name} is not installed, please install it in Settings')

N("TaskErrors", 'Unable to retrieve version information')
N("TaskErrors", 'Checksum verification failed')
N("TaskErrors", 'No update is available for the current platform')
N("TaskErrors", '{path} is already taken by another file')
N("TaskErrors", 'Administrator authorization was not granted')
N("TaskErrors", 'No .app bundle was found in the DMG')

N("TaskErrors", 'Port {port} is occupied, please change port')
N("TaskErrors", 'No permission to listen on port {port}, please change port')
N("TaskErrors", 'Cannot listen on port {port}, see log for details')
N("TaskErrors", 'This link cannot be used for replacement')
N("TaskErrors", "The new link's content differs from the original task; please add a new task")
