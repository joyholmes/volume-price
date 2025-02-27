class TrendMomentumConfig:
    """趋势动量策略配置"""
    
    # Tushare配置
    TUSHARE_TOKEN = "your_token_here"
    
    # 交易品种配置
    SYMBOL = "512880.SH"        # 证券ETF
    SYMBOL_NAME = "证券ETF"
    INDEX_SYMBOL = "399975.SZ"  # 证券公司指数
    
    # 回测时间配置
    START_DATE = "2023-01-01"
    END_DATE = "2024-12-31"
    
    # 资金配置
    INITIAL_CAPITAL = 1000000   # 初始资金100万
    
    # 趋势参数
    FAST_MA = 5                 # 快速均线周期
    MID_MA = 20                 # 中期均线周期
    SLOW_MA = 60               # 慢速均线周期
    
    # 动量参数
    ROC_PERIOD = 5             # 变化率周期
    RSI_PERIOD = 14            # RSI周期
    MACD_FAST = 12            # MACD快线
    MACD_SLOW = 26            # MACD慢线
    MACD_SIGNAL = 9           # MACD信号线
    
    # 波动率参数
    ATR_PERIOD = 14           # ATR周期
    VOLATILITY_MA = 20        # 波动率均线周期
    
    # 仓位控制
    MAX_POSITIONS = 1.0       # 最大仓位
    INITIAL_POSITION = 0.3    # 初始建仓仓位
    POSITION_STEP = 0.2       # 加仓步长
    
    # 止损参数
    FIXED_STOP_LOSS = 0.05    # 固定止损比例
    TRAILING_STOP = 0.08      # 追踪止损比例
    
    # 信号阈值
    TREND_THRESHOLD = 0.02    # 趋势确认阈值
    RSI_OVERSOLD = 30        # RSI超卖阈值
    RSI_OVERBOUGHT = 70      # RSI超买阈值
    
    # 输出配置
    OUTPUT_DIR = "backtest_results" 