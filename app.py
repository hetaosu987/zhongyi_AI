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

# 核心修改：如果没有有效的 Key，直接停止运行并提示用户
if not api_key or "YOUR_API_KEY" in api_key:
    st.error("⚠️ 未检测到有效的 API Key！")
    st.info("请在 .streamlit/secrets.toml 中配置 API_KEY，或在 Streamlit Cloud 后台设置 Secrets。")
    st.stop()

client = ZhipuAI(api_key=api_key)

# 最大轮次改为 8
MAX_TURNS = 8

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
        # 允许 AI 自主决定何时结束问诊
        system_prompt = f"""
        你是一位经验丰富的中医主任医师，精通《黄帝内经》《伤寒杂病论》，擅长体质辨证。
        
        【阶段一：问诊】
        1.  态度亲切，称呼“您”。
        2.  **每次仅问1个核心问题**。
        3.  你最多可以问 {MAX_TURNS} 个问题。
        4.  **重要：智能收尾机制**
            - 如果你在 {MAX_TURNS} 轮之前，已经收集到了足够的症状信息（寒热、汗液、二便、饮食、睡眠、情志、舌象等）足以精准辨证，**请直接停止提问，立即输出诊断报告**。
            - 不需要等待用户说“描述完毕”，你可以主动给出结果。
            - 如果信息不足，继续提问，直到第 {MAX_TURNS} 轮。
        
        【阶段二：诊断报告】
        当决定生成报告时，**必须严格**遵循以下Markdown板块（不少于800字）：
        
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

# === [修改点 3] 核心修复：优化生成回复选项的逻辑 ===
def generate_smart_replies(last_ai_question):
    try:
        # 修改 prompt：专门处理“A还是B”的选择题
        prompt = f"""
        任务：基于中医问诊场景，帮患者预判3个回答。
        医生刚才问：“{last_ai_question}”
        
        要求：
        1. 如果医生问的是“是否...”的简单问题，输出：是|否|不清楚。
        2. **重点**：如果医生问的是“选择题”（例如：是A还是B？有没有A或者B？），**必须输出具体选项**。
           - 例：“睡不着还是盗汗？” -> 输出：睡不着|盗汗|都有|都没有
           - 例：“口干还是口苦？” -> 输出：口干|口苦|又干又苦
           - **绝对不要**在这种情况下输出简单的“是/否”。
        3. 答案不要超过6个字。
        4. 直接输出3-4个答案，用竖线 "|" 分隔。
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
            
        return options[:4] # 取前4个，适应“A|B|都|无”的情况
    except Exception as e:
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
        st.caption(f"问诊进度 (最大 {MAX_TURNS} 轮)")
        # 进度条只是视觉参考
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
        
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 12px; padding: 10px 0; background-color: rgba(0,0,0,0.02); border-radius: 5px;'>
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
        # 如果消息内容是生成报告的隐藏指令，则跳过显示
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
        # [修改] 只有在达到绝对最大上限时才强制触发，否则交给 AI 或用户按钮决定
        if st.session_state.turn_count >= MAX_TURNS:
            st.session_state.messages.append({
                "role": "user", 
                "content": CMD_GENERATE_REPORT
            })
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
        # 判断是否正在生成报告（通过轮次 或 指令 或 状态）
        is_generating_report_cmd = st.session_state.turn_count >= MAX_TURNS or CMD_GENERATE_REPORT in st.session_state.messages[-1]["content"]
        
        spinner_text = "🌿 小助手正在查阅古籍，撰写深度诊断报告..." if is_generating_report_cmd else "思考中..."

        if is_generating_report_cmd:
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
            
            # [修改点 4] 智能检测：如果 AI 的回复里包含了“深度辨证”等报告关键词，说明 AI 自动决定生成报告了
            ai_decided_to_report = "### 🩺 深度辨证" in full_response or "### 深度辨证" in full_response
            
            if is_generating_report_cmd or ai_decided_to_report:
                st.session_state.stage = 2
                st.session_state.suggested_options = []
            else:
                st.session_state.suggested_options = generate_smart_replies(full_response)
            
            st.rerun()

# 3. 问诊中
if st.session_state.stage == 1:
    if st.session_state.messages[-1]["role"] == "assistant" and st.session_state.suggested_options:
        st.caption(f"请选择您的具体情况，或手动输入 (当前第 {st.session_state.turn_count} 轮)")
        cols = st.columns(len(st.session_state.suggested_options))
        for i, option in enumerate(st.session_state.suggested_options):
            if cols[i].button(option):
                handle_user_input(option)
        
        st.markdown("---")
        # [修改点 5] 用户主动触发按钮
        if st.button("✅ 结束问诊，生成养生诊断报告", type="primary", use_container_width=True):
            # 发送隐形指令
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


