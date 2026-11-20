"""Create a dedicated SELECT-only account; store its URL in ignored local config."""
import json
import secrets
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / '.deps'))
import yaml
import pymysql
from sqlalchemy.engine import URL

root = Path(__file__).parent
target = root / '.local_ai.json'
if target.exists():
    raise SystemExit('本地配置已存在；不修改账号或覆盖凭据。')
config = yaml.safe_load((root / 'config/config.yaml').read_text(encoding='utf-8-sig'))['database']
password = secrets.token_urlsafe(32)
conn = pymysql.connect(host=config['host'], port=int(config['port']), user=config['user'], password=str(config['password']), connect_timeout=5)
try:
    database = config['name']
    if not database.replace('_', '').isalnum():
        raise ValueError('数据库名含不支持的字符')
    with conn.cursor() as cursor:
        cursor.execute('CREATE USER %s@%s IDENTIFIED BY %s', ('ecommerce_ai_reader', 'localhost', password))
        cursor.execute(f'GRANT SELECT ON `{database}`.`dwd_order_detail` TO %s@%s', ('ecommerce_ai_reader', 'localhost'))
    url = URL.create('mysql+pymysql', username='ecommerce_ai_reader', password=password, host=config['host'], port=int(config['port']), database=database, query={'charset': 'utf8mb4'})
    target.write_text(json.dumps({'database_url': url.render_as_string(hide_password=False)}), encoding='utf-8')
    print('已创建仅能读取订单明细的账号；凭据保存到被 Git 忽略的本地配置，未输出密码。')
finally:
    conn.close()
