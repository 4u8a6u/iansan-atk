# attack_streamlit.py
# 伊安珊夜魂值加攻模拟 - 基于Streamlit的交互式可视化工具
# 感谢元宝deepseek帮助编写代码
# 在线访问 https://iansan-atk.streamlit.app/
# 本地部署使用指令 streamlit run attack_streamlit.py
# 默认访问本地8501端口 http://localhost:8501/

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from functools import wraps

# --------------------------
# 全局状态管理系统
# --------------------------
# 初始化会话状态（持久化存储用户交互状态）
if 'no_nightsoul_signal' not in st.session_state:
    st.session_state.update({
        'no_nightsoul_signal': 1,    # 夜魂信号状态标志位 (1-未触发，0-已触发)
        'max_level': 13,             # 元素爆发当前最大等级 (9-13级)
        'overflow_events': []        # 夜魂值溢出事件时间戳记录（用于可视化标记）
    })

# 模拟器基础参数配置
ini_atk = 3000    # 初始角色攻击力基准值（单位：点）
ini_d = 3.0       # 初始移动距离参数（游戏内前台移动系数）
decline = -6      # 夜魂值自然衰减速率（单位：点/秒）
recover = 0.67    # 夜魂值增益速率（单位：点/单位）

# 元素爆发等级与攻击力上限映射表（动态约束攻击力上限）
LEVEL_MAP = {
    9: 650,
    10: 690,
    11: 730,
    12: 770,
    13: 810
}

# --------------------------
# 核心计算引擎模块
# --------------------------
def validate_numeric_params(func):
    """参数验证装饰器（确保数值计算稳定性）
    """
    def wrapper(x, d, atk):
        d = float(d)
        atk = int(atk)
        return func(x, d, atk)
    return wrapper

def get_nightsoul(x, d):
    """夜魂值模拟
    参数：
        x : np.array - 时间序列（单位：秒）
        d : float   - 移动距离参数（游戏内动态变量）
    返回：
        np.array - 随时间变化的夜魂值数组
    算法流程：
        1. 初始化夜魂系统状态
        2. 逐秒计算自然衰减与增益效果
        3. 处理溢出存储机制
        4. 记录关键事件时间戳
    """
    # 输入预处理与类型安全保证
    x = np.asarray(x, dtype=np.float64)
    d = float(d)
    
    # 初始化计算缓冲区
    x_values = x.flatten()
    result = np.zeros_like(x_values, dtype=np.float64)
    
    # 夜魂系统初始状态
    current_value = 54.0          # 当前夜魂值（满值为54点）
    last_time = 0.0               # 上次计算时间点（用于增量计算）
    stored_overflow = 0.0         # 溢出存储池（50%溢出量存储机制）
    st.session_state.overflow_events = []  # 重置溢出事件记录
    
    # 时间序列迭代计算
    for i in range(len(x_values)):
        t = x_values[i]
        delta_t = t - last_time
        
        # 自然衰减阶段
        current_value += decline * delta_t
        
        # 增益效果计算（假设仅当移动距离参数有效时）
        if d > 0:
            # 逐秒处理机制（确保每秒触发一次增益）
            for int_sec in range(int(last_time) + 1, int(t) + 1):
                # 应用存储的溢出值（如有）
                if stored_overflow > 0:
                    current_value += stored_overflow
                    stored_overflow = 0
                
                # 前台移动增益+固有天赋基础增益
                base_gain = d * recover + 1
                current_value += base_gain
                
                # 时间点特殊增益
                extra_gain = 0
                # 自身夜魂变动+四命爆发增益（前3秒，第1秒为自身夜魂消耗，第2、3秒为四命元素爆发回复）
                if int_sec in [1, 2, 3]:
                    extra_gain += 4
                # 前台夜魂变动增益（第1、4、7、10、13秒，其中第1秒为自身变动，已经计入）
                if st.session_state.no_nightsoul_signal != 1:
                    if int_sec in [4, 7, 10, 13]:
                        extra_gain += 4
                current_value += extra_gain
                
                # 四命溢出处理（动态存储50%溢出量）
                if current_value > 54:
                    st.session_state.overflow_events.append(int_sec)  # 事件记录
                    overflow = current_value - 54
                    stored_overflow = overflow * 0.5                  # 溢出存储
                    current_value = 54                                # 当前值修正
        
        # 夜魂值上限约束
        current_value = min(current_value, 54)
        result[i] = current_value
        last_time = t

    return result

