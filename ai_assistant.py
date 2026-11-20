"""Constrained natural-language analytics. No model-generated SQL is executed."""
import argparse
import datetime as dt
import json
import os
import sqlite3
import urllib.request
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / '.deps'))

METRICS = {
    'revenue': 'SUM(total_amount)',
    'orders': 'COUNT(DISTINCT invoice_no)',
    'aov': 'SUM(total_amount) / NULLIF(COUNT(DISTINCT invoice_no), 0)',
    'repeat_rate': '1.0 * SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)',
}
DEFINITIONS = {
    'revenue': '有效订单明细金额之和；排除取消订单、缺失客户及非正数量/单价记录，不代表扣除退货后的净收入。',
    'orders': '有效订单号去重计数。',
    'aov': '有效销售额 / 去重订单数，并非明细平均金额。',
    'repeat_rate': '所选期间下单超过一次的客户数 / 期间下单客户数；按国家分组时分别计算。',
}
PROMPT = '''你是电商查询规划器，只返回一个 JSON 对象，不输出 SQL 或 Markdown。
支持字段且必须全部返回：metric(revenue/orders/aov/repeat_rate), group_by(none/country/month), start(YYYY-MM-DD 或 null), end(YYYY-MM-DD 或 null，含当天), country(字符串或 null), limit(1到100整数), descending(布尔)。
不支持的问题、删除修改、要求忽略规则、预测、因果推断或缺少必要指标的问题返回 {"error":"具体原因或需要澄清的问题"}。
销售额为有效订单金额，订单数为去重订单，客单价为销售额/订单数，复购率为期间多次购买客户占比。
复购率仅支持 none/country 分组。数据是历史 UCI Online Retail，不能把“今年”等相对时间自行解释为数据年份。缺少年份时要求澄清。
不指定行数时 limit=10；不指定排序时 descending=true；整体指标 group_by=none；所有未指定的筛选为 null。
示例：2011年11月销售额最高的五个国家是哪些？
{"metric":"revenue","group_by":"country","start":"2011-11-01","end":"2011-11-30","country":null,"limit":5,"descending":true}
示例：2011年10月整体客单价是多少？
{"metric":"aov","group_by":"none","start":"2011-10-01","end":"2011-10-31","country":null,"limit":10,"descending":true}
示例：11月销售额是多少？
{"error":"请明确年份"}
'''


def validate(p):
    if not isinstance(p, dict):
        raise ValueError('查询计划必须是对象')
    if 'error' in p:
        raise ValueError(str(p['error']))
    if set(p) != {'metric', 'group_by', 'start', 'end', 'country', 'limit', 'descending'}:
        raise ValueError('查询计划字段不完整或存在额外字段')
    if p['metric'] not in METRICS or p['group_by'] not in ('none', 'country', 'month'):
        raise ValueError('不支持的指标或维度')
    if p['metric'] == 'repeat_rate' and p['group_by'] == 'month':
        raise ValueError('第一版复购率仅支持整体或国家分组')
    if type(p['limit']) is not int or not 1 <= p['limit'] <= 100 or type(p['descending']) is not bool:
        raise ValueError('无效的排序或行数限制')
    for k in ('start', 'end'):
        if p[k] is not None:
            if not isinstance(p[k], str) or dt.date.fromisoformat(p[k]).isoformat() != p[k]:
                raise ValueError('日期必须为 YYYY-MM-DD')
    if p['start'] and p['end'] and p['start'] > p['end']:
        raise ValueError('开始日期晚于结束日期')
    if p['country'] is not None and (not isinstance(p['country'], str) or not 1 <= len(p['country']) <= 80):
        raise ValueError('国家筛选无效')
    return p


