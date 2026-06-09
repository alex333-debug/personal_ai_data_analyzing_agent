import streamlit as st
import pandas as pd
import os
import datetime
import yfinance as yf
import akshare as ak
from smolagents import CodeAgent, OpenAIModel, tool

st.set_page_config(page_title="AI 首席数据分析师", page_icon="📈")
st.title("AI 首席数据分析师")
st.markdown("我支持读取本地文档，并且现在**接入了全球股市实时数据**！")

TOP_20_TECH_STOCKS = {
    "苹果": "AAPL", "微软": "MSFT", "英伟达": "NVDA", "谷歌": "GOOGL", "亚马逊": "AMZN",
    "Meta(脸书)": "META", "台积电": "TSM", "博通": "AVGO", "特斯拉": "TSLA", "阿斯麦": "ASML",
    "三星": "005930.KS", "腾讯": "0700.HK", "超微半导体": "AMD", "甲骨文": "ORCL", "高通": "QCOM",
    "奈飞": "NFLX", "思科": "CSCO", "英特尔": "INTC", "IBM": "IBM", "应用材料": "AMAT"
}

@tool
def read_any_document(file_path:str)->str:
    """这是一个超级文档读取工具，支持读取 .txt 和 .csv 文件。
    Args:
        file_path: 目标文件的具体路径（例如 'data.csv'）。
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ 错误：找不到文件 {file_path}，请检查路径。"
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f"【TXT文件内容】:\n{f.read()}"
        elif ext == '.csv':
            try:
                # 第一套方案：尝试用通用的 UTF-8 读取
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                # 第二套方案：如果报错，说明是 Windows Excel 生成的表格，改用 GBK 读取
                df = pd.read_csv(file_path, encoding='gbk')
            summary = (
                f"【CSV 结构】包含 {df.shape[0]} 行, {df.shape[1]} 列。\n"
                f"【列名】: {list(df.columns)}\n"
                f"【前 20 行数据预览】:\n{df.head(20).to_markdown()}"
            )
            return summary
        else:
            return f"❌ 错误：不支持的文件类型 {ext}，请上传 .txt 或 .csv 文件。"
    except Exception as e:
        return f"❌ 错误：读取文件时发生异常：{str(e)}"
    
@tool
def get_global_stock_trend(ticker: str, days: int = 7) -> str:
    """
    这是一个终极股票查询工具，支持查询全球股票（包括美股、港股和中国 A 股）最近几天的收盘价走势。
    它内置了双数据源，会自动匹配最合适的数据源。
    
    Args:
        ticker: 股票代码。美股直接传代码（如 'AAPL'）；
                如果是中国 A 股，可以直接传 6 位纯数字代码（如 '600519'）或者带后缀的代码（如 '600519.SS'）。
        days: 需要查询的最近天数（默认 7 天）。
    """
    # ---------------------------------------------------------
    # 策略 1：清理股票代码，为 A 股查询做准备
    # 如果用户输入了 '600519.SS'，我们把 '600519' 提取出来备用
    # ---------------------------------------------------------
    clean_a_share_code = ""
    if len(ticker) == 6 and ticker.isdigit():
        clean_a_share_code = ticker
    elif ticker.endswith('.SS') or ticker.endswith('.SZ'):
        clean_a_share_code = ticker.split('.')[0]

    # ---------------------------------------------------------
    # 策略 2：优先尝试引擎 A (Yahoo Finance)
    # yfinance 处理美股、港股是无敌的
    # ---------------------------------------------------------
    try:
        stock = yf.Ticker(ticker)
        # 获取足够的数据以排除周末停盘的影响
        hist = stock.history(period=f"{days+5}d") 
        if not hist.empty:
            recent_data = hist.tail(days)['Close'].round(2)
            trend_str = f"📈 【{ticker} (数据源: Yahoo Finance) 最近 {len(recent_data)} 个交易日收盘价】:\n"
            for date, price in recent_data.items():
                trend_str += f"- {date.strftime('%Y-%m-%d')}: {price}\n"
            return trend_str
    except Exception:
        # 引擎 A 报错了！但我们不要声张（静默失败），继续往下走
        pass 
        
    # ---------------------------------------------------------
    # 策略 3：引擎 A 失败了，启动引擎 B (AKShare)
    # 只要它看起来像 A 股（提取到了 6 位数字代码），就用国内专用接口
    # ---------------------------------------------------------
    if clean_a_share_code:
        try:
            # 调用 AKShare 接口，获取历史 A 股数据（前复权）
            stock_df = ak.stock_zh_a_hist(symbol=clean_a_share_code, adjust="qfq")
            
            if not stock_df.empty:
                recent_data = stock_df.tail(days)
                trend_str = f"📈 【A 股 {clean_a_share_code} (数据源: AKShare 原生接口) 最近 {len(recent_data)} 个交易日收盘价】:\n"
                
                for index, row in recent_data.iterrows():
                    date_str = row['日期']
                    close_price = row['收盘']
                    trend_str += f"- {date_str}: ¥{close_price}\n"
                return trend_str
        except Exception:
            # 引擎 B 也报错了！静默失败，继续往下走
            pass

    # ---------------------------------------------------------
    # 策略 4：彻底失败的最终审判
    # ---------------------------------------------------------
    return (
        f"❌ 终极查询失败：双数据源均无法获取到 {ticker} 的股票数据。\n"
        f"请检查股票代码是否正确。美股请使用正确代码（如 AAPL），A 股请确保包含正确的6位数字（如 600519）。"
    )

@st.cache_resource
def get_agent():
    model = OpenAIModel(
        model_id="deepseek-chat",
        api_base="https://api.deepseek.com/v1",
        api_key=st.secrets["DEEPSEEK_API_KEY"]
    )
    return CodeAgent(tools=[read_any_document,get_global_stock_trend], model=model, add_base_tools=True)
agent = get_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []
    
with st.sidebar:
    # ==========================================
    # 新增模块：云端文件上传区
    # ==========================================
    st.subheader("📂 私有数据上传区")
    st.markdown("把你的本地文件传给云端 Agent：")
    
    # 召唤 Streamlit 的上传组件
    uploaded_file = st.file_uploader("支持 TXT 和 CSV", type=["txt", "csv"])
    
    if uploaded_file is not None:
        # 🌟 核心魔法：把用户浏览器传过来的文件，真实地写进云端服务器的硬盘里
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ 文件 `{uploaded_file.name}` 已传至云端！现在可以命令 Agent 分析它了。")
        
    st.divider() # 画一条华丽的分割线
    
    # ==========================================
    # 原有的：快捷指令区
    # ==========================================
    st.subheader("⚡ 快捷指令区")
    st.markdown("选择你想一键分析的科技巨头：")
    
    selected_company_name = st.selectbox("选择公司", list(TOP_20_TECH_STOCKS))
    selected_ticker = TOP_20_TECH_STOCKS[selected_company_name]
    
    if st.button(f"🔍 一键查询 {selected_company_name} ({selected_ticker}) 昨日走势"):
        quick_prompt = f"请调用股票工具，查询一下 {selected_company_name} ({selected_ticker}) 最近两天的收盘价，并帮我计算昨日相比前日的涨跌幅（百分比），用专业的口吻汇报。"
        st.session_state.quick_action = quick_prompt

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
user_input = st.chat_input("你也可以输入模糊名称，例如：查一下台积电最近7天的股票表现。")

# 🌟 修复 2：在这里也要统一查收 quick_action
if "quick_action" in st.session_state:
    user_input = st.session_state.quick_action
    del st.session_state.quick_action

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        with st.spinner("数据分析师正在后台写代码、查文件..."):
            
            # 🌟 修复时间认知障碍：获取电脑当前的真实日期
            today_str = datetime.datetime.now().strftime("%Y年%m月%d日")
            # 🌟 偷偷把日期塞进用户的指令里，再发给 Agent
            smart_prompt = f"【系统提示：今天是真实的物理世界日期 {today_str}】\n用户指令：{user_input}"
            
            # 🌟 修复 3：拦截 Agent 的原始回答，进行字体防断裂处理
            raw_answer = str(agent.run(user_input))
            # 把所有的 $ 替换为 \$，防止 Streamlit 误认为是 LaTeX 数学公式
            final_answer = raw_answer.replace("$", r"\$")
            
            st.markdown(final_answer)
            
    st.session_state.messages.append({"role": "assistant", "content": final_answer})