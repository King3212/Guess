# 综合光谱解析程序 (Guess)

[English README](README.md)

## 简介

这是一个基于 AI 的有机分子结构推断工具。它能够综合分析质谱 (Mass)、红外光谱 (IR)、氢谱 (1H NMR) 和碳谱 (13C/DEPT NMR) 数据，利用大语言模型（如 GPT-4, Qwen, DeepSeek 等）逐步推断分子的官能团和最终结构。

### 功能特点

*   **多谱综合分析**：支持 Mass, IR, 1H NMR, 13C NMR (BB/DEPT) 数据整合。
    > 如需添加更多种类数据，请在 Issue 中提供示例数据及解读方法。
*   **图形用户界面 (GUI)**：提供直观的 Tkinter 界面，方便操作。
*   **分步推断**：
    *   **Step 1**: 数据预处理与标准化。
    *   **Step 2**: AI 推测可能的官能团。
    *   **Step 3**: AI 综合证据链推断分子式与结构简式。
*   **自定义 AI 配置**：支持 OpenAI 兼容接口，可自定义 Base URL 和 Model。

## 使用说明

### 安装

#### 从源代码安装 (Linux / MacOS / Windows)

1.  确保已安装 Python 3.8 或更高版本。
2.  安装依赖库：
    ```bash
    pip install -r requirements.txt
    ```
    *(注：GUI 使用 Python 内置的 `tkinter`，通常无需额外安装)*
3.  运行 `gui.py` 启动图形界面：
    ```bash
    python gui.py
    ```

#### 使用二进制文件 (Windows 推荐)

1.  下载并解压 `Guess-Windows-x86-64.zip`。
2.  双击 `Guess.exe` 即可运行。

### 配置 API

在程序界面的 "AI API 配置" 区域填写你的大模型 API 信息：
*   **Base URL**: API 服务地址 (例如 `https://api.openai.com/v1` 或其他兼容地址)。
*   **API Key**: 你的 API 密钥 (请勿向他人泄露)。
*   **Model**: 使用的模型名称 (建议使用逻辑推理能力强的模型)。

> **提示**：
> *   该程序为 Step 2 和 Step 3 提供了使用不同模型的功能。
> *   可以采用 UI 提供的 API 编辑功能，也可以打开程序所在目录 (默认保存目录)，创建并修改 `API.json`。
> *   `API.json` 示例如下：
>     ```json
>     {
>         "api_key": "sk-XXXXXXXX",
>         "base_url_1": "https://api.deepseek.com/v3.2_speciale_expires_on_20251215",
>         "base_url_2": "https://api.deepseek.com/v1",
>         "model_1": "deepseek-reasoner",
>         "model_2": "deepseek-reasoner"
>     }
>     ```
>     示例中的 DeepSeek API 可以在 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取，请注意自行承担费用。

### 运行分析

1.  点击 "选择文件" 加载包含光谱数据的 JSON 文件，加载完成后亦可对文件内容进行修改和保存。
2.  你可以点击 "一键分析" 自动运行全流程。
3.  或者按步骤点击 "Step1 分析" -> "Step2 分析" -> "Step3 分析" 查看中间结果。

## 数据输入说明 (JSON)

程序支持通过 JSON 文件批量输入光谱数据。请参考以下格式编写 JSON 文件（例如 `input.json`）。

### JSON 结构示例

```json
{
  "mass": [120.1, 105.0, 77.0],
  "ir": [3050, 2950, 1710, 1600, 1450],
  "h_nmr": [
    {"shift": 7.2, "area": 5, "multiplicity": 1},
    {"shift": 2.3, "area": 3, "multiplicity": 1}
  ],
  "c_nmr": {
    "bb": [
      [170.5, ">1"],
      [135.0, "1"],
      [128.5, "1"],
      [21.0, "1"]
    ],
    "dept90": [128.5],
    "dept135": [
      [128.5, 1],
      [21.0, 1]
    ]
  }
}
```

### 字段说明

#### 1. 质谱 (mass)
*   **类型**: 数字数组 `[float]`
*   **说明**: 输入质谱中观察到的主要离子峰的质荷比 (m/z)。通常包含分子离子峰和主要碎片峰。

#### 2. 红外光谱 (ir)
*   **类型**: 数字数组 `[float]`
*   **说明**: 输入主要吸收峰的波数 (cm⁻¹)。

#### 3. 氢谱 (h_nmr)
*   **类型**: 对象数组 `[Object]`
*   **字段**:
    *   `shift`: 化学位移 (ppm)
    *   `area`: 积分面积 (相对氢原子数)，支持数字或字符串（如 "N/A"）
    *   `multiplicity`: 峰的裂分重数 (1=单峰, 2=二重峰, 3=三重峰, etc.)

#### 4. 碳谱 (c_nmr)
*   **类型**: 字典 `Object`
*   **说明**: 包含 `bb` ($^{13}$C NMR), `dept90`, `dept135` 三个字段。
*   **字段详情**:
    *   `bb`: 列表 `[[shift, count], ...]`
        *   `shift`: 化学位移 (ppm)
        *   `count`: 峰的数量，支持数字或字符串（如 `">1"`, `"1"`）
    *   `dept90`: 列表 `[shift, ...]`
        *   仅需列出在 DEPT-90 谱图中出现的峰的化学位移。
    *   `dept135`: 列表 `[[shift, polarity], ...]`
        *   `shift`: 化学位移 (ppm)
        *   `polarity`: 峰的极性 (`1` 为向上, `-1` 为向下)

**推断逻辑**:
程序会自动根据 DEPT 数据推断碳类型：
*   DEPT-90 有峰 -> **CH**
*   DEPT-135 向下 (-1) -> **CH2**
*   DEPT-135 向上 (+1) 且不在 DEPT-90 -> **CH3**
*   仅在 BB 谱中有峰 -> **Cq** (季碳)
