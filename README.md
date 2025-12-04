# Comprehensive Spectral Analysis Program (Guess)

[中文说明 (Chinese README)](README_zh.md)

This is an AI-based tool for inferring organic molecular structures. It integrates the analysis of Mass Spectrometry (Mass), Infrared Spectroscopy (IR), Proton NMR (1H NMR), and Carbon NMR (13C/DEPT NMR) data, utilizing Large Language Models (such as GPT-4, Qwen, DeepSeek, etc.) to progressively infer functional groups and the final molecular structure.

## Features

*   **Multi-Spectrum Integrated Analysis**: Supports integration of Mass, IR, 1H NMR, and 13C NMR (BB/DEPT) data.
*   **Graphical User Interface (GUI)**: Provides an intuitive Tkinter interface for easy operation.
*   **Step-by-Step Inference**:
    *   **Step 1**: Data preprocessing and standardization.
    *   **Step 2**: AI infers possible functional groups.
    *   **Step 3**: AI synthesizes the chain of evidence to infer the molecular formula and structural formula.
*   **Custom AI Configuration**: Supports OpenAI-compatible interfaces, allowing customization of Base URL and Model.

## Installation

### Us

1.  Ensure Python 3.8 or higher is installed.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The GUI uses Python's built-in `tkinter`, which usually does not require separate installation)*

## User Guide

### 1. Start the Program

**Option A: Run Executable (Recommended for Windows)**
1.  Navigate to the `dist` folder.
2.  Double-click `GuessUI.exe` to launch the application.
    *   *Note: The `dist` folder contains necessary configuration files (`API.json`) and examples.*

**Option B: Run from Source**
Run `gui.py` to launch the graphical interface:
```bash
python gui.py
```

### 2. Configure API
Fill in your API information in the "AI API Configuration" section of the interface:
*   **Base URL**: API service address (e.g., `https://api.openai.com/v1` or other compatible addresses)
*   **API Key**: Your API key
*   **Model**: The model name to use (models with strong logical reasoning capabilities are recommended)

You can configure different model settings for Step 2 (Functional Group Inference) and Step 3 (Structure Inference) separately, or save them as the default configuration (`API.json`).

### 3. Run Analysis
1.  Click "Select File" to load a JSON file containing spectral data.
2.  You can click "One-Click Analysis" to automatically run the full process.
3.  Or click "Step1 Analysis" -> "Step2 Analysis" -> "Step3 Analysis" step by step to view intermediate results.

---

# Data Input Instructions (JSON)

The program supports batch input of spectral data via JSON files. Please refer to the following format to write your JSON file (e.g., `input.json`).

## JSON Structure Example

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

## Field Descriptions

### 1. Mass Spectrometry (mass)
*   **Type**: Number Array `[float]`
*   **Description**: Input the mass-to-charge ratios (m/z) of the main ion peaks observed in the mass spectrum. Usually includes the molecular ion peak and major fragment peaks.

### 2. Infrared Spectroscopy (ir)
*   **Type**: Number Array `[float]`
*   **Description**: Input the wavenumbers (cm⁻¹) of the main absorption peaks.

### 3. Proton NMR (h_nmr)
*   **Type**: Object Array `[Object]`
*   **Fields**:
    *   `shift`: Chemical shift (ppm)
    *   `area`: Integration area (relative number of hydrogen atoms), supports numbers or strings (e.g., "N/A")
    *   `multiplicity`: Peak splitting multiplicity (1=singlet, 2=doublet, 3=triplet, etc.)

### 4. Carbon NMR (c_nmr)
*   **Type**: Dictionary `Object`
*   **Description**: Contains three fields: `bb` (Broadband Decoupled), `dept90`, and `dept135`.
*   **Field Details**:
    *   `bb`: List `[[shift, count], ...]`
        *   `shift`: Chemical shift (ppm)
        *   `count`: Number of peaks, supports numbers or strings (e.g., `">1"`, `"1"`)
    *   `dept90`: List `[shift, ...]`
        *   Only list the chemical shifts of peaks appearing in the DEPT-90 spectrum.
    *   `dept135`: List `[[shift, polarity], ...]`
        *   `shift`: Chemical shift (ppm)
        *   `polarity`: Peak polarity (`1` for up, `-1` for down)

**Inference Logic**:
The program automatically infers carbon types based on DEPT data:
*   DEPT-90 has peak -> **CH**
*   DEPT-135 down (-1) -> **CH2**
*   DEPT-135 up (+1) and not in DEPT-90 -> **CH3**
*   Peak only in BB spectrum -> **Cq** (Quaternary Carbon)
