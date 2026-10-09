import os
import sys
import json
import time
import subprocess

# ensure requests
try:
    import requests
except Exception:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "--user"])
    import requests

MCP_URL = 'http://127.0.0.1:23120/mcp'
COLLECTION_KEY = 'GLN8YZG3'

CONFIG_PATH = os.path.join(os.getcwd(), 'Configs', 'config.json')

def safe_filename(name):
    return ''.join(c if c not in '<>:"/\\|?*' else '_' for c in name)

def main():
    # get collection items
    coll_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "get_collection_items", "arguments": {"collectionKey": COLLECTION_KEY, "mode": "preview"}}
    }
    r = requests.post(MCP_URL, json=coll_payload, timeout=30)
    r.raise_for_status()
    coll_j = r.json()
    raw_text = coll_j['result']['content'][0]['text']
    coll_obj = json.loads(raw_text)
    items = coll_obj.get('data', [])

    out_dir = os.path.join(os.getcwd(), 'References', 'mc_theory')
    os.makedirs(out_dir, exist_ok=True)

    query_text = (
        "请用中文提取本文提出的方法与关键观点，分条列出方法（methods）与关键观点（key_points），"
        "并给出一段不超过150字的章节级摘要（summary）；请只返回一个 JSON 对象，字段为："
        "title, summary, methods, key_points。"
    )

    # candidate section headings to probe when automatic structure extraction fails
    candidate_headings = [
        'Abstract', '摘要', 'Introduction', '引言', 'Background', '背景',
        'Method', 'Methods', '方法', 'Methodology', 'Materials and Methods',
        'Results', '结果', 'Discussion', '讨论', 'Conclusion', '结论', 'Conclusions', '参考文献'
    ]

    # DEBUG: only process the target item for now
    for it in items:
        key = it.get('key')
        # only debug NRCB53QN
        if key != 'NRCB53QN':
            continue
        title = it.get('title', '').strip()
        creators = it.get('creators', []) or []
        authors = ', '.join([f"{c.get('firstName','').strip()} {c.get('lastName','').strip()}".strip() for c in creators])
        doi = it.get('DOI', '')

        sem_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "semantic_search", "arguments": {"itemKey": key, "query": query_text}}
        }

        try:
            sr = requests.post(MCP_URL, json=sem_payload, timeout=120)
            sr.raise_for_status()
            srj = sr.json()
            sem_text = srj['result']['content'][0].get('text', '')
            try:
                parsed = json.loads(sem_text)
            except Exception:
                parsed = None
        except Exception as e:
            sem_text = json.dumps({"error": str(e)}, ensure_ascii=False)
            parsed = None

        fname = f"{key} - {title}.md"
        fname = safe_filename(fname)
        path = os.path.join(out_dir, fname)

        md = []
        md.append(f"# {title}")
        md.append("")
        md.append(f"- Zotero Key: {key}")
        md.append("")
        md.append(f"- Authors: {authors}")
        md.append("")
        md.append(f"- DOI: {doi}")
        md.append("")

        # STEP 1: try to obtain section structure by asking semantic_search to list sections
        struct_query = (
            "请用中文列出本文的章节结构（按出现顺序），仅返回一个 JSON 对象：{\"sections\": [\"章节标题1\", \"章节标题2\", ...]}，"
            "如果无法确定章节结构，请返回空数组。"
        )
        struct_payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "semantic_search", "arguments": {"itemKey": key, "query": struct_query}}}
        sections = []
        try:
            sr2 = requests.post(MCP_URL, json=struct_payload, timeout=60)
            sr2.raise_for_status()
            txt = sr2.json()['result']['content'][0].get('text', '')
            try:
                j = json.loads(txt)
                if isinstance(j, dict) and 'sections' in j and isinstance(j['sections'], list):
                    sections = [s for s in j['sections'] if isinstance(s, str) and s.strip()]
            except Exception:
                # fallback: try to extract section-like titles from the returned text heuristically
                pass
        except Exception:
            pass

        # fallback: probe candidate headings one-by-one and detect presence/content
        if not sections:
            for h in candidate_headings:
                probe_q = f"请在本文中查找是否存在章节标题'{h}'，若存在返回该章节的摘要或相关段落（不超过1000字），否则返回空字符串。只返回 JSON: { { 'section': h, 'content': '...' } }"
                probe_payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "semantic_search", "arguments": {"itemKey": key, "query": probe_q}}}
                try:
                    pr = requests.post(MCP_URL, json=probe_payload, timeout=30)
                    pr.raise_for_status()
                    ptxt = pr.json()['result']['content'][0].get('text', '')
                    # crude check: if any Chinese characters or English words present, consider it found
                    if ptxt and any(c.isalpha() or ord(c) > 127 for c in ptxt):
                        sections.append(h)
                except Exception:
                    continue

        # STEP 2: for each detected section, request methods and key points within that section
        section_results = []
        for sec in sections:
            sec_q = (
                f"请针对本文中章节'{sec}'，用中文分条列出本节提出的方法（methods）和关键观点（key_points），并给出不超过100字的本节摘要（summary）。"
                " 请仅返回一个 JSON 对象，字段为: summary, methods, key_points。"
            )
            sec_payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "semantic_search", "arguments": {"itemKey": key, "query": sec_q}}}
            sec_parsed = None
            sec_text = ''
            try:
                sr3 = requests.post(MCP_URL, json=sec_payload, timeout=60)
                sr3.raise_for_status()
                sec_content_obj = sr3.json()['result']['content'][0]
                sec_text = sec_content_obj.get('text', '')
                # try parse as JSON if the retrieval actually returned structured JSON
                try:
                    parsed_search = json.loads(sec_text)
                except Exception:
                    parsed_search = None

                # Intercept empty retrievals: if parsed_search indicates zero results, skip LLM
                empty_retrieval = False
                if parsed_search is not None:
                    # check data array or metadata.resultCount
                    data_arr = parsed_search.get('data') if isinstance(parsed_search, dict) else None
                    meta = parsed_search.get('metadata') if isinstance(parsed_search, dict) else None
                    # if results are empty or they don't reference the target item, treat as empty
                    if (isinstance(data_arr, list) and len(data_arr) == 0) or (isinstance(meta, dict) and meta.get('resultCount', 1) == 0):
                        empty_retrieval = True
                    else:
                        # if returned data are other items (not the item key), then it's a library search, not item content
                        try:
                            has_own = any((d.get('itemKey') == key) for d in (data_arr or []))
                        except Exception:
                            has_own = False
                        if not has_own and isinstance(data_arr, list) and len(data_arr) > 0:
                            empty_retrieval = True
                else:
                    # if sec_text is empty or too short, consider empty
                    if not sec_text or len(sec_text.strip()) < 50:
                        empty_retrieval = True

                if empty_retrieval:
                    print(f"[DEBUG] semantic_search returned empty for item {key}, section {sec}; skipping LLM call.")
                    sec_parsed = None
                else:
                    # if parsed_search already is a directly usable JSON with summary/methods, use it
                    if isinstance(parsed_search, dict) and any(k in parsed_search for k in ('summary', 'methods', 'key_points')):
                        sec_parsed = parsed_search
                    else:
                        # leave sec_parsed None so downstream will trigger LLM call
                        sec_parsed = None
            except Exception:
                sec_text = ''

            # If semantic_search returned search-mode matchedChunks text, extract top chunk and call LLM
            # Only call LLM if we have non-empty retrieval and sec_parsed still None
            if sec_parsed is None and sec_text:
                # try to extract the most relevant matched chunk text
                def extract_top_chunk(text):
                    import re
                    # find all "text": "..." occurrences inside matchedChunks blocks
                    pattern = re.compile(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"', re.S)
                    matches = pattern.findall(text)
                    if not matches:
                        return text
                    # unescape JSON string escapes
                    unescaped = [json.loads('"' + m + '"') for m in matches]
                    # pick the longest chunk
                    unescaped.sort(key=lambda s: len(s), reverse=True)
                    return unescaped[0]

                top_chunk = extract_top_chunk(sec_text)

                # load config for LLM API key
                config = {}
                try:
                    with open(CONFIG_PATH, 'r', encoding='utf-8') as cf:
                        config = json.load(cf)
                except Exception:
                    config = {}

                # ensure OpenAI SDK is installed
                try:
                    from openai import OpenAI
                except Exception:
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openai', '--user'])
                    from openai import OpenAI

                base_url = config.get('base_url', 'https://api.deepseek.com')
                api_key = config.get('api_key') or os.environ.get('DEEPSEEK_API_KEY')

                def call_llm_stream(prompt, api_key, base_url, model='deepseek-chat'):
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    # stream=True to receive incremental events; we'll merge them
                    stream_resp = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.0,
                        stream=True,
                    )

                    parts = []
                    try:
                        for chunk in stream_resp:
                            # chunk may be a dict-like object
                            try:
                                # OpenAI-like event: {'choices': [{'delta': {'content': '...'}}]}
                                choices = chunk.get('choices') if isinstance(chunk, dict) else None
                            except Exception:
                                choices = None

                            content_piece = ''
                            if choices:
                                c0 = choices[0]
                                # delta style
                                delta = c0.get('delta') if isinstance(c0, dict) else None
                                if delta and isinstance(delta, dict):
                                    content_piece = delta.get('content', '')
                                else:
                                    # older style: message.content
                                    msg = c0.get('message')
                                    if isinstance(msg, dict):
                                        content_piece = msg.get('content', '')
                            # append if any
                            if content_piece:
                                parts.append(content_piece)
                    except Exception:
                        # fallback: try to stringify stream_resp
                        try:
                            txt = str(stream_resp)
                            parts.append(txt)
                        except Exception:
                            pass

                    full = ''.join(parts)
                    return full

                # build prompt (assemble parts to avoid complex escaping)
                prompt_parts = [
                    "请用中文基于下面的检索片段，严格返回一个 JSON 对象，字段为:\n",
                    '{"summary":"不超过100字的本节摘要", "methods": ["方法短句"], "key_points": ["关键观点短句"]}\n',
                    "注意：1) 只返回有效的 JSON，不要包含任何额外说明或代码块。2) 如果信息不足，尽量从文本中归纳，不要臆造具体的引用细节。\n\n",
                    "检索片段：\n---BEGIN CHUNK---\n",
                    top_chunk,
                    "\n---END CHUNK---\n\n",
                    f"文章元数据：标题：{title}；作者：{authors}\n",
                ]
                prompt = ''.join(prompt_parts)

                llm_text = ''
                try:
                    if api_key:
                        llm_text = call_llm_stream(prompt, api_key, base_url)
                    else:
                        llm_text = ''
                except Exception:
                    llm_text = ''

                # try parse LLM JSON
                if llm_text:
                    try:
                        sec_parsed = json.loads(llm_text)
                    except Exception:
                        # try to extract first JSON object
                        import re
                        m = re.search(r"\{[\s\S]*\}", llm_text)
                        if m:
                            try:
                                sec_parsed = json.loads(m.group(0))
                            except Exception:
                                sec_parsed = None
                        else:
                            sec_parsed = None

                # record raw llm text in sec_text for auditing
                if llm_text:
                    sec_text += '\n\n[LLM_RESPONSE]\n' + llm_text
            # assemble section entry
            entry = {'section': sec, 'summary': '', 'methods': [], 'key_points': [], 'raw': sec_text}
            if isinstance(sec_parsed, dict):
                entry['summary'] = sec_parsed.get('summary', '')
                entry['methods'] = sec_parsed.get('methods', []) if isinstance(sec_parsed.get('methods', []), list) else [sec_parsed.get('methods', '')]
                entry['key_points'] = sec_parsed.get('key_points', []) if isinstance(sec_parsed.get('key_points', []), list) else [sec_parsed.get('key_points', '')]
            else:
                # fallback: extract sentences from sec_text using keywords
                import re
                sents = re.split(r'[。\n；;]+', sec_text)
                kws = ['方法', '算法', '提出', '采用', '重要性采样', 'null-collision', '路径', '随机']
                for s in sents:
                    ss = s.strip()
                    if not ss:
                        continue
                    if any(k in ss for k in kws):
                        if len(entry['methods']) < 8 and any(k in ss for k in ['方法', '算法', '采样', '随机', '路径']):
                            entry['methods'].append(ss)
                        elif len(entry['key_points']) < 8:
                            entry['key_points'].append(ss)
                if not entry['summary']:
                    entry['summary'] = sec_text[:400]

            section_results.append(entry)

        # write sections to markdown
        md.append('## 章节结构（检测到的顺序）')
        md.append('')
        if sections:
            for s in sections:
                md.append(f"- {s}")
        else:
            md.append('- （未检测到明确章节结构）')
        md.append('')

        for ent in section_results:
            md.append(f"### {ent['section']}")
            md.append('')
            md.append('**本节摘要：**')
            md.append('')
            md.append(ent['summary'] if ent['summary'] else '（无）')
            md.append('')
            md.append('**本节方法（methods）：**')
            md.append('')
            if ent['methods']:
                for m in ent['methods']:
                    md.append(f"- {m}")
            else:
                md.append('- （无）')
            md.append('')
            md.append('**本节关键观点（key_points）：**')
            md.append('')
            if ent['key_points']:
                for kp in ent['key_points']:
                    md.append(f"- {kp}")
            else:
                md.append('- （无）')
            md.append('')

        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))

        print(f"Wrote: {path}")
        time.sleep(0.3)

    print(f"Completed: generated files in {out_dir}")

if __name__ == '__main__':
    main()
