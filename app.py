import streamlit as st
import random
import time
from zhipuai import ZhipuAI

# ================= 0. 基础配置 =================
# 尝试获取API KEY，如果没配置secrets则提示
try:
    api_key = st.secrets["API_KEY"]
except:
    # 为了防止报错，这里放一个占位符，或者你可以临时硬编码方便调试
    api_key = "你的_API_KEY_在这里" 
    # st.warning("未检测到 .streamlit/secrets.toml 配置，请确保API KEY正确。")

client = ZhipuAI(api_key=api_key)
MAX_TURNS = 5 

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
        prompt = f"请生成一条关于中医“{theme}”的养生小知识。要求：简短（30字以内），通俗易懂，必须包含emoji，语气亲切。不要解释，直接给内容。"
        
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
        system_prompt = f"""
        你是一位经验丰富的中医专家，精通《黄帝内经》与《伤寒杂病论》。
        
        【阶段一：问诊（前{MAX_TURNS}轮）】
        1. 态度亲切，称呼用户为“您”。
        2. 每次 **只问 1 个** 短问题，抓取核心症状（寒热/汗/便/食/眠/情志）。
        
        【阶段二：诊断（当收到“描述完毕”或达到轮数上限）】
        **请输出一份详尽的、高质量的中医诊断报告（字数不少于600字）。**
        必须严格包含以下Markdown板块：
        
        ### 🩺 深度辨证
        (分析病机、阴阳虚实、体质判断)
        
        ### 📜 经典溯源
        > 必须引用《黄帝内经》、《寒杂病论》等中医经典原文。
        *   **释义**：用通俗的语言解释这段古文的含义，并说明它如何对应用户的症状。
        
        ### 🍵 膳食良方
        1.  推荐2款具体食疗方，严格遵循格式：【方名】+【食材】（标注具体克数，选日常易采购食材）+【做法】（3-4步内，简洁可操作）+【功效】（贴合用户体质/症状）+【小贴士】（1句，适配性或操作技巧）。
        2.  食疗方需贴合用户辨证结果，标注体质适配提示（慎用/优先食用），拒绝生僻食材和复杂步骤。

        ### 🧘 导引按跷
        1.  推荐2个关键穴位，严格遵循格式：【穴位名】（标注核心适配症状）+【位置】（详细描述+简易找法，通俗易懂）+【手法】（明确按压/揉搓，标注每次操作时间、频率，无需工具）。
        2.  穴位需与用户症状高度相关，位置描述清晰，确保新手可自行找到、操作。

        ### 🌞 起居禁忌
        1.  作息建议：3条，每条需标注具体时间/频率，结合用户体质说明原因，贴合日常可执行。
        2.  忌口清单：明确具体品类，每条标注忌口原因，补充适配的替代食材，拒绝笼统表述。

        ### 😊 情志调理
        1.  推荐1-2条简易情志调理建议，贴合用户症状（如失眠、烦躁、焦虑等），结合中医“情志致病”逻辑。
        2.  内容简洁可操作，适配日常（如静坐、听舒缓音乐等），标注调理原理，贴合用户体质。

        ### 建议结合专业中医师面诊，辨证调整调理方案
        
        【补充要求】
        1. 不使用西医术语。
        2. 语言风格专业且温和。
        """
        st.session_state.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "assistant", "content": "您好，我是您的中医智能小助手🌿。我可为您提供体质辨证、食疗方子、穴位按摩和情绪调理等养生帮助，您可以说说近日的身体状态，我来为您定制专属养生方案。"}
        ]
    
    if "stage" not in st.session_state: st.session_state.stage = 0 
    if "turn_count" not in st.session_state: st.session_state.turn_count = 0 
    if "current_tip" not in st.session_state: st.session_state.current_tip = FALLBACK_TIPS[0]
    if "suggested_options" not in st.session_state: st.session_state.suggested_options = []

