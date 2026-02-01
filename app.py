import streamlit as st
import random
import time
from zhipuai import ZhipuAI

# ================= 0. 基础配置 =================
# 尝试获取API KEY
try:
    api_key = st.secrets["API_KEY"]
except:
    # 修复：这里必须用空字符串或英文，不能用中文，否则会报 UnicodeEncodeError
    api_key = "" 

# 如果没有Key，给出提示但允许代码运行（避免直接崩溃）
if not api_key:
    # 仅在本地调试时可以使用硬编码Key，但在云端必须用Secrets
    # api_key = "YOUR_KEY" 
    pass

client = ZhipuAI(api_key=api_key)

# [修改] 移除了 MAX_TURNS 常量，因为不再限制轮次

CMD_GENERATE_REPORT = "我描述完了。请按照规定的Markdown格式，引用古籍，给出详细的、篇幅较长的诊断报告（包含具体的食疗方做法和穴位位置）。"

st.set_page_config(page_title="国医AI智能问诊", page_icon="🌿", layout="wide")

# ================= 1. CSS：样式优化 (保持不变) =================
st.markdown("""
<style>
    /* 全局背景 */
    .stApp {
        background-color: #f7f5f0;
        background-image: url("https://www.transparenttextures.com/patterns/cream-paper.png");
    }
    
    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background-color: #ece8e1;
        border-right: 1px solid #dcd3c9;
    }

    /* 聊天气泡布局 */
    div[data-testid="stChatMessage"] { padding: 1rem; }
    
    /* AI 报告卡片 */
    div[data-testid="stChatMessage"]:nth-child(odd) div[data-testid="stMarkdownContainer"] {
        background-color: #ffffff;
        color: #333;
        padding: 25px;
        border-radius: 4px 15px 15px 15px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08); 
        line-height: 1.7;
        font-size: 15px;
    }
    
    /* 用户气泡 */
    div[data-testid="stChatMessage"]:nth-child(even) { flex-direction: row-reverse; }
    div[data-testid="stChatMessage"]:nth-child(even) div[data-testid="stMarkdownContainer"] {
        background-color: #eaddcf; 
        color: #5d4037;
        padding: 15px;
        border-radius: 15px 15px 4px 15px;
        border: 1px solid #d7ccc8;
    }

    /* Markdown 标题美化 */
    div[data-testid="stMarkdownContainer"] h3 {
        background: linear-gradient(to right, #f4f0ec, #fff);
        color: #8d6e63;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 6px solid #8d6e63;
        margin-top: 30px;
        margin-bottom: 15px;
        font-size: 18px;
        font-weight: 700;
    }
    div[data-testid="stMarkdownContainer"] strong { color: #8d6e63; }
    div[data-testid="stMarkdownContainer"] blockquote {
        background-color: #faf9f6;
        border-left: 3px solid #d7ccc8;
        color: #666;
        font-family: "KaiTi", "楷体", serif;
        padding: 10px 15px;
        margin: 10px 0;
    }

    /* --- 通用按钮样式 --- */
    .stButton button {
        background-color: #fffaf5 !important;
        color: #5d4037 !important;
        border: 1px solid #d7ccc8 !important;
        border-radius: 8px !important;
    }
    .stButton button:hover {
        background-color: #eaddcf !important;
        transform: translateY(-2px);
    }
    button[kind="primary"] {
        background-color: #8d6e63 !important;
        color: white !important;
        border: none !important;
    }
    
    /* === 首页大图标卡片样式 === */
    .start-screen-buttons button {
        height: 120px !important;
        font-size: 24px !important;
        font-weight: bold !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 10px rgba(141, 110, 99, 0.1) !important;
        border: 2px solid #eaddcf !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        border-radius: 15px !important;
    }
    .start-screen-buttons button:hover {
        border-color: #8d6e63 !important;
        transform: scale(1.02) !important;
    }

    /* 下载按钮特别样式 */
    .download-btn-container {
        text-align: center;
        margin-top: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 备用本地知识库 (防止API调用失败时使用)
FALLBACK_TIPS = [
    "🥤 晨起一杯温水，唤醒肠胃，助阳气升发。",
    "🦶 睡前泡脚20分钟，微微出汗即可，胜吃补药。",
    "😴 子时大睡（23点-1点），此时胆经当令，最养肝血。"
]

# ================= 2. 逻辑函数与状态 =================

# 调用AI生成随机养生知识的函数
def get_ai_health_tip():
    """让AI随机生成一条养生建议"""
    try:
        themes = ["饮食", "睡眠", "运动", "情志", "四季", "穴位", "饮茶"]
        theme = random.choice(themes)
        prompt = f"""
        请生成一条关于中医“{theme}”的养生小知识，要求：
        1.  严格遵循中医理论，不包含任何西医术语，贴合《黄帝内经》等经典中医著作的核心思想。
        2.  内容简短（30字以内），通俗易懂，语气亲切，必须包含1个贴合主题的emoji。
        3.  内容具体可落地，避免空泛表述（如“不要熬夜”改为“23点前入睡，养肝血护正气”）。
        4.  不要输出任何解释性内容，直接给出养生小知识本身。
        5.  避免夸大疗效，不使用“根治”“百分百”等表述。
        """
        
        response = client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9 
        )
        return response.choices[0].message.content
    except Exception as e:
        return random.choice(FALLBACK_TIPS)

def init_state():
    if "messages" not in st.session_state:
        # [修改] System Prompt 移除了对前5轮的限制，改为智能判断
        system_prompt = f"""
        你是一位经验丰富的中医主任医师，精通《黄帝内经》《伤寒杂病论》《金匮要略》，擅长体质辨证与日常养生调理，秉持“辨证施治、标本兼顾”的理念。
        
        【问诊策略：自由辨证模式】
        1.  态度亲切温和，始终称呼用户为“您”。
        2.  **没有固定的问诊轮次限制**。请根据中医“望闻问切”的逻辑，逐一询问用户的核心症状（寒热、汗出、头身、二便、饮食、睡眠、情志等）。
        3.  每次**仅提出1个**核心封闭式/半封闭式短问题，不要一次抛出多个问题。
        4.  **智能收尾**：如果你认为已经收集到了足够的信息（明确了病机、虚实、脏腑），**不需要等待用户指令，请直接开始输出诊断报告**。
        5.  **用户主动触发**：如果用户发送“我描述完了”或“生成报告”，请立即停止发问，根据已知信息生成报告。
        
        【诊断报告生成规范】
        当决定生成报告时，请严格遵循以下Markdown板块格式，不得遗漏：
        
        ### 🩺 深度辨证
        (分析病机、阴阳虚实、体质判断)
        
        ### 📜 经典溯源
        (引用《黄帝内经》等经典，并通俗释义)
        
        ### 🍵 膳食良方
        (推荐2款食疗方：方名+食材+做法+功效+禁忌)
        
        ### 🧘 导引按跷
        (推荐2个穴位：位置+手法+频率)
        
        ### 🌞 起居禁忌
        (作息建议 + 忌口清单)
        
        ### 😊 情志调理
        (简易情志建议)
        
        ### ⚠️ 调理须知
        (免责声明与就医提示)
        
        【补充强制要求】
        1. 全程不使用任何西医术语。
        2. 语言风格专业、温和、严谨。
        """
        st.session_state.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "您好，我是您的中医智能小助手🌿。我可为您提供体质辨证、食疗方子、穴位按摩和情绪调理等养生帮助，您可以说说近日的身体状态，我来为您定制专属养生方案。"}
        ]
    
    if "stage" not in st.session_state: st.session_state.stage = 0 
    # [修改] 移除了 turn_count 初始化
    if "current_tip" not in st.session_state: st.session_state.current_tip = FALLBACK_TIPS[0]
    if "suggested_options" not in st.session_state: st.session_state.suggested_options = []

def generate_smart_replies(last_ai_question):
    try:
        prompt = f"""
        任务：基于中医问诊场景。
        医生刚才问：“{last_ai_question}”
        
        请帮患者预判3个最可能的简短回答（不要超过6个字）。
        要求：
        1. 直接输出3个答案，用竖线 "|" 分隔。
        2. 不要输出任何多余的解释、序号或前缀。
        3. 如果是是非题，输出：是|否|不清楚。
        
        正确输出示例：睡得很差|一般般|睡得很好
        错误输出示例：选项1|选项2|选项3
        """
        
        response = client.chat.completions.create(
            model="glm-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5 
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("\n", "").replace('"', "").replace("'", "")
        options = content.split("|")
        
        if len(options) < 2:
            return ["有", "没有", "不清楚"]
            
        return options[:3] 
    except Exception as e:
        return ["是", "否", "不清楚"]

def reset_chat():
    del st.session_state["messages"]
    # [修改] 移除了 turn_count 重置
    st.session_state.suggested_options = []
    init_state()
    st.session_state.stage = 0
    st.rerun()

init_state()

# ================= 3. 侧边栏 =================
with st.sidebar:
    st.markdown("""
    <div style="color:#8d6e63; font-weight:bold; font-size:18px;">
        中医智能小助手
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 开始新问诊", type="primary", use_container_width=True):
        reset_chat()
    
    # [修改] 移除了进度条显示代码
    
    st.markdown("---")
    st.caption("🛠️ 辅助功能 (待上线)")
    col_mock1, col_mock2 = st.columns(2)
    col_mock1.button("👅 AI舌诊", disabled=True, use_container_width=True)
    col_mock2.button("😐 AI面诊", disabled=True, use_container_width=True)
    col_mock3, col_mock4 = st.columns(2)
    col_mock3.button("📄 拍报告", disabled=True, use_container_width=True)
    col_mock4.button("💊 拍药盒", disabled=True, use_container_width=True)
    
    st.markdown("---")
    
    # 养生一签区域
    st.markdown(f"""
    <div style="background:#fff; padding:15px; border-radius:8px; border-left:4px solid #8d6e63; box-shadow:0 2px 5px rgba(0,0,0,0.05);">
        <div style="font-weight:bold; color:#8d6e63; margin-bottom:5px;">💡 中医养生锦囊</div>
        <div style="font-size:13px; color:#555;">{st.session_state.current_tip}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 获取新知识"):
        with st.spinner("AI正在查阅医书..."): 
            st.session_state.current_tip = get_ai_health_tip()
        st.rerun()
        
    st.markdown("<br>"*3, unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown(
        """
        <div style='
            text-align: center; 
            color: #666; 
            font-size: 12px; 
            padding: 10px 0;
            background-color: rgba(0,0,0,0.02);
            border-radius: 5px;
        '>
            ⚠️ 本产品仅为AI技术演示，内容仅供参考，不能替代专业医疗诊断。
        </div>
        """, 
        unsafe_allow_html=True
    )

# ================= 4. 主逻辑控制 =================
st.title("🌿 中医智能小助手")

# 渲染历史
for message in st.session_state.messages:
    if message["role"] != "system":
        if message["content"] == CMD_GENERATE_REPORT:
            continue
            
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_user_input(text):
    st.session_state.messages.append({"role": "user", "content": text})
    
    if st.session_state.stage == 0:
        st.session_state.stage = 1
    
    # [修改] 移除了 turn_count 增加逻辑和自动触发逻辑
    # 现在完全依赖：1.用户点击按钮触发 2.AI自动判断触发
    st.rerun()

# 1. 首页
if st.session_state.stage == 0 and len(st.session_state.messages) <= 2:
    st.markdown("### 您可能有以下困扰？")
    st.markdown('<div class="start-screen-buttons">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    if col1.button("😴 睡不着"): handle_user_input("我最近总是睡不着")
    if col2.button("💇‍♀️ 掉头发"): handle_user_input("我最近掉头发很严重")
    if col3.button("❄️ 手脚凉"): handle_user_input("我手脚总是冰凉")
    if col4.button("🤢 胃胀气"): handle_user_input("我经常胃胀气")
    st.markdown('</div>', unsafe_allow_html=True)

# 2. AI 回复
if st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        # 判断是否正在生成报告（用户触发 或 AI之前已经进入状态）
        # [修改] 判断逻辑：只要用户发了指令，或者是AI自己开始写了
        is_generating_report = "描述完" in st.session_state.messages[-1]["content"] or "生成报告" in st.session_state.messages[-1]["content"]
        
        spinner_text = "🌿 小助手正在查阅古籍，撰写深度诊断报告..." if is_generating_report else "思考中..."

        if is_generating_report:
            st.caption("💡 等候期间，可查看左侧「养生锦囊」获取实用小知识")
        
        with st.spinner(spinner_text):
            response = client.chat.completions.create(
                model="glm-4", messages=st.session_state.messages, stream=True, temperature=0.8
            )
            placeholder = st.empty()
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + " ▌")
            placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # [核心修改] 智能检测：如果AI回复中包含了报告的特征标题，自动切换到结果页
            if "### 🩺 深度辨证" in full_response or is_generating_report:
                st.session_state.stage = 2
                st.session_state.suggested_options = []
            else:
                st.session_state.suggested_options = generate_smart_replies(full_response)
            
            st.rerun()

# 3. 问诊中
if st.session_state.stage == 1:
    if st.session_state.messages[-1]["role"] == "assistant" and st.session_state.suggested_options:
        st.caption(f"请选择您的情况，或在下方对话框详细描述（AI将智能判断何时生成报告）")
        cols = st.columns(len(st.session_state.suggested_options))
        for i, option in enumerate(st.session_state.suggested_options):
            if cols[i].button(option):
                handle_user_input(option)
        
        st.markdown("---")
        # [修改] 无论第几轮，都显示“主动结束”按钮，作为保底方案
        if st.button("✅ 描述完毕，直接看结果", type="primary", use_container_width=True):
            handle_user_input(CMD_GENERATE_REPORT)

# 4. 结果页
if st.session_state.stage == 2:
    st.success("✅ 深度诊断报告已生成")
    
    report_content = st.session_state.messages[-1]["content"]
    
    col_dl1, col_dl2 = st.columns([1, 4])
    with col_dl1:
        st.download_button(
            label="📥 下载诊断报告",
            data=report_content,
            file_name="中医AI诊断报告.md",
            mime="text/markdown",
            use_container_width=True
        )
    
    st.caption("您可以继续追问详情：")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🍲 七日食谱"): handle_user_input("请推荐一个适合我的七天食谱，要有具体做法。")
    if c2.button("🚫 详细忌口"): handle_user_input("请列出我绝对不能吃的食物清单。")
    if c3.button("🍵 茶饮调理"): handle_user_input("日常适合喝什么茶？")
    if c4.button("💆 更多穴位"): handle_user_input("针对我的症状，日常可以按摩哪些穴位")

# 5. 输入框
if prompt := st.chat_input("输入回答..."):
    handle_user_input(prompt)
