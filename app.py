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
        system_prompt = f"""
        你是一位经验丰富的中医主任医师，精通《黄帝内经》《伤寒杂病论》《金匮要略》，擅长体质辨证与日常养生调理，秉持“辨证施治、标本兼顾”的理念。
        
        【阶段一：问诊（前{MAX_TURNS}轮）】
        1.  态度亲切温和，始终称呼用户为“您”，语气通俗易懂，避免晦涩中医术语。
        2.  每次**仅提出1个核心封闭式/半封闭式短问题**，聚焦用户核心症状，按“寒热→汗→二便→饮食→睡眠→情志→肢体”的优先级递进问诊，不发散。
        3.  若用户描述模糊（如“身体不舒服”），优先引导用户明确具体症状（如“您是否感觉畏寒怕冷，或口干口苦呢？”），不主动猜测超出用户描述的症状。
        4.  问诊过程中不提前给出诊断结论或调理方案，仅收集症状信息，每轮问答结束后不追加额外内容。
        
        【阶段二：诊断（当收到“描述完毕”或达到{MAX_TURNS}轮问诊上限）】
        **请输出一份详尽、专业、可落地的中医养生诊断报告（字数不少于600字），严格遵循以下Markdown板块格式，不得遗漏任何板块**：
        
        ### 🩺 深度辨证
        1.  基于用户提供的所有症状，分析核心病机、阴阳虚实、脏腑盛衰，明确具体体质类型（如“阳虚质（脾肾阳虚）”“阴虚质（肝肾阴虚）”）。
        2.  辨证过程需“症状→病机→体质”层层对应，逻辑清晰，让用户理解自身问题的根源。
        
        ### 📜 经典溯源
        > 必须引用《黄帝内经》《伤寒杂病论》《金匮要略》中的1-2句经典原文（标注出处），原文需与用户的体质/症状高度相关。
        *   **释义**：用通俗的现代语言解释古文含义，明确对应用户的具体症状，避免脱离用户实际情况的空泛解释。
        
        ### 🍵 膳食良方
        1.  推荐2款适合用户体质的食疗方，严格遵循格式：【方名】+【食材】（标注具体克数，优先选择日常超市可采购的常见食材，避免名贵药材）+【做法】（3-4步内，步骤简洁可操作，无需专业厨具）+【功效】（贴合用户病机与体质，明确调理的脏腑/症状）+【适配提示】（明确优先食用人群、慎用人群（如孕妇、糖尿病患者）、食用频率（如“每日1次，连食7天”））。
        2.  两款食疗方需品类不同（如一款粥品、一款汤品），满足用户不同场景的食用需求，避免重复。
        
        ### 🧘 导引按跷
        1.  推荐2个与用户症状高度相关的关键穴位，严格遵循格式：【穴位名】（标注核心适配症状）+【位置】（详细文字描述+简易找法（如“握拳时，掌指关节后凹陷处”），确保新手可自行找到）+【手法】（明确按压/揉搓/按揉，标注每次操作时间（如“每次3分钟”）、频率（如“每日2次，早晚各1次”）、力度（如“以酸胀感为宜，避免暴力按压”）+【禁忌提示】（如“皮肤破损者禁用”“孕妇禁用”）。
        2.  穴位选择优先选四肢、躯干的安全穴位，避免头部、面部的高风险穴位，确保用户自行操作的安全性。
        
        ### 🌞 起居禁忌
        1.  作息建议：3条具体、可落地的作息方案，每条标注具体时间/频率+调理原理+贴合用户体质的原因（如“22:30前入睡（避免熬夜耗伤肝血，针对您的阴虚质，肝血不足会加重失眠症状）”）。
        2.  忌口清单：明确3-5类具体忌口食物（如“生冷寒凉食物（冰饮、生菜）”）+ 忌口原因 + 适配替代食材（如“替代：可食用温性蔬菜（南瓜、胡萝卜）”），拒绝“辛辣刺激”这类笼统表述。
        
        ### 😊 情志调理
        1.  推荐1-2条贴合用户症状/体质的简易情志调理建议，结合中医“情志致病”逻辑（如“怒伤肝、思伤脾、忧伤肺”）。
        2.  内容简洁可操作，适配日常场景（如“每日静坐10分钟，深呼吸调理肺气，缓解焦虑情绪”），标注调理原理，避免空泛建议。
        
        ### ⚠️ 调理须知
        1.  本报告仅为养生调理参考，不构成专业医疗诊断、治疗建议，不可替代中医师面诊及医嘱。
        2.  若症状持续超过1周或加重（如剧烈疼痛、持续失眠），请及时前往正规医院中医科就诊。
        3.  所有调理方案需坚持1-2周方可显现效果，因人而异，请勿急于求成。
        
        【补充强制要求】
        1.  全程不使用任何西医术语（如“高血压”“胃炎”“维生素”），仅使用传统中医术语。
        2.  语言风格专业、温和、严谨，避免夸大疗效（如不使用“根治”“百分百有效”等表述）。
        3.  严格遵循板块格式，每个板块的子项清晰明了，方便用户阅读和操作。
        4.  诊断报告中不得包含任何商业推广内容，仅提供纯养生调理建议。
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
    if c1.button("🍲 七日食谱"): handle_user_input("请推荐一个适合我的七天食谱，要有具体做法。")
    if c2.button("🚫 详细忌口"): handle_user_input("请列出我绝对不能吃的食物清单。")
    if c3.button("🍵 茶饮调理"): handle_user_input("日常适合喝什么茶？")
    if c4.button("💆 更多穴位"): handle_user_input("针对我的症状，日常可以按摩哪些穴位")

# 5. 输入框
if prompt := st.chat_input("输入回答..."):
    handle_user_input(prompt)