# === 核心修复：优化生成回复选项的逻辑 ===
def generate_smart_replies(last_ai_question):
    try:
        # 修改 prompt：更明确的指令，防止模型输出“选项1”这种占位符
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
            temperature=0.5 # 降低温度，让格式更稳定
        )
        content = response.choices[0].message.content.strip()
        
        # 简单的清洗，防止模型加上引号或换行
        content = content.replace("\n", "").replace('"', "").replace("'", "")
        
        options = content.split("|")
        
        # 如果生成失败或不足3个，返回默认
        if len(options) < 2:
            return ["有", "没有", "不清楚"]
            
        return options[:3] # 确保只取前3个
    except Exception as e:
        # 调试时可以打印 e，生产环境直接返回兜底选项
        return ["是", "否", "不清楚"]

def reset_chat():
    del st.session_state["messages"]
    st.session_state.turn_count = 0
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
    
    if st.session_state.stage == 1:
        st.caption(f"问诊进度 ({st.session_state.turn_count}/{MAX_TURNS})")
        st.progress(min(st.session_state.turn_count / MAX_TURNS, 1.0))
    
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
    
    # 换一换按钮逻辑
    if st.button("🔄 获取新知识"):
        with st.spinner("AI正在查阅医书..."): 
            st.session_state.current_tip = get_ai_health_tip()
        st.rerun()
        
    st.markdown("---")
    st.caption("⚠️ 本产品仅为AI技术演示，内容仅供参考，不能替代专业医疗诊断。")

# ================= 4. 主逻辑控制 =================
st.title("🌿 中医智能小助手")

# 渲染历史
for message in st.session_state.messages:
    if message["role"] != "system":
        # [核心修改] 如果消息内容是生成报告的隐藏指令，则跳过显示，不渲染出气泡
        if message["content"] == CMD_GENERATE_REPORT:
            continue
            
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_user_input(text):
    st.session_state.messages.append({"role": "user", "content": text})
    
    if st.session_state.stage == 0:
        st.session_state.stage = 1
    
    if st.session_state.stage == 1:
        st.session_state.turn_count += 1
        # [修改] 达到轮数上限，自动发送隐形指令
        if st.session_state.turn_count >= MAX_TURNS:
            st.session_state.messages.append({
                "role": "user", 
                "content": CMD_GENERATE_REPORT # 这里替换为变量
            })
    st.rerun()

# 1. 首页 (应用了大图标 CSS)
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
        is_generating_report = st.session_state.turn_count >= MAX_TURNS or "描述完" in st.session_state.messages[-1]["content"]
        spinner_text = "🌿 小助手正在查阅古籍，撰写深度诊断报告..." if is_generating_report else "思考中..."
        
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
            
            if is_generating_report:
                st.session_state.stage = 2
                st.session_state.suggested_options = []
            else:
                st.session_state.suggested_options = generate_smart_replies(full_response)
            
            st.rerun()

# 3. 问诊中
if st.session_state.stage == 1:
    if st.session_state.messages[-1]["role"] == "assistant" and st.session_state.suggested_options:
        st.caption(f"请选择您的情况，或在下方对话框手动输入(第 {st.session_state.turn_count}/{MAX_TURNS} 轮)")
        cols = st.columns(len(st.session_state.suggested_options))
        for i, option in enumerate(st.session_state.suggested_options):
            if cols[i].button(option):
                handle_user_input(option)
        
        st.markdown("---")
        if st.button("💪 描述完毕，直接看结果", type="primary", use_container_width=True):
            # [修改] 点击按钮，发送隐形指令
            handle_user_input(CMD_GENERATE_REPORT) # 这里替换为变量

# 4. 结果页 (新增下载按钮)
if st.session_state.stage == 2:
    st.success("✅ 深度诊断报告已生成")
    
    # === 新增功能：下载/打印按钮 ===
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
    if c1.button("🍲 七日食谱"): handle_user_input("请再推荐一个适合我的七日食疗方，要有具体做法。")
    if c2.button("🚫 详细忌口"): handle_user_input("请列出我绝对不能吃的食物清单。")
    if c3.button("🍵 茶饮调理"): handle_user_input("平时上班适合喝什么茶？")
    if c4.button("💆 更多穴位"): handle_user_input("还有什么穴位可以按？")

# 5. 输入框
if prompt := st.chat_input("输入回答..."):

    handle_user_input(prompt)


