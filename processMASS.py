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

# 常见碎片及其质量
COMMON_FRAGMENTS = {
    14: "CH2 (Methylene)",
    15: "CH3 (Methyl)",
    16: "NH2 (Amino)",
    17: "OH (Hydroxyl)",
    18: "H2O (Water)",
    28: "CO or C2H4",
    29: "C2H5 (Ethyl) or CHO",
    31: "OCH3 (Methoxy)",
    41: "C3H5 (Allyl)",
    43: "C3H7 (Propyl) or C2H3O (Acetyl)",
    45: "COOH (Carboxyl) or OCH2CH3 (Ethoxy)",
    57: "C4H9 (Butyl)",
    77: "C6H5 (Phenyl)",
    91: "C7H7 (Benzyl/Tropylium)"
    
}

def analyze_masses(masses):
    """
    分析质谱数据，通过质量差推断可能的基团。
    """
    masses = sorted(masses, reverse=True)
    findings = []
    
    # 计算两两之间的差值
    for i in range(len(masses)):
        for j in range(i + 1, len(masses)):
            diff = round(masses[i] - masses[j])
            if diff in COMMON_FRAGMENTS:
                findings.append((diff, COMMON_FRAGMENTS[diff], masses[i], masses[j]))
    
    return findings

def processMASS(masses, lang='zh'):
        for mass in masses:
            assert type(mass) == float or type(mass) == int, "Mass values must be numbers." 
            assert mass > 0, "Mass values must be positive."
        
        results = analyze_masses(masses)
        
        result_text = tr("mass_result_title", lang, len(results))
        result_text += tr("mass_possible_mw", lang, max(masses))
        result_text += "\n".join([tr("mass_diff_line", lang, diff, group, m1, m2) for diff, group, m1, m2 in results])
        print(result_text)
        return result_text
    
if __name__ == "__main__":
    print("请输入质谱图中主要峰的质量 (以空格分隔):")
    try:
        # 从标准输入读取
        line = sys.stdin.readline()
        if not line:
            exit(1)
        parts = line.strip().split()
        masses = [float(p) for p in parts]
        
        processMASS(masses)
            
    except ValueError:
        print("输入错误: 请确保输入的是数字。")