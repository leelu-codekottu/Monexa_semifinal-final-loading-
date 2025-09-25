import streamlit as st
import plotly.express as px
import pandas as pd
import sys
import os

# Add the project's root directory to the Python path
# This allows for absolute imports from the 'backend' package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    # Use absolute imports from the backend package
    from backend.finance_service import get_financial_data, calculate_expected_return, get_ticker_info
    from backend.news_service import get_financial_news, summarize_news_for_llm
    from backend.llm_service import get_llm_response
except ImportError as e:
    st.error(f"Error importing backend services: {e}. Please ensure the backend files exist in a 'backend' folder at the project root.")
    st.stop()


# --- Page Configuration ---
st.set_page_config(
    page_title="Monexa - Your AI Financial Advisor",
    page_icon="🤖",
    layout="wide"
)

# --- Market Data Constants ---
INDIAN_STOCKS = {
    "Low Risk": ["HDFCBANK.NS", "TCS.NS", "HINDUNILVR.NS", "INFY.NS", "RELIANCE.NS"],
    "Medium Risk": ["ICICIBANK.NS", "AXISBANK.NS", "SBIN.NS", "LT.NS", "MARUTI.NS"],
    "High Risk": ["TATAMOTORS.NS", "ZOMATO.NS", "PAYTM.NS", "YESBANK.NS", "IDEA.NS"]
}

US_STOCKS = {
    "Low Risk": ["MSFT", "AAPL", "JNJ", "PG", "KO"],
    "Medium Risk": ["GOOGL", "AMZN", "META", "NVDA", "V"],
    "High Risk": ["TSLA", "PLTR", "RIVN", "COIN", "GME"]
}

CRYPTO_TICKERS = ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD"]

MUTUAL_FUNDS = {
    "Large Cap": ["HDFC Top 100", "Axis Bluechip", "Mirae Asset Large Cap"],
    "Mid Cap": ["Kotak Emerging Equity", "HDFC Mid-Cap Opportunities", "DSP Midcap"],
    "Small Cap": ["Nippon Small Cap", "SBI Small Cap", "Axis Small Cap"]
}

# --- UI Rendering ---
# Main header with columns for better layout
col1, col2 = st.columns([1, 4])
with col1:
    st.image("https://em-content.zobj.net/source/microsoft-teams/363/robot_1f916.png", width=120)
with col2:
    st.title("Monexa AI Financial Advisor")
    st.markdown("Your personalized guide to smart investing. Let's build a plan for your financial future!")

# --- Sidebar for User Inputs ---
with st.sidebar:
    st.header("👤 Your Financial Profile")

    # Investment Type Selection
    investment_type = st.selectbox(
        "What would you like to invest in?",
        ("Stocks", "Mutual Funds", "Cryptocurrency"),
        help="Select the type of investment you're interested in"
    )

    user_inputs = {"investment_type": investment_type}

    # Market Selection for Stocks
    if investment_type == "Stocks":
        market = st.selectbox(
            "Which market would you like to invest in?",
            ("Indian Market", "US Market"),
            help="Select the stock market you want to invest in"
        )
        user_inputs["market"] = market

        # Stock search
        stock_search = st.text_input(
            "Search for specific stocks:",
            placeholder="e.g., RELIANCE.NS or AAPL",
            help="Enter stock symbol to search"
        )
        user_inputs["stock_search"] = stock_search

    # Common inputs for all investment types
    user_inputs["investment_amount"] = st.number_input(
        "How much can you invest monthly (₹)?",
        min_value=0, step=1000, value=5000,
        help="Enter the amount you can comfortably invest each month in INR"
    )
    
    user_inputs["horizon"] = st.slider(
        "What is your investment horizon?",
        min_value=1, max_value=30, value=10, format="%d years",
        help="How many years are you planning to invest for?"
    )
    
    user_inputs["risk"] = st.select_slider(
        "What is your risk tolerance?",
        options=["Low Risk", "Medium Risk", "High Risk"], 
        value="Medium Risk",
        help="Low risk aims for stable returns. High risk has potential for higher growth but also higher volatility."
    )
    
    custom_tickers_input = st.text_area(
        "Track specific tickers (optional):",
        placeholder="e.g., GOOGL, BTC-USD, AMZN",
        help="Enter any stock or crypto tickers you want to include in the analysis, separated by commas."
    )
    if custom_tickers_input:
        user_inputs["tickers"] = [ticker.strip().upper() for ticker in custom_tickers_input.split(',') if ticker.strip()]
    
    analyze_button = st.button("✨ Get My Personalized Advice", use_container_width=True, type="primary")

