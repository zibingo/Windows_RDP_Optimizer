import os
import sys
import winreg
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, font
import ctypes

# 检查管理员权限
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    messagebox.showwarning("需要管理员权限", "此程序需要管理员权限运行，请以管理员身份运行。")
    sys.exit(1)

class RDPOptimizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows远程桌面RDP性能优化工具")
        self.root.geometry("575x780")
        self.root.resizable(False, False)
        
        # 设置字体
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="微软雅黑", size=12)
        
        # 应用状态标志
        self.is_app_enabled = False
        
        # 定义注册表修改项（按功能分类）
        # 每个配置项包含以下字段：
        # - category: 功能分类
        # - name: 配置项显示名称
        # - description: 功能描述
        # - path: 注册表路径
        # - key: 注册表键名（单键值）或 multi_key: True（多键值）
        # - enable_value: 启用时的值
        # - disable_action: 禁用时的操作（"delete"删除键值或指定disable_value）
        # - disable_value: 禁用时的值（可选）
        
        self.registry_mods = [
            # 帧率和时序优化
            {
                "category": "帧率和时序优化",
                "name": "优化帧时序 (DWMFRAMEINTERVAL) 终端服务器",
                "description": "为桌面窗口管理器设置较低的帧间隔，以实现更高的帧率（目标约60 FPS）",
                "path": r"SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations",
                "key": "DWMFRAMEINTERVAL",
                "enable_value": 0x0f,
                "disable_action": "delete"
            },
            {
                "category": "帧率和时序优化",
                "name": "禁用DWM最低帧率要求",
                "description": "可帮助解决基于Chromium的应用的渲染问题",
                "path": r"SOFTWARE\Microsoft\Windows\Dwm",
                "key": "OverlayMinFPS",
                "enable_value": 0,
                "disable_action": "delete"
            },
            {
                "category": "帧率和时序优化",
                "name": "设置系统响应性为0以提升性能",
                "description": "防止多媒体播放限制网络性能，可提高RDP响应性",
                "path": r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile",
                "key": "SystemResponsiveness",
                "enable_value": 0x00,
                "disable_value": 0x14
            },
            {
                "category": "帧率和时序优化",
                "name": "移除RDP人为延迟 (InteractiveDelay)",
                "description": "移除RDP交互中的内置小延迟",
                "path": r"SYSTEM\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp",
                "key": "InteractiveDelay",
                "enable_value": 0x00,
                "disable_value": 0x32
            },
            
            # 网络和带宽优化
            {
                "category": "网络和带宽优化",
                "name": "优化TermDD服务流控制设置",
                "description": "调整显示和虚拟通道的带宽分配，优先保证流畅的视觉体验",
                "multi_key": True,
                "keys": [
                    {"name": "FlowControlDisable", "value": 0x01},
                    {"name": "FlowControlDisplayBandwidth", "value": 0x10},
                    {"name": "FlowControlChannelBandwidth", "value": 0x90},
                    {"name": "FlowControlChargePostCompression", "value": 0x00}
                ],
                "path": r"SYSTEM\CurrentControlSet\Services\TermDD"
            },
            {
                "category": "网络和带宽优化",
                "name": "优化LanmanWorkstation网络",
                "description": "禁用网络带宽限制并启用对大网络数据包（MTU）的支持",
                "multi_key": True,
                "keys": [
                    {"name": "DisableBandwidthThrottling", "value": 0x01},
                    {"name": "DisableLargeMtu", "value": 0x00}
                ],
                "path": r"SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters"
            },
            
            # 图形和编码优化
            {
                "category": "图形和编码优化",
                "name": "优先使用硬件显卡处理RDP",
                "description": "强制RDP使用硬件GPU进行渲染，对图形要求高的应用至关重要",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "bEnumerateHWBeforeSW",
                "enable_value": 1,
                "disable_action": "delete"
            },
            {
                "category": "图形和编码优化",
                "name": "允许RDP同时使用UDP和TCP协议",
                "description": "配置RDP传输协议使用UDP在低延迟网络上获得更好性能，TCP作为备用",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "SelectTransport",
                "enable_value": 2,
                "disable_action": "delete"
            },
            {
                "category": "图形和编码优化",
                "name": "启用硬件H.264编码",
                "description": "优先使用硬件加速的H.264/AVC视频编码，比软件编码更高效",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "AVCHardwareEncodePreferred",
                "enable_value": 1,
                "disable_action": "delete"
            },
            {
                "category": "图形和编码优化",
                "name": "优先使用H.264/AVC 444图形模式",
                "description": "启用最高质量的H.264模式（AVC 444），实现像素级色彩精度，对文本和清晰图像有益",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "AVC444ModePreferred",
                "enable_value": 1,
                "disable_action": "delete"
            },
            {
                "category": "图形和编码优化",
                "name": "使用XDDM驱动替代WDDM",
                "description": "现代系统和高性能 GPU 环境选择 WDDM，老系统或兼容性优先时选择 XDDM",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "fEnableWddmDriver",
                "enable_value": 0,
                "disable_action": "delete"
            },
            {
                "category": "图形和编码优化",
                "name": "关闭桌面合成（Aero效果）",
                "description": "即使客户端请求也禁用桌面合成，通常可提高性能",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "fAllowDesktopCompositionOnServer",
                "enable_value": 0,
                "disable_action": "delete"
            },
            {
                "category": "图形和编码优化",
                "name": "关闭字体平滑（ClearType等）",
                "description": "为远程会话禁用字体平滑。如果看到文本渲染问题请启用此选项",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "fNoFontSmoothing",
                "enable_value": 1,
                "disable_action": "delete"
            },
            
            # RemoteFX高级功能
            {
                "category": "RemoteFX高级功能",
                "name": "启用RemoteFX虚拟化图形",
                "description": "启用虚拟化 GPU 加速",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "fEnableVirtualizedGraphics",
                "enable_value": 1,
                "disable_action": "delete"
            },
            {
                "category": "RemoteFX高级功能",
                "name": "启用RemoteFX图形配置文件",
                "description": "优化图形渲染性能",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "GraphicsProfile",
                "enable_value": 2,
                "disable_action": "delete"
            },
            {
                "category": "RemoteFX高级功能",
                "name": "启用RemoteFX高级远程应用",
                "description": "提升远程应用的图形体验",
                "path": r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services",
                "key": "fEnableRemoteFXAdvancedRemoteApp",
                "enable_value": 1,
                "disable_action": "delete"
            }
        ]
        
        self.setup_ui()
        self.checkboxes = []
        self.create_checkboxes()
        self.refresh_state()
    
    def setup_ui(self):
        """设置UI界面"""
        
        # 说明
        instruction_label = tk.Label(self.root, 
            text="说明：勾选启用，取消勾选恢复默认（不一定禁用）",
            wraplength=600, justify="center")
        instruction_label.pack(pady=5)
        
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        
        # 创建Canvas和Scrollbar用于滚动
        self.canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill=tk.BOTH, expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # RemoteFX质量设置组
        quality_frame = ttk.LabelFrame(self.root, text="RemoteFX 质量设置 (视觉体验、帧率、压缩、图像质量)")
        quality_frame.pack(fill=tk.X, padx=5, pady=5)
        
        quality_inner = ttk.Frame(quality_frame)
        quality_inner.pack(pady=5)
        
        self.quality_var = tk.StringVar(value="disabled")
        
        ttk.Radiobutton(quality_inner, text="高质量\n(富媒体)", variable=self.quality_var, 
                       value="high", command=self.apply_quality_setting).grid(row=0, column=0, padx=10)
        ttk.Radiobutton(quality_inner, text="低质量\n(文本优化)", variable=self.quality_var, 
                       value="low", command=self.apply_quality_setting).grid(row=0, column=1, padx=10)
        ttk.Radiobutton(quality_inner, text="禁用\n(系统默认)", variable=self.quality_var, 
                       value="disabled", command=self.apply_quality_setting).grid(row=0, column=2, padx=10)
        
        self.custom_label = tk.Label(quality_inner, text="[自定义值]", fg="red")
        self.custom_label.grid(row=0, column=3, padx=10)
        self.custom_label.grid_remove()
        
        # 按钮框架
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="刷新", command=self.refresh_state).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重启RDP", command=self.restart_rdp).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=self.root.quit).pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_label = tk.Label(self.root, text="状态: 就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_checkboxes(self):
        """按分类创建复选框和描述标签"""
        # 配置分类框架样式（蓝色标题）
        style = ttk.Style()
        style.configure("Blue.TLabelframe.Label", foreground="blue", font=("微软雅黑", 12, "bold"))
        
        # 按分类分组配置项
        categories = {}
        for mod in self.registry_mods:
            category = mod.get("category", "其他")
            if category not in categories:
                categories[category] = []
            categories[category].append(mod)
        
        # 为每个分类创建分组框架
        for category, mods in categories.items():
            # 创建分类标题框架（使用蓝色样式）
            category_frame = ttk.LabelFrame(self.scrollable_frame, text=category, style="Blue.TLabelframe")
            category_frame.pack(fill=tk.X, padx=8, pady=10)
            
            # 在分类框架内创建配置项
            for mod in mods:
                var = tk.IntVar()
                
                # 创建复选框
                cb = ttk.Checkbutton(category_frame, text=mod["name"], variable=var,
                                    command=lambda m=mod, v=var: self.on_checkbox_change(m, v))
                cb.pack(anchor=tk.W, pady=(0, 0), padx=12)
                
                # 创建描述标签
                if "description" in mod:
                    desc_label = tk.Label(category_frame, text=mod["description"], 
                                         wraplength=620, justify=tk.LEFT, foreground="gray",
                                         font=("微软雅黑", 9))
                    desc_label.pack(anchor=tk.W, pady=(0, 0), padx=32)
                
                self.checkboxes.append((cb, var, mod))
    
    def get_reg_value(self, path, key):
        """安全获取注册表值"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ) as reg_key:
                value, _ = winreg.QueryValueEx(reg_key, key)
                return value
        except:
            return None
    
    def set_reg_value(self, path, key, value, value_type=winreg.REG_DWORD):
        """设置注册表值"""
        try:
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, path) as reg_key:
                winreg.SetValueEx(reg_key, key, 0, value_type, value)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"设置注册表失败: {e}")
            return False
    
    def delete_reg_value(self, path, key):
        """删除注册表值"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE) as reg_key:
                winreg.DeleteValue(reg_key, key)
            return True
        except:
            return False
    
    def check_state(self, mod):
        """检查单个修改项的状态"""
        if "multi_key" in mod and mod["multi_key"]:
            # 多键值检查
            all_present = True
            all_correct = True
            
            for key_info in mod["keys"]:
                value = self.get_reg_value(mod["path"], key_info["name"])
                if value is None:
                    all_present = False
                elif value != key_info["value"]:
                    all_correct = False
            
            if not all_present:
                return "disabled"
            elif all_correct:
                return "enabled"
            else:
                return "indeterminate"
        else:
            # 单键值检查
            value = self.get_reg_value(mod["path"], mod["key"])
            if value is None:
                return "disabled"
            elif value == mod["enable_value"]:
                return "enabled"
            else:
                return "indeterminate"
    
    def apply_setting(self, mod, enable):
        """应用设置"""
        try:
            if "multi_key" in mod and mod["multi_key"]:
                # 多键值设置
                if enable:
                    for key_info in mod["keys"]:
                        self.set_reg_value(mod["path"], key_info["name"], key_info["value"])
                else:
                    for key_info in mod["keys"]:
                        self.delete_reg_value(mod["path"], key_info["name"])
            else:
                # 单键值设置
                if enable:
                    self.set_reg_value(mod["path"], mod["key"], mod["enable_value"])
                else:
                    if "disable_action" in mod and mod["disable_action"] == "delete":
                        self.delete_reg_value(mod["path"], mod["key"])
                    elif "disable_value" in mod:
                        self.set_reg_value(mod["path"], mod["key"], mod["disable_value"])
            
            self.status_label.config(text=f"状态: {'已启用' if enable else '已禁用'} - {mod['name']}")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"应用设置失败: {e}")
            return False
    
    def on_checkbox_change(self, mod, var):
        """复选框变化事件"""
        if not self.is_app_enabled:
            return
        
        enable = var.get() == 1
        if self.apply_setting(mod, enable):
            # 刷新显示状态
            current_state = self.check_state(mod)
            if current_state == "indeterminate":
                # 这里可以添加显示自定义值的标记
                pass
    
    def apply_quality_setting(self):
        """
        应用RemoteFX质量预设设置
        
        质量预设说明：
        - 高质量: 针对快速连接上的高质量连接优化，将各种压缩设置减少到最小压缩
        - 低质量: 针对次优连接优化，将各种压缩设置增加到最大压缩
        - 禁用: 恢复为系统默认设置
        
        具体配置项：
        - VisualExperiencePolicy: 视觉体验策略 (1=高质量, 2=低质量)
        - VGOptimization_CaptureFrameRate: 捕获帧率优化
        - VGOptimization_CompressionRatio: 压缩比优化
        - ImageQuality: 图像质量设置
        - MaxCompressionLevel: 最大压缩级别
        - GraphicsProfile: 图形配置文件 (2=启用RemoteFX)
        - fEnableRemoteFXAdvancedRemoteApp: 启用RemoteFX高级远程应用 (1=启用)
        """
        if not self.is_app_enabled:
            return
        
        quality = self.quality_var.get()
        path = r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"
        
        try:
            if quality == "disabled":
                # 删除所有质量设置
                keys = ["VisualExperiencePolicy", "VGOptimization_CaptureFrameRate", 
                       "VGOptimization_CompressionRatio", "ImageQuality", "MaxCompressionLevel",
                       "GraphicsProfile", "fEnableRemoteFXAdvancedRemoteApp"]
                for key in keys:
                    self.delete_reg_value(path, key)
                self.status_label.config(text="状态: 质量设置已禁用")
                self.custom_label.grid_remove()
            
            elif quality == "high":
                # 高质量设置
                self.set_reg_value(path, "VisualExperiencePolicy", 1)
                self.set_reg_value(path, "VGOptimization_CaptureFrameRate", 2)
                self.set_reg_value(path, "VGOptimization_CompressionRatio", 2)
                self.set_reg_value(path, "ImageQuality", 2)
                self.set_reg_value(path, "MaxCompressionLevel", 0)
                self.set_reg_value(path, "GraphicsProfile", 2)
                self.set_reg_value(path, "fEnableRemoteFXAdvancedRemoteApp", 1)
                self.status_label.config(text="状态: 已应用高质量设置")
                self.custom_label.grid_remove()
            
            elif quality == "low":
                # 低质量设置
                self.set_reg_value(path, "VisualExperiencePolicy", 2)
                self.set_reg_value(path, "VGOptimization_CaptureFrameRate", 3)
                self.set_reg_value(path, "VGOptimization_CompressionRatio", 3)
                self.set_reg_value(path, "ImageQuality", 4)
                self.set_reg_value(path, "MaxCompressionLevel", 3)
                self.set_reg_value(path, "GraphicsProfile", 2)
                self.set_reg_value(path, "fEnableRemoteFXAdvancedRemoteApp", 1)
                self.status_label.config(text="状态: 已应用低质量设置")
                self.custom_label.grid_remove()
        except Exception as e:
            messagebox.showerror("错误", f"应用质量设置失败: {e}")
    
    def refresh_state(self):
        """刷新所有状态"""
        self.is_app_enabled = False
        self.status_label.config(text="状态: 刷新中...")
        
        # 刷新复选框状态
        for cb, var, mod in self.checkboxes:
            state = self.check_state(mod)
            if state == "enabled":
                var.set(1)
            elif state == "disabled":
                var.set(0)
            else:  # indeterminate
                var.set(0)  # Tkinter不支持三态，这里简化处理
        
        # 刷新质量设置状态
        path = r"SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services"
        v1 = self.get_reg_value(path, "VisualExperiencePolicy")
        v2 = self.get_reg_value(path, "VGOptimization_CaptureFrameRate")
        v3 = self.get_reg_value(path, "VGOptimization_CompressionRatio")
        v4 = self.get_reg_value(path, "ImageQuality")
        v5 = self.get_reg_value(path, "MaxCompressionLevel")
        v6 = self.get_reg_value(path, "GraphicsProfile")
        v7 = self.get_reg_value(path, "fEnableRemoteFXAdvancedRemoteApp")
        
        if v1 is None and v2 is None and v3 is None and v4 is None and v5 is None and v6 is None and v7 is None:
            self.quality_var.set("disabled")
            self.custom_label.grid_remove()
        elif v1 == 1 and v2 == 2 and v3 == 2 and v4 == 2 and v5 == 0 and v6 == 2 and v7 == 1:
            self.quality_var.set("high")
            self.custom_label.grid_remove()
        elif v1 == 2 and v2 == 3 and v3 == 3 and v4 == 4 and v5 == 3 and v6 == 2 and v7 == 1:
            self.quality_var.set("low")
            self.custom_label.grid_remove()
        else:
            # 自定义值
            self.quality_var.set("disabled")  # 不选中任何选项
            self.custom_label.grid()
        
        self.is_app_enabled = True
        self.status_label.config(text="状态: 注册表值已刷新")
    
    def restart_rdp(self):
        """重启RDP服务"""
        try:
            self.status_label.config(text="状态: 正在重启RDP服务...")
            
            # 停止依赖服务
            result = subprocess.run(['powershell', '-Command', 
                'Get-Service -Name TermService -DependentServices | Where-Object { $_.Status -eq "Running" } | Stop-Service -Force'],
                capture_output=True, text=True)
            
            # 停止TermService
            subprocess.run(['net', 'stop', 'TermService'], capture_output=True)
            
            import time
            time.sleep(3)
            
            # 启动TermService
            subprocess.run(['net', 'start', 'TermService'], capture_output=True)
            
            # 启动依赖服务
            subprocess.run(['powershell', '-Command',
                'Get-Service -Name TermService -DependentServices | Start-Service'],
                capture_output=True)
            
            self.status_label.config(text="状态: RDP服务已重启")
            messagebox.showinfo("成功", "RDP服务已成功重启")
        except Exception as e:
            messagebox.showerror("错误", f"重启RDP服务失败: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RDPOptimizer(root)
    root.mainloop()