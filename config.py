import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, 'data')
ACCOUNTS_DB = os.path.join(DATA_DIR, 'accounts.db')
NOTES_DB = os.path.join(DATA_DIR, 'notes.db')

BACKUP_DIR = os.path.join(BASE_DIR, 'backup')

STATIC_DESKTOP = os.path.join(BASE_DIR, 'static', 'desktop')
STATIC_MOBILE = os.path.join(BASE_DIR, 'static', 'mobile')

ACCESS_TOKEN_TTL = 3600
REFRESH_TOKEN_TTL = 604800
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

COLORS = ['blue', 'green', 'yellow', 'orange', 'red', 'gray']

SHARE_DEFAULT_LOGO_TEXT = '分享来自 Open Note'
SHARE_DEFAULT_WATERMARK = '备忘录'

MOBILE_UA_KEYWORDS = ['mobile', 'android', 'iphone', 'ipad', 'webos', 'blackberry', 'windows phone']