def nightsoul2atk(x, d, atk):
    """攻击力加成转换器
    参数：
        x   : np.array - 时间序列
        d   : float   - 移动距离参数
        atk : int     - 基础攻击力值
    返回：
        np.array - 受等级限制的攻击加成数组
    处理流程：
        1. 获取夜魂值曲线
        2. 计算非线性转换系数
        3. 应用元素爆发等级约束
    """
    # 获取夜魂值曲线数据
    total_nightsoul = get_nightsoul(x, d)
    
    # 分段计算
    with np.errstate(invalid='ignore'):
        factor = np.where(
            total_nightsoul >= 42.0,
            0.27,  # 最大值段
            np.clip(total_nightsoul * 0.005, 0.0, 0.27)  # 线性增长段
        )
    
    # 等级上限动态约束
    level = int(st.session_state.max_level)
    level_limit = LEVEL_MAP.get(level, 810)

    return np.minimum(atk * factor, float(level_limit))

# --------------------------
# 界面交互管理系统
# --------------------------
def init_session():
    """会话状态初始化器
    功能：
        1. 初始化参数存储结构
        2. 执行类型安全校验
    """
    if 'params' not in st.session_state:
        st.session_state.params = {
            'd': float(ini_d),
            'a': int(ini_atk)
        }
    else:
        # 类型安全强制转换
        st.session_state.params['d'] = float(st.session_state.params.get('d', ini_d))
        st.session_state.params['a'] = int(st.session_state.params.get('a', ini_atk))
    st.session_state.max_level = int(st.session_state.get('max_level', 13))

def toggle_signal():
    """夜魂信号状态切换器
    功能：翻转夜魂信号触发标志位
    """
    st.session_state.no_nightsoul_signal = 0 if st.session_state.no_nightsoul_signal == 1 else 1

def update_d():
    """移动距离参数更新器
    功能：同步滑动条与会话状态中的参数值
    """
    st.session_state.params['d'] = float(st.session_state.d_slider)

def update_a():
    """攻击力参数更新器
    功能：同步滑动条与会话状态中的参数值
    """
    st.session_state.params['a'] = int(st.session_state.a_slider)

def update_level():
    """等级参数参数更新器
    功能：同步选项与会话状态中的参数值
    """
    selected = int(st.session_state.level_selector)
    if selected != st.session_state.max_level:
        st.session_state.max_level = selected

def reset_params():
    """参数重置器
    功能：恢复默认参数并刷新界面
    """
    st.session_state.max_level = 13  # 重置为默认值
    st.session_state.params['d'] = float(ini_d)
    st.session_state.params['a'] = int(ini_atk)
    st.rerun()

# --------------------------
# 可视化渲染系统
# --------------------------
# 页面基础配置
st.set_page_config(page_title="加攻曲线", layout="wide")
st.title("伊安珊夜魂值加攻")
st.markdown("**已更新四命溢出存半效果**\n\rfrom 幽夜净土")
st.markdown("""
        ### 使用说明""")
st.markdown("""
        1. 拖动滑块实时调整参数
        3. 因伊安珊自身夜魂消耗，第1s回复4点夜魂值
        4. 4命假设0~2s期间释放了一次元素爆发，第2、3s各回复4点夜魂值
        5. 前台消耗夜魂的恢复时刻在第1、4、7、10、13s
        6. 图一为实时加攻，图二为自身夜魂，红线为6命增伤覆盖
        7. D为0时，是纯衰减情况""")
init_session()

# 双列布局系统比例
col_chart, col_control = st.columns([5, 3])

