from processC_DEPR_NMR import processC_DEPR_NMR
from processH_NMR import processH_NMR
from processIR import processIR
from processMASS import processMASS
import sys
import json
from openai import OpenAI
def gen_prompt_1(datas):
    # 一个生成基团列表的prompt生成
    prompt = f"""你是一个有经验的有机化学家，擅长通过质谱 (MASS)、红外光谱 (IR)、氢核磁共振 (1H NMR) 和碳核
                 磁共振 (13C/DEPT NMR) 数据来推断有机分子可能的基团列表。\n"""
    for data in datas:
        prompt += data + "\n"
    prompt += "请综合以上信息，给出可能的基团列表和几个可能的化学式，确保化学式的相对分子质量与MASS推测的分子质量相符，无需给出理由。\n"
    
    return prompt

def gen_prompt_2(findings):
    # 一个生成分子式和结构的prompt生成
    prompt = f"""你是一个有经验的有机化学家，擅长通过质谱 (MASS)、红外光谱 (IR)、氢核磁共振 (1H NMR) 和碳核
                 磁共振 (13C/DEPT NMR) 等数据来推断有机分子的可能存在的基团并推断该有机分子可能的结构。\n"""
    if isinstance(findings, list):
        prompt += "\n".join(findings)
    else:
        prompt += findings
    prompt += "请综合以上信息，推断该有机分子可能的结构,给出物质名称和结构简式，无需给出理由。\n"
    
    return prompt
    
def ask_AI(prompt, *, api_config_path: str = "API.json", api_key: str = None,
           base_url: str = None, model: str = None, on_delta=None, on_thinking=None, thinking:str = "enabled") -> str:
    """调用 AI 模型，支持流式回调，并返回完整字符串。

    参数优先级：显式参数 > 配置文件。
    on_delta: 可选回调函数，签名为 on_delta(text: str)，每次增量输出调用一次。
    on_thinking: 可选回调函数，签名为 on_thinking(text: str)，每次增量思考内容调用一次。
    thinking: 控制思考内容的显示，"enabled" 或 "disabled"。
    """
    config = {}
    if api_config_path:
        try:
            with open(api_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except FileNotFoundError:
            config = {}

    api_key = api_key or config.get("api_key")
    base_url = base_url or config.get("base_url")
    model = model or config.get("model")

    if not api_key or not base_url or not model:
        raise ValueError("API 配置不完整，请提供 api_key、base_url 和 model。")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        stream=True,
        extra_body={"thinking": {"type": thinking}},
    )

    full_text_parts = []
    for chunk in completion:
        # 尝试获取思考内容 (DeepSeek 等模型使用 reasoning_content)
        reasoning = getattr(chunk.choices[0].delta, 'reasoning_content', None)
        if reasoning:
            if on_thinking:
                on_thinking(reasoning)
        
        delta = chunk.choices[0].delta.content or ""
        if not delta:
            continue
        full_text_parts.append(delta)
        if on_delta is not None:
            on_delta(delta)
        # 兼容原先命令行使用
        print(delta, end="", flush=True)

    return "".join(full_text_parts)
        
def get_data_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def gen_datas(data):
    datas = []
    # 质谱：JSON: "mass" -> processMASS: 列表[数值]
    if "mass" in data:
        mass_data = data["mass"]
        mass_result = processMASS(mass_data)
        datas.append(mass_result)

    # IR：JSON: "ir" -> processIR: 列表[数值]
    if "ir" in data:
        ir_data = data["ir"]
        ir_result = processIR(ir_data)
        datas.append(ir_result)

    # 1H NMR：JSON: "h_nmr" (dict 列表) -> processH_NMR: 列表[(shift, area, mult)]
    if "h_nmr" in data:
        h_nmr_raw = data["h_nmr"]
        h_nmr_data = []
        for item in h_nmr_raw:
            shift = float(item["shift"])
            area = item.get("area")
            mult = int(item.get("multiplicity", 1))
            h_nmr_data.append((shift, area, mult))
        h_nmr_result = processH_NMR(h_nmr_data)
        datas.append(h_nmr_result)

    # 13C/DEPT NMR：JSON: "c_nmr" (dict 列表) -> processC_DEPR_NMR: 列表[(shift, type_str)]
    if "c_nmr" in data:
        c_nmr_raw = data["c_nmr"]
        
        if isinstance(c_nmr_raw, dict):
            # 新格式：直接传递包含 bb, dept90, dept135 的字典
            c_dept_nmr_result = processC_DEPR_NMR(c_nmr_raw)
            if isinstance(c_dept_nmr_result, list):
                datas.append(f"13C/DEPT NMR Data: {json.dumps(c_dept_nmr_result)}")
            else:
                datas.append(c_dept_nmr_result)
    return datas
""" 
    data = get_data_from_json(file_path)
    datas = gen_datas(data)
    证据链
    
    prompt_1 = gen_prompt_1(datas)
    parts = ask_AI(prompt_1)
    AI 推测基团
    
    findings = parts + "\n以下是证据链:\n"
    for data in datas:
        findings += data + "\n" 
    prompt_2 = gen_prompt_2(findings)
    ask_AI(prompt_2)
    AI 推测分子式和结构
"""

if __name__ == "__main__":
    file_path = "input_template.json"  # 替换为实际 JSON 文件路径
    data = get_data_from_json(file_path)
    datas = gen_datas(data)
    print("=== 证据链 ===")
    findings_chain = "\n".join(datas)

    # promt_1 = gen_prompt_1(datas)
    # print("=== 基团推测 ===")
    # fg_result = ask_AI(promt_1)
    
    

