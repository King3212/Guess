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

# 常见红外吸收峰范围 (单位: cm^-1)
# 格式: (min, max, description)
COMMON_IR_PEAKS = [
    (3200, 3650, "O-H stretch (Alcohol, Phenol) - Broad"),
    (3300, 3500, "N-H stretch (Amine, Amide)"),
    (3000, 3100, "C-H stretch (Alkene, Aromatic)"),
    (2850, 3000, "C-H stretch (Alkane)"),
    (2500, 3000, "O-H stretch (Carboxylic Acid) - Very Broad"),
    (2100, 2260, "C≡C (Alkyne) or C≡N (Nitrile)"),
    (1670, 1780, "C=O stretch (Carbonyl: Ketone, Aldehyde, Ester, Acid)"),
    (1600, 1680, "C=C stretch (Alkene)"),
    (1450, 1600, "C=C stretch (Aromatic Ring)"),
    (1350, 1550, "N-O stretch (Nitro)"),
    (1000, 1300, "C-O stretch (Alcohol, Ether, Ester, Acid)"),
    (675, 1000, "C-H bend (Aromatic - out of plane)"),
    (600, 800, "C-Cl stretch (Alkyl Halide)"),
]


def analyze_ir(wavenumbers):
    """分析红外光谱波数，推断可能的官能团。"""
    wavenumbers = sorted(wavenumbers, reverse=True)
    findings = []

    for wn in wavenumbers:
        matched = []
        for min_wn, max_wn, desc in COMMON_IR_PEAKS:
            if min_wn <= wn <= max_wn:
                matched.append(desc)

        if matched:
            findings.append((wn, matched))
        else:
            # 指纹区通常在 1500 以下，比较复杂，这里简单标记
            if wn < 1500:
                findings.append((wn, ["Fingerprint Region (Complex)"]))
            else:
                findings.append((wn, ["Unknown"]))

    return findings


def processIR(wavenumbers, lang='zh'):
    """与 processMASS 风格一致的 IR 处理函数。"""
    for wn in wavenumbers:
        assert type(wn) == float or type(wn) == int, "Wavenumbers must be numbers."
        assert wn > 0, "Wavenumbers must be positive."

    results = analyze_ir(wavenumbers)

    result_text = tr("ir_result_title", lang, len(results))
    result_text += "\n".join(
        [
            tr("ir_wavenumber_line", lang, wn)
            + "\n".join([tr("ir_possible_line", lang, g) for g in groups])
            for wn, groups in results
        ]
    )

    print(result_text)
    return result_text


if __name__ == "__main__":
    print("请输入IR图中主要吸收峰(波谷)的波数 (以空格分隔):")
    try:
        line = sys.stdin.readline()
        if not line:
            sys.exit(1)
        parts = line.strip().split()
        wavenumbers = [float(p) for p in parts]
        processIR(wavenumbers)
    except ValueError:
        print("输入错误: 请确保输入的是数字。")
