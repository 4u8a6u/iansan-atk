# attack_streamlit.py
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# 设置全局中文字体（需提前安装）
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

# 全局参数部分新增初始化状态
if 'no_nightsoul_signal' not in st.session_state:
    st.session_state.no_nightsoul_signal = 1  # 默认值设为1

# 新增切换函数
def toggle_signal():
    st.session_state.no_nightsoul_signal = 0 if st.session_state.no_nightsoul_signal == 1 else 1

ini_atk = 3000
ini_d = 1.0
decline = -6

# 核心计算函数
def nightsoul2atk(x, d, atk):
    nightsoul = decline * x + 54 
    nightsoul += np.floor(x) * (d * 0.67 + (d > 0))
    boost = np.where((x >= 1) & (d > 0), 4, 0) + \
            np.where((x >= 2) & (d > 0), 4, 0) + \
            np.where((x >= 3) & (d > 0), 4, 0)
    if st.session_state.no_nightsoul_signal != 1:
        boost += np.where((x >= 4) & (d > 0), 4, 0) + \
                 np.where((x >= 7) & (d > 0), 4, 0) + \
                 np.where((x >= 10) & (d > 0), 4, 0) + \
                 np.where((x >= 13) & (d > 0), 4, 0)

    # 步骤1：计算每个时间点对应的整秒
    int_seconds = np.floor(x).astype(int)
    # 步骤2：计算每个整秒的total_nightsoul
    # 通过np.bincount聚合每个整秒的最大值（假设每整秒内取最大值判断溢出）
    sec_max = np.bincount(int_seconds, weights=decline*x +54 + int_seconds*(d*0.67+(d>0)) + boost, minlength=16)[:16]  # 0-15秒    
    # 步骤3：计算溢出量
    overflow = np.maximum(sec_max - 42, 0)
    overflow_next = np.roll(overflow / 2, shift=-1)  # 下移一位对应i+1
    # 步骤4：映射到连续时间序列
    overflow_boost = np.where((d > 0) & (int_seconds < 15),  overflow_next[int_seconds], 0)
    
    total_nightsoul = nightsoul + boost
    factor = np.where(total_nightsoul >= 42, 0.27, total_nightsoul * 0.005)
    return np.minimum(atk * factor, 810)

# 初始化session state
def init_session():
    if 'params' not in st.session_state:
        st.session_state.params = {
            'd': ini_d,
            'a': ini_atk
        }

# 滑块回调函数
def update_d():
    st.session_state.params['d'] = st.session_state.d_slider

def update_a():
    st.session_state.params['a'] = st.session_state.a_slider

# 重置函数
def reset_params():
    st.session_state.params['d'] = ini_d
    st.session_state.params['a'] = ini_atk
    st.rerun()

# 界面布局
st.set_page_config(page_title="加攻曲线", layout="wide")
st.title("伊安珊前台粗略加攻曲线")

# 初始化session
init_session()

col1, col2 = st.columns([3, 1])

with col1:
    fig, ax = plt.subplots(figsize=(12, 6))
    
with col2:
    st.markdown("### 参数设置")
    
    # 滑块组件
    d = st.slider(
        "前台每秒移动距离D (0-8)", 
        min_value=0.0, 
        max_value=8.0, 
        value=st.session_state.params['d'],
        step=0.05,
        help="拖动滑块调整D值",
        key='d_slider',
        on_change=update_d
    )
    
    a = st.slider(
        "伊安珊自身攻击力A (1200-6000)", 
        min_value=1200, 
        max_value=6000,
        value=st.session_state.params['a'],
        step=50, 
        help="拖动滑块调整A值",
        key='a_slider',
        on_change=update_a
    )
    
    # 新增按钮布局
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("重置参数\n\r（D为1，A为3000）"):
            reset_params()
    with col_btn2:
        btn_label = "切换前台\n\r（当前：{}）".format(
            "非夜魂" if st.session_state.no_nightsoul_signal == 1 else "夜魂"
        )
        if st.button(btn_label):
            toggle_signal()
            st.rerun()

# 动态更新图表
x = np.linspace(0, 15, 600)
y = nightsoul2atk(x, st.session_state.params['d'], st.session_state.params['a'])

with col1:
    ax.clear()
    ax.plot(x, y, color='blue', linewidth=2, label='加攻曲线')

    # 新增淡黄色背景（从x=2到x=15）
    ax.axvspan(2, 15, facecolor='#fff8c4', alpha=0.3)  # 使用柔和的淡黄色
    
    # 新增红色标记逻辑（重点修改部分）
    for t in range(0, 16):  # 遍历所有整数秒
        d_val = st.session_state.params['d']
        # 基础夜魂值计算
        nightsoul = decline * t + 54 
        nightsoul += np.floor(t) * (d_val * 0.67 + (d_val > 0))
        
        # Boost计算
        boost = 0
        if t >= 1 and d_val > 0:
            boost += 4
        if t >= 2 and d_val > 0:
            boost += 4
        if t >= 3 and d_val > 0:
            boost += 4
        if st.session_state.no_nightsoul_signal != 1:
            if t >= 4 and d_val > 0:
                boost += 4
            if t >= 7 and d_val > 0:
                boost += 4
            if t >= 10 and d_val > 0:
                boost += 4
            if t >= 13 and d_val > 0:
                boost += 4

        # 步骤1：计算每个时间点对应的整秒
        int_seconds = np.floor(x).astype(int)
        # 步骤2：计算每个整秒的total_nightsoul
        # 通过np.bincount聚合每个整秒的最大值（假设每整秒内取最大值判断溢出）
        sec_max = np.bincount(int_seconds, weights=decline*x +54 + int_seconds*(d*0.67+(d>0)) + boost, minlength=16)[:16]  # 0-15秒    
        # 步骤3：计算溢出量
        overflow = np.maximum(sec_max - 42, 0)
        overflow_next = np.roll(overflow / 2, shift=-1)  # 下移一位对应i+1
        # 步骤4：映射到连续时间序列
        overflow_boost = np.where((d > 0) & (int_seconds < 15),  overflow_next[int_seconds], 0)

        total_nightsoul = nightsoul + boost
        
        # 触发条件判断
        if total_nightsoul >= 54:
            start = max(t, -5)  # 限制在可见范围
            end = min(t + 3, 20)
            ax.axvspan(start, end, ymin=0.02, ymax=0.05, 
                      color='red', alpha=0.5, linewidth=0)
    
    ax.set_title("伊安珊加攻曲线")
    ax.set_xlabel("时间（秒）")
    ax.set_ylabel("攻击力加成")
    ax.set_xlim(-5, 20)
    ax.set_ylim(-20, 1000)
    ax.set_xticks(range(-5, 21))
    ax.set_yticks(range(0, 1001, 100))
    ax.grid(True, linestyle='--', alpha=0.7)
    st.pyplot(fig)

# 侧边栏说明
with col2:
    st.markdown("""
        ### 使用说明""")
    st.markdown("""
        1. 拖动滑块实时调整参数   
        2. **没有考虑夜魂值溢出和存半效果**  
        3. 因伊安珊自身夜魂消耗，第1s回复4点夜魂值
        4. 4命假设0~2s期间释放了一次元素爆发，第2、3s各回复4点夜魂值  
        5. 前台消耗夜魂的恢复时刻在第1、4、7、10、13s  
        6. 红线为6命增伤覆盖
        7. D为0时，是纯衰减情况""")