# --- Helper function to display results ---
def display_results(user_inputs):
    """Encapsulates the logic to fetch data, generate insights, and render UI elements."""
    try:
        # 1. Get Investment Type and Market Selection
        investment_type = user_inputs.get("investment_type")
        risk_level = user_inputs.get("risk", "Medium Risk")
        
        # 2. Fetch and Display Latest Market News
        with st.spinner("Fetching market data and news..."):
            news_data = get_financial_news()
            if "error" in news_data:
                st.warning(f"Could not fetch latest news: {news_data['error']}")
                news_context = "No recent financial news available."
            else:
                news_context = summarize_news_for_llm(news_data)
                
                # Display news in expander with plain text content
                with st.expander("📰 Latest Market News", expanded=False):
                    for article in news_data:
                        st.markdown(f"### {article['title']}")
                        if article.get('content'):
                            st.markdown(article['content'])
                        st.markdown(f"*Source: {article['source']}*")
                        st.markdown("---")

        # 3. Handle Different Investment Types
        if investment_type == "Stocks":
            market = user_inputs.get("market", "Indian Market")
            stock_list = INDIAN_STOCKS if market == "Indian Market" else US_STOCKS
            
            # Display top stocks based on risk level
            st.subheader(f"📈 Top {market.split()[0]} Stocks - {risk_level}")
            tickers_to_chart = stock_list.get(risk_level, [])[:]  # Make a copy
            # Handle custom stock search
            custom_stock = user_inputs.get("stock_search", "").strip().upper()
            if custom_stock:
                # Add .NS suffix for Indian stocks if not present
                if market == "Indian Market" and not custom_stock.endswith(".NS"):
                    custom_stock += ".NS"
                tickers_to_chart.insert(0, custom_stock)  # Add to beginning of list

            # Initialize validation lists
            invalid_tickers = []
            valid_custom = []
            
            # Handle custom tickers if provided
            custom_tickers = user_inputs.get("tickers", [])
            if custom_tickers:
                for ticker in custom_tickers:
                    if ticker:  # Skip empty strings
                        info = get_ticker_info(ticker)
                        if info:
                            valid_custom.append(ticker)
                        else:
                            invalid_tickers.append(ticker)
                
                if invalid_tickers:
                    st.warning(f"Could not find data for these tickers: {', '.join(invalid_tickers)}. They will be ignored.")
                if valid_custom:
                    tickers_to_chart.extend(valid_custom)
                    tickers_to_chart = list(dict.fromkeys(tickers_to_chart))  # Remove duplicates while preserving order
            
            # Fetch and display stock data
            with st.spinner(f"Fetching {market} stock data..."):
                stock_data = get_financial_data(tickers_to_chart, market=market.split()[0].upper())
                
                if stock_data:
                    # Create tabs for different visualizations
                    price_tab, volume_tab, compare_tab = st.tabs(["Price History", "Volume Analysis", "Comparison"])
                    
                    with price_tab:
                        for ticker, data in stock_data.items():
                            st.subheader(f"{data['name']} ({ticker})")
                            hist_df = data['historical_data']
                            
                            # Price history chart
                            fig = px.line(hist_df, x='Date', y='Close',
                                        title=f'Price History (₹)',
                                        labels={'Close': 'Price (₹)', 'Date': 'Date'})
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Key metrics
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Current Price", f"₹{data['current_price']:,.2f}")
                            col2.metric("Change", f"{data['price_change']:,.2f}%")
                            col3.metric("52W High", f"₹{data['high_52week']:,.2f}")
                            col4.metric("52W Low", f"₹{data['low_52week']:,.2f}")
                    
                    with volume_tab:
                        for ticker, data in stock_data.items():
                            hist_df = data['historical_data']
                            fig = px.bar(hist_df, x='Date', y='Volume',
                                       title=f'Trading Volume - {ticker}',
                                       labels={'Volume': 'Volume', 'Date': 'Date'})
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with compare_tab:
                        # Normalize prices for comparison
                        comparison_df = pd.DataFrame()
                        for ticker, data in stock_data.items():
                            hist_df = data['historical_data']
                            comparison_df[ticker] = hist_df['Close'] / hist_df['Close'].iloc[0] * 100
                        
                        comparison_df.index = next(iter(stock_data.values()))['historical_data']['Date']
                        fig = px.line(comparison_df, 
                                    title='Price Comparison (Normalized)',
                                    labels={'value': 'Normalized Price (%)', 'Date': 'Date'})
                        st.plotly_chart(fig, use_container_width=True)

            # 3. Fetch Financial Data
            if tickers_to_chart:
                with st.spinner("Fetching market data..."):
                    # Get current market data
                    market_data = get_financial_data(tickers_to_chart)
                    
                    if market_data:
                        # Display current market overview
                        st.subheader("📊 Market Overview")
                        cols = st.columns(len(market_data))
                        for idx, (ticker, data) in enumerate(market_data.items()):
                            with cols[idx]:
                                st.metric(
                                    label=ticker,
                                    value=f"${data['current_price']:.2f}",
                                    delta=f"{data['price_change']:.1f}%"
                                )
                        
                        # Create financial context for LLM
                        summaries = []
                        for ticker, data in market_data.items():
                            summary = (
                                f"{ticker}: Current=${data['current_price']:.2f}, "
                                f"Change={data['price_change']:.1f}%, "
                                f"52w-High=${data['high_52week']:.2f}"
                            )
                            summaries.append(summary)
                        financial_data_context = "Market Data:\n" + "\n".join(summaries)
                    else:
                        st.warning("Could not fetch current market data.")
                        financial_data_context = "No market data available."
            else:
                financial_data_context = "No specific tickers to analyze."

            # 4. Get and Display AI Analysis
            with st.spinner("Generating AI analysis..."):
                llm_response = get_llm_response(user_inputs, financial_data_context, news_context)
                
                st.subheader("💡 Your AI-Generated Plan")
                with st.container(border=True):
                    st.markdown(llm_response)

        # 6. Visualization (only for Investing goal)
        if tickers_to_chart:
            st.subheader("📊 Visualizing Your Potential")
            with st.container(border=True):
                hist_data = get_financial_data(tickers_to_chart, period="5y")
                
                if hist_data is None or hist_data.empty:
                    st.warning("Could not fetch historical data for visualization.")
                    return

                tab1, tab2 = st.tabs(["📈 Growth Simulation", "📊 Expected Returns"])

                with tab1:
                    # --- Chart 1: Animated Growth of $10,000 ---
                    st.markdown("##### Growth of a $10,000 Investment Over 5 Years")
                    st.markdown("This animated chart shows how a one-time $10,000 investment could have grown over the past five years based on historical performance.")

                    # Normalize data for growth comparison
                    df_normalized = pd.DataFrame()
                    for ticker in tickers_to_chart:
                        if (ticker, 'Adj Close') in hist_data.columns:
                            adj_close = hist_data[(ticker, 'Adj Close')].dropna()
                            if not adj_close.empty:
                                df_normalized[ticker] = (adj_close / adj_close.iloc[0]) * 10000
                    
                    if not df_normalized.empty:
                        df_normalized.reset_index(inplace=True)
                        df_melted = df_normalized.melt(id_vars=['Date'], var_name='Ticker', value_name='Portfolio Value')
                        
                        # Set a dynamic but sensible y-axis range
                        min_val, max_val = df_melted['Portfolio Value'].min(), df_melted['Portfolio Value'].max()
                        padding = (max_val - min_val) * 0.1
                        
                        fig_growth = px.line(
                            df_melted, x="Date", y="Portfolio Value", color='Ticker',
                            labels={"Portfolio Value": "Portfolio Value ($)", "Ticker": "Assets"},
                            animation_frame="Date", animation_group="Ticker",
                            range_y=[min_val - padding, max_val + padding],
                            template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Plotly
                        )
                        fig_growth.update_layout(legend_title_text='Assets')
                        st.plotly_chart(fig_growth, use_container_width=True)

                with tab2:
                    # --- Chart 2: Bar Chart of Expected Returns ---
                    st.markdown("##### Comparison of Expected Annual Returns")
                    st.markdown("This chart compares the average annualized return of each asset, calculated from its performance over the last year.")
                    returns_data = {ticker: calculate_expected_return(hist_data[ticker].dropna()) for ticker in tickers_to_chart if ticker in hist_data}
                    
                    if returns_data:
                        returns_df = pd.DataFrame(list(returns_data.items()), columns=["Ticker", "Return"]).sort_values("Return", ascending=False)
                        
                        fig_returns = px.bar(
                            returns_df, x="Ticker", y="Return", color="Return",
                            title="Annualized Return Expectation", template="plotly_dark",
                            labels={"Return": "Expected Annual Return (%)"},
                            color_continuous_scale=px.colors.sequential.Tealgrn,
                            text_auto='.2f'
                        )
                        fig_returns.update_traces(texttemplate='%{y:.2f}%', textposition='outside')
                        st.plotly_chart(fig_returns, use_container_width=True)

    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.error("Please check your API keys in the .env file, your internet connection, and try again.")


# --- Main Content Area ---
if analyze_button:
    # Validate inputs before proceeding
    if not user_inputs.get("risk"):
        st.error("Please select a risk tolerance level.")
    else:
        # Use a spinner to show that the app is working
        with st.spinner("Monexa AI is crafting your personalized plan..."):
            display_results(user_inputs)
else:
    # Initial welcome message
    st.info("Please fill out your profile in the sidebar to get started!")
    st.markdown("### How it works:")
    st.markdown("1. **Choose your investment:** Select from Stocks (Indian/US Markets), Mutual Funds, or Cryptocurrency")
    st.markdown("2. **Set your parameters:** Define your investment amount, time horizon, and risk tolerance")
    st.markdown("3. **Get Instant Insights:** Our AI analyzes market data and news to provide personalized recommendations with interactive visualizations")

# --- Disclaimer ---
st.markdown("---")
st.markdown("*Disclaimer: Monexa AI provides information and suggestions based on financial data and AI models. This is not financial advice. Please consult with a qualified financial professional before making any investment decisions.*")

