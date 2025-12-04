import sys

# 常见 H-NMR 化学位移范围 (ppm)
COMMON_SHIFTS = [
    (0.5, 2.0, "Alkyl C-H (R-CH3, R-CH2-R, R3CH)"),
    (2.0, 2.5, "Alpha to Carbonyl (H-C-C=O) or Benzylic (Ar-C-H)"),
    (2.5, 4.5, "Alpha to Electronegative Atom (H-C-O, H-C-N, H-C-X)"),
    (4.5, 6.5, "Vinylic (C=C-H)"),
    (6.5, 8.5, "Aromatic (Ar-H)"),
    (9.0, 10.0, "Aldehyde (CHO)"),
    (10.0, 13.0, "Carboxylic Acid (COOH) or Phenol (Ar-OH)"),
]


def get_multiplicity_desc(n):
    """根据重峰数返回描述"""
    if n == 1:
        return "Singlet (s, 0 neighbors)"
    if n == 2:
        return "Doublet (d, 1 neighbor)"
    if n == 3:
        return "Triplet (t, 2 neighbors)"
    if n == 4:
        return "Quartet (q, 3 neighbors)"
    if n == 5:
        return "Quintet (4 neighbors)"
    if n == 6:
        return "Sextet (5 neighbors)"
    if n == 7:
        return "Septet (6 neighbors)"
    if n > 1:
        return f"Multiplet (m, ~{n-1} neighbors)"
    return "Unknown"


def analyze_h_nmr(peaks):
    """分析 H-NMR 数据: peaks 为 (shift, area, multiplicity) 列表"""
    findings = []
    peaks = sorted(peaks, key=lambda x: x[0])

    for shift, area, mult in peaks:
        possible_groups = []
        for min_s, max_s, desc in COMMON_SHIFTS:
            if min_s <= shift <= max_s:
                possible_groups.append(desc)

        if not possible_groups:
            possible_groups.append("Unknown Region")

        findings.append(
            {
                "shift": shift,
                "area": area,
                "mult": mult,
                "mult_desc": get_multiplicity_desc(mult),
                "groups": possible_groups,
            }
        )
    return findings


def processH_NMR(peaks):
    """与 processMASS/processIR 风格一致的 H-NMR 处理函数。"""
    # 基本断言检查
    for p in peaks:
        assert isinstance(p, (list, tuple)) and len(p) == 3, "Each peak must be (shift, area, multiplicity)."
        shift, area, mult = p
        assert isinstance(shift, (int, float)), "Shift must be numeric."
        assert isinstance(mult, int), "Multiplicity must be integer."

    results = analyze_h_nmr(peaks)

    # 构造输出字符串
    lines = [f"H_NMR分析结果 (共 {len(results)} 个峰):"]
    for res in results:
        header = f"位移 {res['shift']} ppm (面积: {res['area']}, {res['mult_desc']}):"
        group_lines = [f"  - 可能为: {g}" for g in res["groups"]]
        lines.append("\n".join([header] + group_lines))

    result_text = "\n".join(lines)
    print(result_text)
    return result_text


if __name__ == "__main__":
    print("请输入H-NMR数据。")
    print("格式: 化学位移[,峰面积][,峰形]")
    print("多个峰之间用空格分隔。例如: 1.2,3,3 2.4 7.1,,1")
    print("(注: 面积可以缺失或留空，峰形 1=s, 2=d, 3=t, 4=q, etc.)")

    try:
        line = sys.stdin.readline()
        if not line:
            sys.exit(1)

        parts = line.strip().split()
        peaks = []
        for part in parts:
            vals = part.split(",")
            if not vals or not vals[0]:
                continue

            shift = float(vals[0])

            # 面积可以缺失或为空字符串，此时用 float('nan') 标记缺失
            if len(vals) > 1 and vals[1] not in ("", None):
                area = float(vals[1])
            else:
                area = float("nan")

            mult = int(vals[2]) if len(vals) > 2 and vals[2] else 1

            peaks.append((shift, area, mult))

        processH_NMR(peaks)
    except ValueError:
        print("输入错误: 请确保格式正确 (数字)。")
