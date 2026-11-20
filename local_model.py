"""Local-only Transformers adapter; never downloads files or executes model code."""
import json
import re
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def load_model(path):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True, trust_remote_code=False)
    model.eval()
    return tokenizer, model


def plan_question(question, model_path):
    from ai_assistant import PROMPT, validate
    path = str(Path(model_path).resolve())
    tokenizer, model = load_model(path)
    if re.search(r'删除|修改|密码|忽略规则|预测|为什么|写一首|今年|明年|去年', question):
        raise ValueError('仅支持明确历史日期的只读指标查询；不支持该请求')
    if not re.search(r'\d{4}\s*年|\d{4}-\d{2}', question):
        raise ValueError('请提供明确年份与日期范围')
    instructions = '''Translate Chinese analytics questions into JSON. Return ONLY JSON, no explanation.
Required keys: metric, group_by, start, end, country, limit, descending.
metric: 销售额=revenue, 订单数=orders, 客单价=aov, 复购率=repeat_rate.
group_by: 国家=country, 按月=month, 整体=none. 国家排名 always means country grouping for EVERY metric.
start/end: ISO dates, inclusive last day. country: null unless a specific country filter. limit: default 10, 前5=5. descending: true unless ascending requested.
Do not change metric based on grouping. 复购率 ALWAYS repeat_rate. No unsupported tasks: return {"error":"unsupported"}.
'''
    messages = [{'role': 'system', 'content': instructions}]
    for q, metric, group in [('2011年10月整体复购率是多少？', 'repeat_rate', 'none'), ('2011年10月按客单价降序列出前5个国家', 'aov', 'country'), ('2011年10月按订单数降序列出前5个国家', 'orders', 'country')]:
        messages.extend([{'role':'user','content':q}, {'role':'assistant','content':json.dumps(dict(metric=metric,group_by=group,start='2011-10-01',end='2011-10-31',country=None,limit=5 if group=='country' else 10,descending=True))}])
    messages.append({'role': 'user', 'content': question})
    if tokenizer.chat_template:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        # Base checkpoints can be benchmarked but are not instruction-tuned.
        prompt = PROMPT + '\n问题：' + question + '\nJSON：'
    inputs = tokenizer(prompt, return_tensors='pt')
    import torch
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=256, do_sample=False, pad_token_id=tokenizer.eos_token_id)
    raw = tokenizer.decode(output[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
    if raw.startswith('```') and raw.endswith('```'):
        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    try:
        plan = validate(json.loads(raw))
        for label, metric in [('销售额','revenue'), ('订单数','orders'), ('客单价','aov'), ('复购率','repeat_rate')]:
            if label in question and plan['metric'] != metric:
                raise ValueError('模型指标与问题不一致')
        if '国家' in question and plan['group_by'] != 'country':
            raise ValueError('模型分组与问题不一致')
        return plan
    except (ValueError, TypeError) as exc:
        raise ValueError('本地模型未返回有效查询计划，不执行查询；请使用 Instruct 模型并评测') from exc
