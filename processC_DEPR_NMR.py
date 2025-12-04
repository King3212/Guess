import sys
import json
import os

def load_locales():
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, "locales.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

LOCALES = load_locales()

def tr(key, lang='zh', *args):
    lang_data = LOCALES.get(lang, {})
    text = lang_data.get(key, key)
    if args:
        try:
            return text.format(*args)
        except:
            return text
    return text

# 常见 13C 化学位移范围 (ppm)
COMMON_C_SHIFTS = [
    (0, 40, "Alkyl (R-CH3, R-CH2-R, R3CH, Cq)"),
    (40, 80, "C-O (Alcohol, Ether) or C-N (Amine) or C-X (Halide)"),
    (65, 90, "C≡C (Alkyne)"),
    (100, 150, "C=C (Alkene) or Aromatic"),
    (115, 125, "C≡N (Nitrile)"),
    (160, 185, "C=O (Carboxylic Acid, Ester, Amide)"),
    (190, 220, "C=O (Aldehyde, Ketone)"),
]


def analyze_c_nmr(peaks):
    """分析 13C/DEPT 数据: peaks 为 (shift, type_str) 列表"""
    findings = []
    peaks = sorted(peaks, key=lambda x: x[0])

    for shift, c_type in peaks:
        possible_groups = []
        for min_s, max_s, desc in COMMON_C_SHIFTS:
            if min_s <= shift <= max_s:
                possible_groups.append(desc)

        if not possible_groups:
            possible_groups.append("Unknown Region")

        findings.append({"shift": shift, "type": c_type, "groups": possible_groups})
    return findings


def interpret_dept_data(bb_peaks, dept90_shifts, dept135_peaks, tolerance=1.0):
    """
    解析 13C/DEPT 原始数据（新版输入格式），推断碳类型并保留峰数。

    参数:
    - bb_peaks: list of [shift, count]，count 可以是整数或字符串（如 ">1"）。
    - dept90_shifts: list of shift（仅列表，表示该位移在 DEPT-90 上出现）
    - dept135_peaks: list of [shift, polarity]，polarity 为 1 或 -1。

    返回:
    - list of [shift, type_code, count]
      type_code: 3=CH3, 2=CH2, 1=CH, 0=Cq
    """
    resolved = []

    # 标准化并排序 bb_peaks
    norm_bb = []
    for item in bb_peaks:
        if not item:
            continue
        try:
            shift_bb = float(item[0])
        except Exception:
            continue
        count = item[1] if len(item) > 1 else 1
        # 尝试把 count 转为 int，否则保留原样（如 ">1"）
        try:
            count_val = int(count)
        except Exception:
            count_val = str(count)
        norm_bb.append((shift_bb, count_val))

    norm_bb = sorted(norm_bb, key=lambda x: x[0])

    # 便于匹配的 dept90 set（只要有位移就视为存在）
    dept90_set = [float(s) for s in dept90_shifts] if dept90_shifts is not None else []

    # dept135 标准化为 (shift, polarity)
    norm_135 = []
    for item in dept135_peaks:
        try:
            s = float(item[0])
            p = int(item[1])
            norm_135.append((s, p))
        except Exception:
            continue

    for shift_bb, count_val in norm_bb:
        # 寻找是否在 DEPT-90 存在（按容差匹配）
        found90 = False
        for s in dept90_set:
            if abs(s - shift_bb) <= tolerance:
                found90 = True
                break

        # 寻找 DEPT-135 对应峰及其极性
        found135_pol = 0
        min_diff = float('inf')
        for s, p in norm_135:
            diff = abs(s - shift_bb)
            if diff <= tolerance and diff < min_diff:
                min_diff = diff
                found135_pol = p

        # 根据 DEPT 规则推断类型
        # 优先 DEPT-90 为 CH
        if found90:
            type_code = 1  # CH
        else:
            if found135_pol == -1:
                type_code = 2  # CH2
            elif found135_pol == 1:
                type_code = 3  # CH3
            else:
                type_code = 0  # Cq

        resolved.append([shift_bb, type_code, count_val])

    return resolved


def processC_DEPR_NMR(data, lang='zh'):
    """与 processMASS/processIR/processH_NMR 风格一致的 13C/DEPT 处理函数。

    输入格式（仅支持新格式）：
      - data 为 dict: {'bb': [[shift,count],...], 'dept90':[shift,...], 'dept135':[[shift,polarity],...]}

    返回格式：
      - 字符串: "化学位移xx ppm；类型为：CH3；数量：1；\n ......"
    """
    if not isinstance(data, dict):
        raise ValueError("Input data must be a dictionary with keys 'bb', 'dept90', 'dept135'.")

    bb = data.get('bb', [])
    dept90 = data.get('dept90', [])
    dept135 = data.get('dept135', [])
    
    # 解析数据
    peaks_resolved = interpret_dept_data(bb, dept90, dept135)
    
    # 构建返回字符串
    type_map = {3: 'CH3', 2: 'CH2', 1: 'CH', 0: 'Cq'}
    result_lines = []
    
    # 同时构建用于 analyze_c_nmr 的列表以便打印详细分析（保留原有功能作为控制台输出）
    peaks_for_analysis = []

    for shift, tcode, count in peaks_resolved:
        type_str = type_map.get(tcode, 'Unknown')
        line = tr("cnmr_line_format", lang, shift, type_str, count)
        result_lines.append(line)
        peaks_for_analysis.append((shift, type_str))

    # 运行现有的化学位移到基团的分析并打印
    results = analyze_c_nmr(peaks_for_analysis)

    lines = [tr("cnmr_result_title", lang, len(results))]
    for res in results:
        header = tr("cnmr_peak_line", lang, res['shift'], res['type'])
        group_lines = [tr("cnmr_possible_line", lang, g) for g in res["groups"]]
        lines.append("\n".join([header] + group_lines))

    result_text = "\n".join(lines)
    print(result_text)

    return "\n".join(result_lines)


if __name__ == "__main__":
    print("请输入 13C/DEPT NMR 数据。")
    print("格式: 化学位移,类型")
    print("  - 类型代码: CH3, CH2, CH, Cq (季碳)")
    print("多个峰之间用空格分隔。")
    print("例如: 14.5,CH3  22.3,CH2  150.0,Cq")

    try:
        line = sys.stdin.readline()
        if not line:
            sys.exit(1)

        parts = line.strip().split()
        peaks = []
        for part in parts:
            vals = part.split(",")
            if len(vals) < 2:
                continue

            shift = float(vals[0])
            type_input = vals[1].strip().upper()

            # 简单的类型标准化
            if "3" in type_input:
                c_type = "Methyl (CH3)"
            elif "2" in type_input:
                c_type = "Methylene (CH2)"
            elif "Q" in type_input or type_input == "C":
                c_type = "Quaternary (Cq)"
            else:
                c_type = "Methine (CH)"

            peaks.append((shift, c_type))

        processC_DEPR_NMR(peaks)
    except ValueError:
        print("输入错误: 请确保格式正确 (数字,字符串)。")