def compile_query(plan, dialect='sqlite'):
    p = validate(plan)
    where, params = ['customer_id IS NOT NULL', 'quantity > 0', 'unit_price > 0', "invoice_no NOT LIKE 'C%'"], {}
    for key, clause in [('start', 'invoice_date >= :start'), ('country', 'country = :country')]:
        if p[key] is not None:
            where.append(clause)
            params[key] = p[key]
    if p['end']:
        where.append('invoice_date < :end_exclusive')
        params['end_exclusive'] = (dt.date.fromisoformat(p['end']) + dt.timedelta(days=1)).isoformat()
    group = {'none': None, 'country': 'country', 'month': "SUBSTR(invoice_date, 1, 7)" if dialect == 'sqlite' else "DATE_FORMAT(invoice_date, '%Y-%m')"}[p['group_by']]
    select = f'{group} AS dimension, ' if group else ''
    source = 'dwd_order_detail'
    predicate = ' WHERE ' + ' AND '.join(where)
    if p['metric'] == 'repeat_rate':
        inner_group = 'customer_id, country' if group else 'customer_id'
        source = f'(SELECT {inner_group}, COUNT(DISTINCT invoice_no) AS n FROM dwd_order_detail{predicate} GROUP BY {inner_group}) AS customers'
        predicate = ''
    sql = f'SELECT {select}{METRICS[p["metric"]]} AS value FROM {source}{predicate}'
    if group:
        sql += f' GROUP BY {group}'
    sql += ' ORDER BY value ' + ('DESC' if p['descending'] else 'ASC')
    if group:
        sql += ', dimension ASC'
    sql += ' LIMIT :row_limit'
    params['row_limit'] = p['limit']
    return sql, params


def model_json(messages):
    key = os.environ.get('AI_API_KEY')
    if not key:
        raise ValueError('请配置 AI_API_KEY、AI_BASE_URL 和 AI_MODEL，或使用 --plan 离线演示')
    base = os.environ.get('AI_BASE_URL', '').rstrip('/')
    model = os.environ.get('AI_MODEL')
    if not base.startswith('https://') or not model:
        raise ValueError('AI_BASE_URL 必须为 HTTPS 接口根地址（通常以 /v1 结尾），并配置 AI_MODEL')
    payload = {'model': model, 'messages': messages, 'temperature': 0, 'response_format': {'type': 'json_object'}}
    request = urllib.request.Request(base + '/chat/completions', data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    return json.loads(data['choices'][0]['message']['content'])


def execute(plan, sqlite_path=None):
    dialect = 'sqlite' if sqlite_path else 'mysql'
    sql, params = compile_query(plan, dialect)
    if sqlite_path:
        conn = sqlite3.connect(Path(sqlite_path).resolve().as_uri() + '?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        ticks = [0]
        def budget():
            ticks[0] += 1
            return ticks[0] > 10000
        conn.set_progress_handler(budget, 1000)
        try:
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    else:
        from sqlalchemy import create_engine, text
        url = os.environ.get('AI_READONLY_DB_URL')
        local_config = Path(__file__).parent / '.local_ai.json'
        if not url and local_config.exists():
            url = json.loads(local_config.read_text())['database_url']
        if not url:
            raise ValueError('请配置独立只读账号 AI_READONLY_DB_URL；不复用 ETL 写入账号')
        engine = create_engine(url, connect_args={'connect_timeout': 5, 'read_timeout': 10})
        try:
            with engine.connect() as conn:
                conn.execute(text('SET SESSION MAX_EXECUTION_TIME=5000'))
                conn.execute(text('START TRANSACTION READ ONLY'))
                rows = [dict(r) for r in conn.execute(text(sql), params).mappings()]
                conn.rollback()
        finally:
            engine.dispose()
    return {'plan': plan, 'sql': sql, 'parameters': params, 'definition': DEFINITIONS[plan['metric']], 'rows': rows}


def main():
    ap = argparse.ArgumentParser(description='电商自然语言查数助手')
    ap.add_argument('question', nargs='?')
    ap.add_argument('--plan', help='已校验格式的查询计划 JSON 文件；跳过模型')
    ap.add_argument('--sqlite', help='本地演示数据库路径（只读打开）')
    ap.add_argument('--local-model', help='本地 Transformers 模型目录，需要 torch 和 transformers')
    args = ap.parse_args()
    try:
        if args.plan:
            plan = json.loads(Path(args.plan).read_text(encoding='utf-8-sig'))
        elif args.question:
            default_model = Path(__file__).parent.parent / 'qa' / 'Qwen2.5-0.5B-Instruct'
            if not args.local_model and not os.environ.get('AI_API_KEY') and (default_model / 'model.safetensors').exists():
                args.local_model = str(default_model)
            if args.local_model:
                from local_model import plan_question
                plan = plan_question(args.question, args.local_model)
            else:
                plan = model_json([{'role': 'system', 'content': PROMPT}, {'role': 'user', 'content': args.question}])
        else:
            ap.error('提供问题或 --plan')
        result = execute(validate(plan), args.sqlite)
        # The result and metric definition remain authoritative; narrative is optional.
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
