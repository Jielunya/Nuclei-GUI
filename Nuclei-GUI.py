import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import threading
import os
from pathlib import Path
import re
import json
from datetime import datetime
import tempfile

class NucleiGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Nuclei GUI Tool v1.0 -by Jielun")
        # 窗口整体缩小一点
        self.root.geometry("1100x800")
        
        # 存储模板列表
        self.templates = []
        self.filtered_templates = []
        # 存储批量扫描的目标URL列表
        self.batch_targets = []
        # 存储自定义POC模板
        self.custom_templates = []
        self.filtered_custom_templates = []
        
        # 模板缓存文件路径
        self.cache_file = "templates_cache.json"
        self.cache_expiry_hours = 24
        
        # ANSI颜色到Tkinter颜色的映射
        self.ansi_color_map = {
            '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
            '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
            '90': 'gray', '91': 'lightcoral', '92': 'lightgreen', 
            '93': 'lightyellow', '94': 'lightblue', '95': 'pink', '96': 'lightcyan'
        }
        
        # 创建界面
        self.create_widgets()
        
        # 启动时尝试从缓存加载模板列表
        self.load_template_list_from_cache()
    
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架 - 使用PanedWindow实现左右分割
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # 左侧配置面板
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # 右侧输出面板
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # 配置左侧面板网格权重
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(6, weight=1)
        
        # 标题
        title_label = ttk.Label(left_frame, text="Nuclei GUI 扫描工具 v1.0", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # 控制按钮框架
        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        
        # 更新模板按钮
        update_btn = ttk.Button(control_frame, text="在线更新到最新POC模板", 
                               command=self.update_templates)
        update_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 刷新模板列表按钮
        refresh_btn = ttk.Button(control_frame, text="读取当前安装的所有官方POC模板", 
                                command=self.force_refresh_templates)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 清除缓存按钮
        clear_cache_btn = ttk.Button(control_frame, text="清除本地POC列表缓存", 
                                    command=self.clear_cache)
        clear_cache_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 代理设置框架
        proxy_frame = ttk.LabelFrame(left_frame, text="代理设置", padding="4")
        proxy_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        
        # 代理开关
        self.proxy_var = tk.BooleanVar()
        proxy_check = ttk.Checkbutton(proxy_frame, text="启用代理", 
                                     variable=self.proxy_var,
                                     command=self.toggle_proxy)
        proxy_check.pack(side=tk.LEFT)
        
        # 代理地址输入
        ttk.Label(proxy_frame, text="代理地址:").pack(side=tk.LEFT, padx=(8, 4))
        self.proxy_entry = ttk.Entry(proxy_frame, width=25)
        self.proxy_entry.insert(0, "http://127.0.0.1:8080")
        self.proxy_entry.pack(side=tk.LEFT)
        self.proxy_entry.config(state='disabled')
        
        # 目标URL输入框架
        url_frame = ttk.LabelFrame(left_frame, text="目标设置", padding="4")
        url_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 8))
        url_frame.columnconfigure(1, weight=1)
        
        # 单目标URL输入行
        single_url_frame = ttk.Frame(url_frame)
        single_url_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 4))
        
        ttk.Label(single_url_frame, text="单个目标URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_entry = ttk.Entry(single_url_frame)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(4, 4), pady=(0, 4))
        
        # 添加URL按钮
        add_url_btn = ttk.Button(single_url_frame, text="添加到列表", 
                                command=self.add_single_url)
        add_url_btn.grid(row=0, column=2, padx=(4, 0))
        
        # 批量扫描文件选择
        batch_frame = ttk.Frame(url_frame)
        batch_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 4))
        batch_frame.columnconfigure(1, weight=1)
        
        ttk.Label(batch_frame, text="批量目标文件:").grid(row=0, column=0, sticky=tk.W)
        self.batch_file_var = tk.StringVar(value="未选择文件")
        batch_file_label = ttk.Label(batch_frame, textvariable=self.batch_file_var, 
                                   foreground="blue", cursor="hand2")
        batch_file_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(4, 0))
        batch_file_label.bind("<Button-1>", self.select_batch_file)
        
        # 批量目标显示框
        ttk.Label(url_frame, text="待扫描地址列表:").grid(row=2, column=0, sticky=tk.W, pady=(4, 0))
        batch_display_frame = ttk.Frame(url_frame)
        batch_display_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(4, 0))
        batch_display_frame.columnconfigure(0, weight=1)
        batch_display_frame.rowconfigure(0, weight=1)
        
        # 批量目标列表框
        self.batch_listbox = tk.Listbox(batch_display_frame, height=3, selectmode=tk.EXTENDED, exportselection=False)
        batch_scrollbar = ttk.Scrollbar(batch_display_frame, orient=tk.VERTICAL, command=self.batch_listbox.yview)
        self.batch_listbox.configure(yscrollcommand=batch_scrollbar.set)
        
        self.batch_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        batch_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 批量操作按钮框架
        batch_buttons_frame = ttk.Frame(url_frame)
        batch_buttons_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))
        
        ttk.Button(batch_buttons_frame, text="清空列表", 
                  command=self.clear_batch_list).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(batch_buttons_frame, text="删除选中", 
                  command=self.delete_selected_targets).pack(side=tk.LEFT)
        
        # 扫描按钮框架
        scan_buttons_frame = ttk.Frame(url_frame)
        scan_buttons_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        
        # 开始扫描按钮
        self.scan_btn = ttk.Button(scan_buttons_frame, text="扫描选中地址", 
                                  command=self.start_scan_selected)
        self.scan_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 批量扫描按钮放在开始扫描按钮右边
        self.batch_scan_btn = ttk.Button(scan_buttons_frame, text="批量扫描全部", 
                                       command=self.start_batch_scan_all)
        self.batch_scan_btn.pack(side=tk.LEFT)
        
        # 搜索和模板选择框架
        template_frame = ttk.LabelFrame(left_frame, text="官方POC模板选择", padding="4")
        template_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(8, 0))
        template_frame.columnconfigure(0, weight=1)
        template_frame.rowconfigure(2, weight=1)
        
        # 搜索框
        search_frame = ttk.Frame(template_frame)
        search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        
        ttk.Label(search_frame, text="搜索POC:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))
        self.search_entry.bind('<KeyRelease>', self.search_templates)
        
        # 官方POC操作按钮框架
        official_buttons_frame = ttk.Frame(template_frame)
        official_buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        
        # 全选官方POC按钮
        select_all_official_btn = ttk.Button(official_buttons_frame, text="全选官方POC", 
                                           command=self.select_all_official_templates)
        select_all_official_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 取消全选官方POC按钮
        deselect_all_official_btn = ttk.Button(official_buttons_frame, text="取消全选官方POC", 
                                              command=self.deselect_all_official_templates)
        deselect_all_official_btn.pack(side=tk.LEFT)
        
        # 模板列表框
        list_frame = ttk.Frame(template_frame)
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 模板列表
        self.template_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=4,
                                          selectmode=tk.MULTIPLE, exportselection=False)
        self.template_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.template_listbox.yview)
        
        # 新增：自定义POC模板选择框架
        custom_template_frame = ttk.LabelFrame(left_frame, text="自定义POC模板", padding="4")
        custom_template_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(8, 0))
        custom_template_frame.columnconfigure(0, weight=1)
        custom_template_frame.rowconfigure(2, weight=1)
        
        # 自定义POC操作按钮框架
        custom_buttons_frame = ttk.Frame(custom_template_frame)
        custom_buttons_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        
        # 读取自定义POC文件夹按钮
        self.load_custom_btn = ttk.Button(custom_buttons_frame, text="读取自定义POC文件夹", 
                                        command=self.load_custom_templates)
        self.load_custom_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 清空自定义POC列表按钮
        self.clear_custom_btn = ttk.Button(custom_buttons_frame, text="清空自定义列表", 
                                          command=self.clear_custom_templates)
        self.clear_custom_btn.pack(side=tk.LEFT)
        
        # 自定义POC搜索框
        custom_search_frame = ttk.Frame(custom_template_frame)
        custom_search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        
        ttk.Label(custom_search_frame, text="搜索自定义POC:").pack(side=tk.LEFT)
        self.custom_search_var = tk.StringVar()
        self.custom_search_entry = ttk.Entry(custom_search_frame, textvariable=self.custom_search_var, width=25)
        self.custom_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))
        self.custom_search_entry.bind('<KeyRelease>', self.search_custom_templates)
        
        # 自定义POC操作按钮框架（全选/取消全选）
        custom_select_buttons_frame = ttk.Frame(custom_template_frame)
        custom_select_buttons_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        
        # 全选自定义POC按钮
        select_all_custom_btn = ttk.Button(custom_select_buttons_frame, text="全选自定义POC", 
                                         command=self.select_all_custom_templates)
        select_all_custom_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 取消全选自定义POC按钮
        deselect_all_custom_btn = ttk.Button(custom_select_buttons_frame, text="取消全选自定义POC", 
                                            command=self.deselect_all_custom_templates)
        deselect_all_custom_btn.pack(side=tk.LEFT)
        
        # 自定义POC列表框
        custom_list_frame = ttk.Frame(custom_template_frame)
        custom_list_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        custom_list_frame.columnconfigure(0, weight=1)
        custom_list_frame.rowconfigure(0, weight=1)
        
        # 自定义POC滚动条
        custom_scrollbar = ttk.Scrollbar(custom_list_frame)
        custom_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 自定义POC列表
        self.custom_template_listbox = tk.Listbox(custom_list_frame, yscrollcommand=custom_scrollbar.set, height=3,
                                                selectmode=tk.MULTIPLE, exportselection=False)
        self.custom_template_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        custom_scrollbar.config(command=self.custom_template_listbox.yview)
        
        # 右侧输出框
        output_frame = ttk.LabelFrame(right_frame, text="扫描输出", padding="4")
        output_frame.pack(fill=tk.BOTH, expand=True)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=18,
                                                    wrap=tk.WORD, font=("Consolas", 9))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 预定义颜色标签
        self.setup_text_tags()
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))
    
    def setup_text_tags(self):
        """设置文本颜色标签"""
        colors = {
            'red': 'red', 'green': 'green', 'yellow': 'yellow', 'blue': 'blue',
            'magenta': 'magenta', 'cyan': 'cyan', 'white': 'white', 'gray': 'gray',
            'lightcoral': 'lightcoral', 'lightgreen': 'lightgreen', 'lightyellow': 'lightyellow',
            'lightblue': 'lightblue', 'pink': 'pink', 'lightcyan': 'lightcyan', 'black': 'black'
        }
        
        for tag_name, color in colors.items():
            self.output_text.tag_config(tag_name, foreground=color)
    
    def parse_ansi_colors(self, text):
        """解析ANSI颜色代码"""
        ansi_escape = re.compile(r'\x1B\[([0-9;]*)([a-zA-Z])')
        result_parts = []
        last_end = 0
        current_color = 'black'
        
        for match in ansi_escape.finditer(text):
            if match.start() > last_end:
                result_parts.append((text[last_end:match.start()], current_color))
            
            ansi_code = match.group(1)
            ansi_command = match.group(2)
            
            if ansi_command == 'm':
                codes = ansi_code.split(';')
                for code in codes:
                    if code in self.ansi_color_map:
                        current_color = self.ansi_color_map[code]
                        break
            
            last_end = match.end()
        
        if last_end < len(text):
            result_parts.append((text[last_end:], current_color))
        
        return result_parts if result_parts else [(text, 'black')]
    
    def insert_colored_text(self, text, color=None):
        """向输出框插入带颜色的文本"""
        try:
            if color:
                self.output_text.insert(tk.END, text, color)
            else:
                colored_parts = self.parse_ansi_colors(text)
                for part_text, part_color in colored_parts:
                    if part_text.strip():
                        self.output_text.insert(tk.END, part_text, part_color)
            
            self.output_text.see(tk.END)
            self.root.update_idletasks()
            
        except Exception as e:
            self.output_text.insert(tk.END, text)
            self.output_text.see(tk.END)
    
    def add_single_url(self):
        """添加单个URL到目标列表"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入目标URL")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = f"http://{url}"
        
        if url not in self.batch_targets:
            self.batch_targets.append(url)
            self.update_batch_listbox()
            self.insert_colored_text(f"已添加目标: {url}\n", 'green')
            self.url_entry.delete(0, tk.END)
        else:
            messagebox.showinfo("提示", "该URL已存在于目标列表中")
    
    def select_batch_file(self, event=None):
        """选择批量扫描文件"""
        file_path = filedialog.askopenfilename(
            title="选择目标URL文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.load_batch_targets(file_path)
    
    def load_batch_targets(self, file_path):
        """加载批量目标URL"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_targets = []
            valid_urls = 0
            
            for line in lines:
                url = line.strip()
                if url and not url.startswith('#'):
                    if url.startswith(('http://', 'https://')):
                        if url not in self.batch_targets and url not in new_targets:
                            new_targets.append(url)
                            valid_urls += 1
                    else:
                        full_url = f"http://{url}"
                        if full_url not in self.batch_targets and full_url not in new_targets:
                            new_targets.append(full_url)
                            valid_urls += 1
            
            self.batch_targets.extend(new_targets)
            self.batch_file_var.set(f"已选择: {os.path.basename(file_path)} (+{valid_urls}个目标)")
            self.update_batch_listbox()
            self.insert_colored_text(f"成功加载批量目标文件: {file_path}\n", 'green')
            self.insert_colored_text(f"新增 {valid_urls} 个有效目标，总计 {len(self.batch_targets)} 个目标\n", 'green')
            
        except Exception as e:
            messagebox.showerror("错误", f"读取文件失败: {e}")
            self.insert_colored_text(f"读取批量目标文件失败: {e}\n", 'red')
    
    def update_batch_listbox(self):
        """更新批量目标列表框"""
        self.batch_listbox.delete(0, tk.END)
        for target in self.batch_targets:
            self.batch_listbox.insert(tk.END, target)
    
    def clear_batch_list(self):
        """清空批量目标列表"""
        self.batch_targets = []
        self.batch_listbox.delete(0, tk.END)
        self.batch_file_var.set("未选择文件")
        self.insert_colored_text("已清空目标列表\n", 'green')
    
    def delete_selected_targets(self):
        """删除选中的目标"""
        selected_indices = self.batch_listbox.curselection()
        if selected_indices:
            removed_count = 0
            for index in sorted(selected_indices, reverse=True):
                if index < len(self.batch_targets):
                    removed_target = self.batch_targets.pop(index)
                    removed_count += 1
                    self.insert_colored_text(f"已移除目标: {removed_target}\n", 'red')
            
            self.update_batch_listbox()
            self.insert_colored_text(f"已删除 {removed_count} 个目标，剩余 {len(self.batch_targets)} 个目标\n", 'green')
        else:
            messagebox.showwarning("警告", "请先选择要删除的目标")
    
    def select_all_official_templates(self):
        """全选官方POC模板"""
        try:
            # 获取所有可见的模板（考虑搜索过滤）[8](@ref)
            all_indices = list(range(len(self.filtered_templates)))
            if all_indices:
                self.template_listbox.selection_set(0, tk.END)
                self.insert_colored_text(f"已全选 {len(all_indices)} 个官方POC模板\n", 'green')
            else:
                self.insert_colored_text("官方POC模板列表为空，无法全选\n", 'red')
        except Exception as e:
            self.insert_colored_text(f"全选官方POC模板时出错: {e}\n", 'red')
    
    def deselect_all_official_templates(self):
        """取消全选官方POC模板"""
        try:
            selected_indices = self.template_listbox.curselection()
            if selected_indices:
                self.template_listbox.selection_clear(0, tk.END)
                self.insert_colored_text(f"已取消选择 {len(selected_indices)} 个官方POC模板\n", 'green')
            else:
                self.insert_colored_text("没有选中的官方POC模板\n", 'red')
        except Exception as e:
            self.insert_colored_text(f"取消全选官方POC模板时出错: {e}\n", 'red')
    
    def select_all_custom_templates(self):
        """全选自定义POC模板"""
        try:
            # 获取所有可见的自定义模板（考虑搜索过滤）[8](@ref)
            all_indices = list(range(len(self.filtered_custom_templates)))
            if all_indices:
                self.custom_template_listbox.selection_set(0, tk.END)
                self.insert_colored_text(f"已全选 {len(all_indices)} 个自定义POC模板\n", 'green')
            else:
                self.insert_colored_text("自定义POC模板列表为空，无法全选\n", 'red')
        except Exception as e:
            self.insert_colored_text(f"全选自定义POC模板时出错: {e}\n", 'red')
    
    def deselect_all_custom_templates(self):
        """取消全选自定义POC模板"""
        try:
            selected_indices = self.custom_template_listbox.curselection()
            if selected_indices:
                self.custom_template_listbox.selection_clear(0, tk.END)
                self.insert_colored_text(f"已取消选择 {len(selected_indices)} 个自定义POC模板\n", 'green')
            else:
                self.insert_colored_text("没有选中的自定义POC模板\n", 'red')
        except Exception as e:
            self.insert_colored_text(f"取消全选自定义POC模板时出错: {e}\n", 'red')
    
    def load_custom_templates(self):
        """读取自定义POC文件夹"""
        folder_path = filedialog.askdirectory(title="选择自定义POC文件夹")
        if not folder_path:
            return
        
        def run_load_custom():
            self.load_custom_btn.config(state='disabled')
            self.status_var.set("正在读取自定义POC文件夹...")
            self.insert_colored_text(f"正在读取自定义POC文件夹: {folder_path}\n", 'blue')
            
            try:
                # 使用os.walk递归遍历文件夹
                new_custom_templates = []
                for root_dir, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.endswith('.yaml') or file.endswith('.yml'):
                            full_path = os.path.join(root_dir, file)
                            new_custom_templates.append(full_path)
                
                if new_custom_templates:
                    self.custom_templates = new_custom_templates
                    self.filtered_custom_templates = self.custom_templates.copy()
                    
                    # 保存自定义POC模板到缓存
                    self.save_templates_to_cache()
                    
                    # 更新自定义POC列表框
                    self.root.after(0, self.update_custom_template_listbox)
                    self.insert_colored_text(f"成功加载 {len(new_custom_templates)} 个自定义POC模板\n", 'green')
                    self.status_var.set(f"已加载 {len(new_custom_templates)} 个自定义POC")
                else:
                    self.insert_colored_text("在所选文件夹中未找到.yaml或.yml文件\n", 'red')
                    self.status_var.set("未找到自定义POC")
                    
            except Exception as e:
                self.insert_colored_text(f"读取自定义POC文件夹失败: {e}\n", 'red')
                self.status_var.set("读取自定义POC失败")
            finally:
                self.load_custom_btn.config(state='normal')
        
        threading.Thread(target=run_load_custom, daemon=True).start()
    
    def update_custom_template_listbox(self):
        """更新自定义POC模板列表框显示"""
        self.custom_template_listbox.delete(0, tk.END)
        for template in self.custom_templates:
            display_name = os.path.basename(template)
            self.custom_template_listbox.insert(tk.END, f"{display_name}")
        self.filtered_custom_templates = self.custom_templates.copy()
    
    def clear_custom_templates(self):
        """清空自定义POC列表"""
        self.custom_templates = []
        self.filtered_custom_templates = []
        self.custom_template_listbox.delete(0, tk.END)
        self.insert_colored_text("已清空自定义POC列表\n", 'green')
        self.status_var.set("已清空自定义POC")
    
    def search_custom_templates(self, event=None):
        """搜索过滤自定义POC模板"""
        search_term = self.custom_search_var.get().lower()
        
        if not search_term:
            self.filtered_custom_templates = self.custom_templates
        else:
            self.filtered_custom_templates = [tpl for tpl in self.custom_templates 
                                           if search_term in tpl.lower()]
        
        # 更新自定义POC列表框显示
        self.custom_template_listbox.delete(0, tk.END)
        for template in self.filtered_custom_templates:
            display_name = os.path.basename(template)
            self.custom_template_listbox.insert(tk.END, f"{display_name} | {template}")
    
    def is_cache_valid(self):
        """检查缓存是否有效"""
        if not os.path.exists(self.cache_file):
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            time_diff = datetime.now() - cache_time
            return time_diff.total_seconds() < (self.cache_expiry_hours * 3600)
            
        except Exception:
            return False
    
    def save_templates_to_cache(self):
        """将模板列表保存到缓存文件"""
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'templates': self.templates,
                'custom_templates': self.custom_templates
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.insert_colored_text(f"模板列表已缓存到 {self.cache_file}\n", 'green')
            
        except Exception as e:
            self.insert_colored_text(f"缓存保存失败: {e}\n", 'red')
    
    def load_templates_from_cache(self):
        """从缓存文件加载模板列表"""
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.templates = cache_data.get('templates', [])
            self.custom_templates = cache_data.get('custom_templates', [])
            
            # 更新模板列表框
            self.root.after(0, self.update_template_listbox)
            # 更新自定义POC列表框
            self.root.after(0, self.update_custom_template_listbox)
            
            cache_time = datetime.fromisoformat(cache_data.get('timestamp', ''))
            time_diff = datetime.now() - cache_time
            hours = int(time_diff.total_seconds() / 3600)
            
            self.status_var.set(f"从缓存加载完成（{hours}小时前）")
            self.insert_colored_text(f"从缓存加载了 {len(self.templates)} 个官方模板和 {len(self.custom_templates)} 个自定义模板\n", 'green')
            return True
            
        except Exception as e:
            return False
    
    def load_template_list_from_cache(self):
        """启动时尝试从缓存加载模板列表"""
        if self.is_cache_valid():
            if self.load_templates_from_cache():
                return
        
        self.insert_colored_text("缓存无效或不存在，从命令获取模板列表...\n", 'red')
        self.load_template_list()
    
    def force_refresh_templates(self):
        """强制刷新模板列表（查看所有当前安装的官方POC模板列表）"""
        self.insert_colored_text("查看所有当前安装的官方POC模板列表...\n", 'green')
        self.load_template_list()
    
    def clear_cache(self):
        """清除缓存文件"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                # 同时清空内存中的自定义POC列表
                self.custom_templates = []
                self.filtered_custom_templates = []
                self.custom_template_listbox.delete(0, tk.END)
                self.insert_colored_text("缓存已清除\n", 'green')
                self.status_var.set("缓存已清除")
            else:
                self.insert_colored_text("缓存文件不存在\n", 'red')
        except Exception as e:
            self.insert_colored_text(f"清除缓存失败: {e}\n", 'red')
    
    def toggle_proxy(self):
        """切换代理输入框状态"""
        if self.proxy_var.get():
            self.proxy_entry.config(state='normal')
        else:
            self.proxy_entry.config(state='disabled')
    
    def update_templates(self):
        """更新Nuclei模板"""
        def run_update():
            self.scan_btn.config(state='disabled')
            self.batch_scan_btn.config(state='disabled')
            self.status_var.set("正在更新模板...")
            self.insert_colored_text("正在更新Nuclei模板...\n", 'blue')
            
            try:
                result = subprocess.run(["nuclei", "-update-templates"], 
                                      capture_output=True, text=True, check=True)
                self.insert_colored_text("模板更新成功！\n", 'green')
                self.insert_colored_text(result.stdout + "\n", 'green')
                self.force_refresh_templates()
                
            except subprocess.CalledProcessError as e:
                self.insert_colored_text(f"模板更新失败: {e}\n", 'red')
                if e.stderr:
                    self.insert_colored_text(f"错误信息: {e.stderr}\n", 'red')
            except FileNotFoundError:
                self.insert_colored_text("错误: 未找到nuclei命令，请确保已安装Nuclei\n", 'red')
            
            self.status_var.set("就绪")
            self.scan_btn.config(state='normal')
            self.batch_scan_btn.config(state='normal')
        
        threading.Thread(target=run_update, daemon=True).start()
    
    def load_template_list(self):
        """从命令加载模板列表"""
        def run_load():
            self.status_var.set("正在加载模板列表...")
            try:
                result = subprocess.run(["nuclei", "-tl"], 
                                      capture_output=True, text=True, check=True)
                
                lines = result.stdout.strip().split('\n')
                new_templates = []
                
                for line in lines:
                    if line.strip() and not line.startswith('[') and line.endswith('.yaml'):
                        new_templates.append(line.strip())
                
                self.templates = new_templates
                self.save_templates_to_cache()
                self.root.after(0, self.update_template_listbox)
                self.status_var.set(f"加载完成，共{len(self.templates)}个模板")
                
            except subprocess.CalledProcessError as e:
                self.root.after(0, lambda: self.status_var.set("加载模板列表失败"))
                self.insert_colored_text(f"加载模板列表失败: {e}\n", 'red')
            except FileNotFoundError:
                self.root.after(0, lambda: self.status_var.set("未找到nuclei命令"))
                self.insert_colored_text("错误: 未找到nuclei命令，请确保已安装Nuclei\n", 'red')
        
        threading.Thread(target=run_load, daemon=True).start()
    
    def update_template_listbox(self):
        """更新模板列表框显示"""
        self.template_listbox.delete(0, tk.END)
        for template in self.templates:
            self.template_listbox.insert(tk.END, template)
        self.filtered_templates = self.templates.copy()
    
    def search_templates(self, event=None):
        """搜索过滤模板"""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            self.filtered_templates = self.templates
        else:
            self.filtered_templates = [tpl for tpl in self.templates 
                                     if search_term in tpl.lower()]
        
        self.template_listbox.delete(0, tk.END)
        for template in self.filtered_templates:
            self.template_listbox.insert(tk.END, template)
    
    def get_selected_templates(self):
        """获取所有选中的模板（标准+自定义）"""
        selected_templates = []
        
        # 获取标准模板选择
        selected_std_indices = self.template_listbox.curselection()
        if selected_std_indices:
            selected_templates.extend([self.filtered_templates[i] for i in selected_std_indices])
        
        # 获取自定义模板选择
        selected_custom_indices = self.custom_template_listbox.curselection()
        if selected_custom_indices:
            selected_templates.extend([self.filtered_custom_templates[i] for i in selected_custom_indices])
        
        return selected_templates
    
    def start_scan_selected(self):
        """扫描选中的目标"""
        selected_indices = self.batch_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "请至少选择一个目标地址")
            return
        
        selected_templates = self.get_selected_templates()
        if not selected_templates:
            messagebox.showwarning("警告", "请选择至少一个POC模板（标准或自定义）")
            return
        
        selected_targets = [self.batch_targets[i] for i in selected_indices]
        
        if len(selected_targets) == 1:
            self.start_single_scan(selected_targets[0], selected_templates)
        else:
            self.start_batch_scan_selected(selected_targets, selected_templates)
    
    def start_batch_scan_all(self):
        """批量扫描所有目标"""
        if not self.batch_targets:
            messagebox.showwarning("警告", "目标列表为空，请先添加目标地址")
            return
        
        selected_templates = self.get_selected_templates()
        if not selected_templates:
            messagebox.showwarning("警告", "请选择至少一个POC模板（标准或自定义）")
            return
        
        result = messagebox.askyesno(
            "确认批量扫描",
            f"即将开始批量扫描所有 {len(self.batch_targets)} 个目标。\n是否继续？"
        )
        
        if result:
            self.start_batch_scan(self.batch_targets, selected_templates)
    
    def start_single_scan(self, target_url, selected_templates):
        """单目标扫描"""
        def run_scan():
            self.scan_btn.config(state='disabled')
            self.batch_scan_btn.config(state='disabled')
            self.status_var.set("扫描进行中...")
            
            try:
                output_dir = Path("./work")
                output_dir.mkdir(exist_ok=True)
                
                # 单目标使用 -u 参数
                cmd = ["nuclei", "-o", "./work/result.txt", "-u", target_url]
                
                for template in selected_templates:
                    cmd.extend(["-t", template])
                
                if self.proxy_var.get():
                    proxy_url = self.proxy_entry.get().strip()
                    if proxy_url:
                        cmd.extend(["-p", proxy_url])
                
                self.insert_colored_text(f"执行命令: {' '.join(cmd)}\n", 'blue')
                self.insert_colored_text("-" * 50 + "\n", 'black')
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                         stderr=subprocess.STDOUT, text=True)
                
                for line in process.stdout:
                    self.insert_colored_text(line)
                    self.root.update_idletasks()
                
                process.wait()
                self.insert_colored_text(f"\n扫描完成！结果已保存到 ./work/result.txt\n", 'green')
                self.status_var.set("扫描完成")
                
            except Exception as e:
                self.insert_colored_text(f"扫描出错: {e}\n", 'red')
                self.status_var.set("扫描出错")
            finally:
                self.scan_btn.config(state='normal')
                self.batch_scan_btn.config(state='normal')
            
            self.output_text.see(tk.END)
        
        threading.Thread(target=run_scan, daemon=True).start()
    
    def start_batch_scan_selected(self, targets, selected_templates):
        """扫描选中的多个目标"""
        def run_batch_scan():
            self.scan_btn.config(state='disabled')
            self.batch_scan_btn.config(state='disabled')
            total_targets = len(targets)
            self.status_var.set(f"扫描选中目标中... (0/{total_targets})")
            
            try:
                output_dir = Path("./work")
                output_dir.mkdir(exist_ok=True)
                
                successful_scans = 0
                failed_scans = 0
                
                for i, target_url in enumerate(targets, 1):
                    self.status_var.set(f"扫描选中目标中... ({i}/{total_targets})")
                    
                    self.insert_colored_text(f"\n[{i}/{total_targets}] 扫描目标: {target_url}\n", 'blue')
                    self.insert_colored_text("-" * 50 + "\n", 'black')
                    
                    # 对每个目标使用 -u 参数
                    cmd = ["nuclei", "-o", f"./work/result_selected_{i}.txt", "-u", target_url]
                    
                    for template in selected_templates:
                        cmd.extend(["-t", template])
                    
                    if self.proxy_var.get():
                        proxy_url = self.proxy_entry.get().strip()
                        if proxy_url:
                            cmd.extend(["-p", proxy_url])
                    
                    self.insert_colored_text(f"执行命令: {' '.join(cmd)}\n", 'blue')
                    
                    try:
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                                stderr=subprocess.STDOUT, text=True)
                        
                        for line in process.stdout:
                            self.insert_colored_text(line)
                            self.root.update_idletasks()
                        
                        process.wait()
                        
                        if process.returncode == 0:
                            self.insert_colored_text(f"[{i}/{total_targets}] 扫描完成 ✓\n", 'green')
                            successful_scans += 1
                        else:
                            self.insert_colored_text(f"[{i}/{total_targets}] 扫描失败 ✗\n", 'red')
                            failed_scans += 1
                            
                    except Exception as e:
                        self.insert_colored_text(f"[{i}/{total_targets}] 扫描异常: {e}\n", 'red')
                        failed_scans += 1
                
                self.insert_colored_text(f"\n选中目标扫描完成！\n", 'green')
                self.insert_colored_text(f"成功: {successful_scans}, 失败: {failed_scans}, 总计: {total_targets}\n", 'green')
                self.status_var.set("选中目标扫描完成")
                
            except Exception as e:
                self.insert_colored_text(f"扫描出错: {e}\n", 'red')
                self.status_var.set("扫描出错")
            finally:
                self.scan_btn.config(state='normal')
                self.batch_scan_btn.config(state='normal')
            
            self.output_text.see(tk.END)
        
        threading.Thread(target=run_batch_scan, daemon=True).start()
    
    def start_batch_scan(self, targets, selected_templates):
        """批量扫描 - 使用 -l 参数"""
        def run_batch_scan():
            self.scan_btn.config(state='disabled')
            self.batch_scan_btn.config(state='disabled')
            self.status_var.set("批量扫描进行中...")
            
            try:
                output_dir = Path("./work")
                output_dir.mkdir(exist_ok=True)
                
                # 创建临时文件保存目标URL
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                    for target in targets:
                        temp_file.write(target + '\n')
                    temp_file_path = temp_file.name
                
                # 构建命令 - 使用 -l 参数代替 -u
                cmd = ["nuclei", "-o", "./work/result_batch.txt", "-l", temp_file_path]
                
                for template in selected_templates:
                    cmd.extend(["-t", template])
                
                if self.proxy_var.get():
                    proxy_url = self.proxy_entry.get().strip()
                    if proxy_url:
                        cmd.extend(["-p", proxy_url])
                
                self.insert_colored_text(f"执行批量扫描命令: {' '.join(cmd)}\n", 'blue')
                self.insert_colored_text(f"扫描目标数量: {len(targets)}\n", 'blue')
                self.insert_colored_text("-" * 50 + "\n", 'black')
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, 
                                         stderr=subprocess.STDOUT, text=True)
                
                for line in process.stdout:
                    self.insert_colored_text(line)
                    self.root.update_idletasks()
                
                process.wait()
                
                # 删除临时文件
                os.unlink(temp_file_path)
                
                self.insert_colored_text(f"\n批量扫描完成！结果已保存到 ./work/result_batch.txt\n", 'green')
                self.status_var.set("批量扫描完成")
                
            except Exception as e:
                self.insert_colored_text(f"批量扫描出错: {e}\n", 'red')
                self.status_var.set("批量扫描出错")
            finally:
                self.scan_btn.config(state='normal')
                self.batch_scan_btn.config(state='normal')
            
            self.output_text.see(tk.END)
        
        threading.Thread(target=run_batch_scan, daemon=True).start()

def main():
    root = tk.Tk()
    app = NucleiGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()