with col_chart:
    # 双轴图表系统配置
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), sharex=False)
    
    # 通用样式配置
    grid_style = {
        'linewidth': 0.7,
        'alpha': 0.6,
        'color': '#444444',
        'linestyle': '--'
    }

    # 数据生成系统
    x = np.linspace(0, 15.1, 151, dtype=np.float64)  # 时间序列生成（0-15.1秒，151采样点）
    y_atk = nightsoul2atk(x, st.session_state.params['d'], st.session_state.params['a'])
    y_ns = get_nightsoul(x, st.session_state.params['d'])

    # 攻击力曲线渲染系统
    ax1.plot(x, y_atk, color='#1f77b4', linewidth=1.5)
    ax1.axvspan(2, 15, facecolor='#fff8c4', alpha=0.3)    # 有效时间区间标记
    ax1.axvspan(2, 12, facecolor='#fff8c4', alpha=0.6)    # 核心增益区间标记
    ax1.axhline(810, color='#d62728', linestyle='--', linewidth=1.5, alpha=0.6)  # 13级参考线
    # ax1.axhline(690, color='#d62728', linestyle='--', linewidth=1.5, alpha=0.6)  # 10级参考线
    ax1.grid(**grid_style)
    ax1.set_title("ATK Boost Curve", fontsize=14, fontweight='bold')
    ax1.set_ylabel("ATK Bonus", fontsize=12)
    ax1.set_xlabel("Time (s)", fontsize=12)
    ax1.set_xlim(-3, 20)      # 扩展时间轴范围
    ax1.set_ylim(-20, 1010)   # 留出底部空白区域
    ax1.set_xticks(range(-2, 20))
    ax1.set_yticks(range(0, 1010, 100))

    # 夜魂值曲线渲染系统
    ax2.plot(x, y_ns, color='#2ca02c', linewidth=1.5)
    ax2.axvspan(2, 15, facecolor='#fff8c4', alpha=0.3)    # 有效时间区间标记
    ax2.axvspan(2, 12, facecolor='#fff8c4', alpha=0.6)    # 核心增益区间标记
    ax2.axhline(54, color='#d62728', linestyle='--', linewidth=1, alpha=0.6)  # 最大值参考线
    ax2.axhline(42, color='#d62728', linestyle='--', linewidth=1, alpha=0.6)  # 分界参考线

    for event_time in st.session_state.overflow_events:   # 六命溢出增伤
        start = max(event_time, 0)
        end = min(event_time + 3, 20)
        ax2.axvspan(start, end, ymin=0.42, ymax=0.43, color='red', alpha=0.3)

    ax2.grid(**grid_style)
    ax2.set_title("Nightsoul Value", fontsize=14, fontweight='bold')
    ax2.set_ylabel("Nightsoul Value", fontsize=12)
    ax2.set_xlabel("Time (s)", fontsize=12)
    ax2.set_xlim(-3, 20)
    ax2.set_ylim(-2, 62)     # 留出底部空白区域
    ax2.set_xticks(range(-2, 20))
    ax2.set_yticks(range(0, 62, 5))

    plt.tight_layout()
    st.pyplot(fig)

with col_control:
    # 控制面板系统
    st.markdown("### 参数设置")
    
    # 动态等级选择器
    levels = sorted(LEVEL_MAP.keys())
    selected_level = st.selectbox(
        "元素爆发等级",
        options=sorted(LEVEL_MAP.keys()),
    format_func=lambda x: f"{x}级（上限{LEVEL_MAP[x]}）",
    index=sorted(LEVEL_MAP.keys()).index(st.session_state.max_level),  # 动态绑定当前值
    key='level_selector',
    on_change=update_level
    )
    
    # 参数调节系统
    d = st.slider(
        "前台每秒移动距离D (0-9)", 0.0, 9.0, 
        value=float(st.session_state.params['d']), 
        step=0.05,
        key='d_slider', 
        on_change=update_d
    )
    a = st.slider(
        "伊安珊自身攻击力A (1200-6000)", 1200, 6000,
        value=int(st.session_state.params['a']), 
        step=50,
        key='a_slider', 
        on_change=update_a
    )
    
    # 操作按钮系统
    col1, col2 = st.columns(2)
    with col1:
        if st.button("重置参数\n\r（D为3，A为3000）"):
            reset_params()
    with col2:
        btn_label = "切换前台\n\r（当前：{}）".format(
            "非夜魂" if st.session_state.no_nightsoul_signal == 1 else "夜魂"
        )
        if st.button(btn_label):
            toggle_signal()
            st.rerun()

    # 实时监控系统
    st.markdown("---\n### 实时值")
    current_time = st.slider("时间点", 0.0, 15.0, 0.0, 0.1)
    
    # 时间点定位算法（最近邻插值）
    idx = np.searchsorted(x, current_time, side='left')
    if idx >= len(x):
        idx = len(x) - 1
    elif idx > 0:
        prev_diff = current_time - x[idx-1]
        next_diff = x[idx] - current_time
        if prev_diff > next_diff:
            idx = idx
    idx = min(max(idx, 0), len(x)-1)

    # 数值显示系统
    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.metric("夜魂值", f"{y_ns[idx]:.3f}" if len(y_ns) > 0 else "N/A") 
    with col_metric2:
        st.metric("攻击加成", f"{y_atk[idx]:.0f}" if len(y_atk) > 0 else "N/A")
