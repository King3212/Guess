import json
import os
import sys
import threading
import queue
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from guess import get_data_from_json, gen_datas, gen_prompt_1, gen_prompt_2, ask_AI


class RedirectStdout:
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self.text_widget = text_widget
        self._buffer = []

    def write(self, s: str):
        if not s:
            return
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("光谱推结构助手")
        self.geometry("900x600")

        self.file_path = tk.StringVar()
        self.api_key_1 = tk.StringVar()
        self.base_url_1 = tk.StringVar()
        self.model_1 = tk.StringVar()
        self.api_key_2 = tk.StringVar()
        self.base_url_2 = tk.StringVar()
        self.model_2 = tk.StringVar()
        # 默认配置文件路径：
        # - 如果程序被打包为可执行文件（如 PyInstaller），优先使用 exe 所在目录
        # - 否则使用脚本文件所在目录
        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(__file__)
        except Exception:
            base_dir = os.path.dirname(__file__)

        self.default_config_path = os.path.join(base_dir, "API.json")

        self.ui_queue = queue.Queue()
        self._process_ui_queue()

        # 缓存中间结果，方便逐步分析
        self.cached_datas = None
        self.cached_fg_result = None
        self._last_json_content = None

        self._build_widgets()
        # 启动时尝试自动加载默认配置
        self._auto_load_default_config()

    def _build_widgets(self):
        # API 配置区域
        api_frame = tk.LabelFrame(self, text="AI API 配置")
        api_frame.pack(fill=tk.X, padx=10, pady=5)

        # Grid layout
        # Row 0: Headers
        tk.Label(api_frame, text="API 1 (Step 3)", font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Label(api_frame, text="API 2 (Step 2)", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="ew", padx=5, pady=5)

        # Row 1: Base URL
        tk.Label(api_frame, text="Base URL:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(api_frame, textvariable=self.base_url_1).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        tk.Entry(api_frame, textvariable=self.base_url_2).grid(row=1, column=2, sticky="ew", padx=5, pady=2)

        # Row 2: API Key
        tk.Label(api_frame, text="API Key:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(api_frame, textvariable=self.api_key_1, show="*").grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        tk.Entry(api_frame, textvariable=self.api_key_2, show="*").grid(row=2, column=2, sticky="ew", padx=5, pady=2)

        # Row 3: Model
        tk.Label(api_frame, text="Model:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        tk.Entry(api_frame, textvariable=self.model_1).grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        tk.Entry(api_frame, textvariable=self.model_2).grid(row=3, column=2, sticky="ew", padx=5, pady=2)

        # Buttons column
        btn_frame = tk.Frame(api_frame)
        btn_frame.grid(row=0, column=3, rowspan=4, padx=10, pady=5, sticky="ns")
        
        tk.Button(btn_frame, text="打开配置文件", command=self.open_api_config_file).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="从配置加载", command=self.load_api_config).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="保存为默认配置", command=self.save_default_api_config).pack(fill=tk.X, pady=2)

        # Configure columns
        api_frame.columnconfigure(1, weight=1)
        api_frame.columnconfigure(2, weight=1)

        # 文件选择区域
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="光谱 JSON 文件:").pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.file_path).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(top_frame, text="选择文件", command=self.choose_file).pack(side=tk.LEFT)
        tk.Button(top_frame, text="保存", command=self.save_file).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="另存为", command=self.save_file_as).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Step1 分析", command=self.start_step1).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Step2 分析", command=self.start_step2).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Step3 分析", command=self.start_step3).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="一键分析", command=self.start_analysis).pack(side=tk.LEFT, padx=5)

        # 中间区域：使用 PanedWindow 实现可调整大小的分栏
        middle_frame = tk.Frame(self)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 水平分割：左侧 Source JSON，中间 Step1，右侧 Step2/3
        h_paned = tk.PanedWindow(middle_frame, orient=tk.HORIZONTAL, sashwidth=4, sashrelief=tk.RAISED)
        h_paned.pack(fill=tk.BOTH, expand=True)

        # Source JSON Frame
        json_frame = tk.LabelFrame(h_paned, text="Source JSON")
        self.text_json = scrolledtext.ScrolledText(json_frame, wrap=tk.WORD)
        self.text_json.pack(fill=tk.BOTH, expand=True)
        h_paned.add(json_frame, minsize=200, width=300)

        # Step1 Frame
        step1_frame = tk.LabelFrame(h_paned, text="Step1: 基础数据 (datas)")
        self.text_datas = scrolledtext.ScrolledText(step1_frame, wrap=tk.WORD)
        self.text_datas.pack(fill=tk.BOTH, expand=True)
        # 设置初始宽度为300 (窗口默认900宽，约占1/3)
        h_paned.add(step1_frame, minsize=200, width=300)

        # 右侧区域：垂直分割 Step2 和 Step3
        v_paned = tk.PanedWindow(h_paned, orient=tk.VERTICAL, sashwidth=4, sashrelief=tk.RAISED)
        h_paned.add(v_paned, minsize=300)

        # Step2 Frame
        step2_frame = tk.LabelFrame(v_paned, text="Step2: 官能团推测")
        self.text_fg = scrolledtext.ScrolledText(step2_frame, wrap=tk.WORD, height=10)
        self.text_fg.pack(fill=tk.BOTH, expand=True)
        self.text_fg.tag_config("thinking", foreground="gray")
        v_paned.add(step2_frame, minsize=100)

        # Step3 Frame
        step3_frame = tk.LabelFrame(v_paned, text="Step3: 分子式与结构推测")
        self.text_struct = scrolledtext.ScrolledText(step3_frame, wrap=tk.WORD)
        self.text_struct.pack(fill=tk.BOTH, expand=True)
        self.text_struct.tag_config("thinking", foreground="gray")
        v_paned.add(step3_frame, minsize=100)

        # 底部控制台
        bottom_frame = tk.LabelFrame(self, text="控制台输出 (调试/流式输出)")
        bottom_frame.pack(fill=tk.X, expand=False, padx=10, pady=(0, 10))

        self.console = scrolledtext.ScrolledText(bottom_frame, height=8, wrap=tk.WORD)
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.tag_config("thinking", foreground="gray")

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="选择光谱 JSON 文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if path:
            self.file_path.set(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.text_json.delete("1.0", tk.END)
                self.text_json.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {e}")

    def save_file(self):
        path = self.file_path.get()
        if not path:
            self.save_file_as()
            return
        
        content = self.text_json.get("1.0", tk.END).strip()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("提示", f"文件已保存: {path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {e}")

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="另存为",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if path:
            self.file_path.set(path)
            content = self.text_json.get("1.0", tk.END).strip()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("提示", f"文件已保存: {path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件失败: {e}")

    def _auto_load_default_config(self):
        """程序启动时自动尝试从默认配置文件加载 API 设置。"""
        if os.path.exists(self.default_config_path):
            try:
                with open(self.default_config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.api_key_1.set(data.get("api_key_1", data.get("api_key", "")))
                self.base_url_1.set(data.get("base_url_1", ""))
                self.model_1.set(data.get("model_1", ""))
                self.api_key_2.set(data.get("api_key_2", ""))
                self.base_url_2.set(data.get("base_url_2", ""))
                self.model_2.set(data.get("model_2", ""))
            except Exception:
                # 自动加载失败不打扰用户，仅忽略
                pass

    def open_api_config_file(self):
        """选择一个配置文件（json），可用于加载/保存。"""
        path = filedialog.askopenfilename(
            title="选择 API 配置文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if path:
            # 将选择的路径设为当前默认配置路径
            self.default_config_path = path
            self.load_api_config()

    def load_api_config(self):
        """从当前默认配置文件路径加载 API 设置。"""
        try:
            with open(self.default_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.api_key_1.set(data.get("api_key_1", data.get("api_key", "")))
            self.base_url_1.set(data.get("base_url_1", ""))
            self.model_1.set(data.get("model_1", ""))
            self.api_key_2.set(data.get("api_key_2", ""))
            self.base_url_2.set(data.get("base_url_2", ""))
            self.model_2.set(data.get("model_2", ""))
            messagebox.showinfo("提示", f"已从 {os.path.basename(self.default_config_path)} 加载 API 配置。")
        except FileNotFoundError:
            messagebox.showwarning("提示", f"未找到配置文件: {self.default_config_path}，请先选择或保存配置。")
        except Exception as e:
            messagebox.showerror("错误", f"读取 qwenAPI.json 失败: {e}")

    def save_default_api_config(self):
        """将当前输入的 API 设置保存到默认配置文件。"""
        data = {
            "api_key": self.api_key_1.get().strip(),
            "api_key_1": self.api_key_1.get().strip(),
            "base_url_1": self.base_url_1.get().strip(),
            "model_1": self.model_1.get().strip(),
            "api_key_2": self.api_key_2.get().strip(),
            "base_url_2": self.base_url_2.get().strip(),
            "model_2": self.model_2.get().strip(),
        }
        try:
            with open(self.default_config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("提示", f"已保存为默认配置: {self.default_config_path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def start_analysis(self):
        json_content = self.text_json.get("1.0", tk.END).strip()
        if not json_content:
            messagebox.showwarning("提示", "JSON 内容为空，请选择文件或输入 JSON。")
            return

        # 清空全部区域，开始完整流水线
        self.text_datas.delete("1.0", tk.END)
        self.text_fg.delete("1.0", tk.END)
        self.text_struct.delete("1.0", tk.END)
        self.console.delete("1.0", tk.END)

        # 重置缓存
        self.cached_datas = None
        self.cached_fg_result = None
        self._last_json_content = json_content

        threading.Thread(target=self._run_pipeline, args=(json_content,), daemon=True).start()

    def start_step1(self):
        json_content = self.text_json.get("1.0", tk.END).strip()
        if not json_content:
            messagebox.showwarning("提示", "JSON 内容为空，请选择文件或输入 JSON。")
            return

        # 只清空 datas 区域和控制台输出
        self.text_datas.delete("1.0", tk.END)
        self.console.delete("1.0", tk.END)

        # 线程执行 step1
        self._last_json_content = json_content
        threading.Thread(target=self._run_step1, args=(json_content,), daemon=True).start()

    def start_step2(self):
        json_content = self.text_json.get("1.0", tk.END).strip()
        if not json_content and not self._last_json_content:
            messagebox.showwarning("提示", "JSON 内容为空，请选择文件或输入 JSON。")
            return

        # 清空 step2 区域和控制台输出
        self.text_fg.delete("1.0", tk.END)
        self.console.delete("1.0", tk.END)

        if json_content:
            self._last_json_content = json_content

        threading.Thread(target=self._run_step2, args=(self._last_json_content,), daemon=True).start()

    def start_step3(self):
        json_content = self.text_json.get("1.0", tk.END).strip()
        if not json_content and not self._last_json_content:
            messagebox.showwarning("提示", "JSON 内容为空，请选择文件或输入 JSON。")
            return

        # 清空 step3 区域 and console
        self.text_struct.delete("1.0", tk.END)
        self.console.delete("1.0", tk.END)

        if json_content:
            self._last_json_content = json_content

        threading.Thread(target=self._run_step3, args=(self._last_json_content,), daemon=True).start()

    def _run_pipeline(self, json_content: str):
        # 顺序执行三步，利用已有的 step helpers
        try:
            self._run_step1(json_content)
            # small pause to ensure UI updated before continuing
            time.sleep(0.1)
            self._run_step2(json_content)
            time.sleep(0.1)
            self._run_step3(json_content)
        except Exception as e:
            messagebox.showerror("错误", f"分析流水线失败: {e}")

    def _call_ai_stream(self, prompt: str, target_widget: scrolledtext.ScrolledText, type:int) -> str:
        """调用 AI，将流式增量实时写入指定文本框和控制台，并返回完整结果。"""

        full_text_parts = []
        buffer = []
        last_update_time = [time.time()]

        def flush_buffer():
            if not buffer:
                return
            
            # 合并相同 tag 的连续文本，减少 UI 更新次数
            merged = []
            if buffer:
                curr_text, curr_tags = buffer[0]
                for text, tags in buffer[1:]:
                    if tags == curr_tags:
                        curr_text += text
                    else:
                        merged.append((curr_text, curr_tags))
                        curr_text, curr_tags = text, tags
                merged.append((curr_text, curr_tags))
            
            for text, tags in merged:
                self._append_text(target_widget, text, tags=tags)
                self._append_text(self.console, text, tags=tags)
            
            buffer.clear()
            last_update_time[0] = time.time()

        def on_delta(text: str):
            full_text_parts.append(text)
            buffer.append((text, None))
            if time.time() - last_update_time[0] >= 2.0:
                flush_buffer()

        def on_thinking(text: str):
            buffer.append((text, "thinking"))
            if time.time() - last_update_time[0] >= 2.0:
                flush_buffer()

        try:
            if type == 1:
                result = ask_AI(
                    prompt,
                    api_key=self.api_key_1.get().strip() or None,
                    base_url=self.base_url_1.get().strip() or None,
                    model=self.model_1.get().strip() or None,
                    on_delta=on_delta,
                    on_thinking=on_thinking,
                )
            else:
                key_2 = self.api_key_2.get().strip()
                if not key_2:
                    key_2 = self.api_key_1.get().strip()
                result = ask_AI(
                    prompt,
                    api_key=key_2 or None,
                    base_url=self.base_url_2.get().strip() or None,
                    model=self.model_2.get().strip() or None,
                    on_delta=on_delta,
                    on_thinking=on_thinking,
                )
        except Exception as e:
            messagebox.showerror("错误", f"调用 AI 失败: {e}")
            return ""
        finally:
            flush_buffer()

        # 兜底，如果 ask_AI 内部返回的 result 与增量拼接不同，以返回值为准
        if result:
            return result
        return "".join(full_text_parts)

    # Step helper implementations
    def _run_step1(self, json_content: str):
        try:
            data = json.loads(json_content)
        except Exception as e:
            messagebox.showerror("错误", f"解析 JSON 失败: {e}")
            return

        try:
            datas = gen_datas(data)
        except Exception as e:
            messagebox.showerror("错误", f"解析光谱数据失败: {e}")
            return

        # 缓存并显示
        self.cached_datas = datas
        self._set_text(self.text_datas, "\n".join(datas) + "\n")

    def _run_step2(self, json_content: str):
        # 确保有 datas
        datas = self.cached_datas
        if datas is None:
            try:
                data = json.loads(json_content)
                datas = gen_datas(data)
            except Exception as e:
                messagebox.showerror("错误", f"生成 datas 失败: {e}")
                return

        self.cached_datas = datas

        # 调用 AI 推测官能团
        self._append_text(self.text_fg, "正在调用 AI 推测官能团...\n")
        fg_result = self._call_ai_stream(
            gen_prompt_1(datas),
            target_widget=self.text_fg,
            type=0
        )

        if fg_result:
            self.cached_fg_result = fg_result

        return fg_result

    def _run_step3(self, json_content: str):
        # 确保有 datas
        datas = self.cached_datas
        if datas is None:
            try:
                data = json.loads(json_content)
                datas = gen_datas(data)
            except Exception as e:
                messagebox.showerror("错误", f"生成 datas 失败: {e}")
                return

        # 确保有 fg_result
        fg = self.cached_fg_result
        if not fg:
            # 自动运行 step2
            fg = self._run_step2(json_content)

        findings_chain = "\n".join(datas)
        findings = (fg or "") + "\n以下是证据链:\n" + findings_chain + "\n"
        self._append_text(self.text_struct, "正在调用 AI 推测分子式和结构...\n")
        self._call_ai_stream(
            gen_prompt_2(findings.splitlines()),
            target_widget=self.text_struct,
            type=1
        )

    def _process_ui_queue(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                func = task[0]
                args = task[1:]
                func(*args)
        except queue.Empty:
            pass
        finally:
            self.after(50, self._process_ui_queue)

    def _set_text(self, widget: scrolledtext.ScrolledText, content: str):
        self.ui_queue.put((self._do_set_text, widget, content))

    def _do_set_text(self, widget: scrolledtext.ScrolledText, content: str):
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.see(tk.END)

    def _append_text(self, widget: scrolledtext.ScrolledText, content: str, tags=None):
        self.ui_queue.put((self._do_append_text, widget, content, tags))

    def _do_append_text(self, widget: scrolledtext.ScrolledText, content: str, tags=None):
        widget.insert(tk.END, content, tags)
        widget.see(tk.END)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
