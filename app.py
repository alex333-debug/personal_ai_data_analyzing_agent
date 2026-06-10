import streamlit as st
import pandas as pd
import os
import datetime
import yfinance as yf
import akshare as ak
from smolagents import CodeAgent, OpenAIModel, tool

st.set_page_config(page_title="AI 首席数据分析师", page_icon="📈")
st.title("📈 AI 首席数据分析师")
st.markdown("我支持读取 **TXT、CSV 和 Excel (XLSX)** 文件，接入了全球股市实时数据，并具备自动清洗能力！")

TOP_20_TECH_STOCKS = {
    "苹果": "AAPL", "微软": "MSFT", "英伟达": "NVDA", "谷歌": "GOOGL", "亚马逊": "AMZN",
    "Meta(脸书)": "META", "台积电": "TSM", "博通": "AVGO", "特斯拉": "TSLA", "阿斯麦": "ASML",
    "三星": "005930.KS", "腾讯": "0700.HK", "超微半导体": "AMD", "甲骨文": "ORCL", "高通": "QCOM",
    "奈飞": "NFLX", "思科": "CSCO", "英特尔": "INTC", "IBM": "IBM", "应用材料": "AMAT"
}

@tool
def read_any_document(file_path: str) -> str:
    """这是一个超级文档读取工具，支持读取 .txt、.csv、.xlsx 和 .xls 文件。
    如果用户上传了表格，请优先调用此工具获取清洗后的内容。
    Args:
        file_path: 目标文件的具体路径（例如 'data.xlsx'）。
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ 错误：找不到文件 {file_path}，请检查路径。"
        
        ext = os.path.splitext(file_path)[-1].lower()
        
        # 1. 处理文本文件
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f"【TXT文件内容】:\n{f.read()}"
        
        # 2. 处理表格文件 (CSV 和 Excel)
        elif ext in ['.csv', '.xlsx', '.xls']:
            if ext == '.csv':
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='gbk')
                except Exception:
                    df = pd.read_csv(file_path, encoding='gbk', sep=None, engine='python', on_bad_lines='skip')
            else:
                # 🌟 新增：读取 Excel 文件（默认读取第一个工作表 Sheet）
                df = pd.read_excel(file_path)
            
            # ==========================================
            # 自动清洗装甲：无论 CSV 还是 Excel，上传即刻清洗
            # ==========================================
            df = df.dropna(how='all') # 删掉全空行
            # ==========================================
            
            summary = (
                f"【表格结构】包含 {df.shape[0]} 行, {df.shape[1]} 列。\n"
                f"【列名】: {list(df.columns)}\n"
                f"【前 20 行干净数据预览】:\n{df.head(20).to_markdown()}"
            )
            return summary
        else:
            return f"❌ 错误：不支持的文件类型 {ext}。"
            
    except Exception as e:
        return f"❌ 错误：读取或自动清洗文件时发生异常：{str(e)}"
    
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
    # ---------------------------------------------------------
    clean_a_share_code = ""
    if len(ticker) == 6 and ticker.isdigit():
        clean_a_share_code = ticker
    elif ticker.endswith('.SS') or ticker.endswith('.SZ'):
        clean_a_share_code = ticker.split('.')[0]

    # ... 下面的 try/except 逻辑保持不变 ...

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days+5}d") 
        if not hist.empty:
            recent_data = hist.tail(days)['Close'].round(2)
            trend_str = f"📈 【{ticker} (数据源: Yahoo Finance) 最近 {len(recent_data)} 个交易日收盘价】:\n"
            for date, price in recent_data.items():
                trend_str += f"- {date.strftime('%Y-%m-%d')}: {price}\n"
            return trend_str
    except Exception:
        pass 
        
    if clean_a_share_code:
        try:
            stock_df = ak.stock_zh_a_hist(symbol=clean_a_share_code, adjust="qfq")
            if not stock_df.empty:
                recent_data = stock_df.tail(days)
                trend_str = f"📈 【A 股 {clean_a_share_code} (数据源: AKShare) 最近 {len(recent_data)} 个交易日收盘价】:\n"
                for index, row in recent_data.iterrows():
                    trend_str += f"- {row['日期']}: ¥{row['收盘']}\n"
                return trend_str
        except Exception:
            pass

    return f"❌ 终极查询失败：无法获取到 {ticker} 的股票数据。"

@st.cache_resource
def get_agent():
    # 🔑 注意：部署到云端时，请确保配置了 st.secrets["DEEPSEEK_API_KEY"]
    model = OpenAIModel(
        model_id="deepseek-chat",
        api_base="https://api.deepseek.com/v1",
        api_key=st.secrets["DEEPSEEK_API_KEY"]
    )
    return CodeAgent(tools=[read_any_document, get_global_stock_trend], model=model, add_base_tools=True)

agent = get_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []
    
with st.sidebar:
    st.subheader("📂 私有数据上传区")
    st.markdown("把你的本地文件传给云端 Agent：")
    
    # 🌟 修改：支持接收 xlsx 和 xls 格式
    uploaded_file = st.file_uploader("支持 TXT, CSV, XLSX", type=["txt", "csv", "xlsx", "xls"])
    
    if uploaded_file is not None:
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ 文件 `{uploaded_file.name}` 已就绪！")
        
        # 👇 这里的 if 和上面的 with open 必须严格垂直对齐
        if st.button(f"📊 一键探索表结构与数据"):
            file_prompt = f"""请调用文档读取工具，读取刚才上传的 `{uploaded_file.name}`。
请作为资深数据分析师执行以下探查：
1. 【概览】这份表总共有多少行、多少列？包含哪些关键字段？
2. 【缺失值诊断】请观察数据中的空值（NaN）。如果是类似“物流单号”的合理空缺（如已退款订单），请保持原样；如果发现由于“Excel合并单元格”导致的某几列出现连续规律性空缺（如序号、产品类别），请你编写 Python 代码专门对那几列使用 `.ffill()` 进行向下填充清洗。
3. 【业务推测】根据前几行数据，推测这是一份什么业务的数据表？"""
            st.session_state.quick_action = file_prompt
            
    st.divider()
    
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

if "quick_action" in st.session_state:
    user_input = st.session_state.quick_action
    del st.session_state.quick_action

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        with st.spinner("数据分析师正在后台写代码、查文件..."):
            today_str = datetime.datetime.now().strftime("%Y年%m月%d日")
            smart_prompt = f"【系统提示：今天是真实的物理世界日期 {today_str}】\n用户指令：{user_input}"
            
            raw_answer = str(agent.run(smart_prompt))
            final_answer = raw_answer.replace("$", r"\$")
            st.markdown(final_answer)
            
    st.session_state.messages.append({"role": "assistant", "content": final_answer})
