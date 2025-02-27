class Config:
    # Tushare配置
    TUSHARE_TOKEN = "your_token_here"
    
    # 交易品种配置
    SYMBOL = "512880.SH"        # 证券ETF
    SYMBOL_NAME = "证券ETF"
    
    # 回测时间配置
    START_DATE = "2023-01-01"
    END_DATE = "2024-12-31"
    
    # 资金配置
    INITIAL_CAPITAL = 1000000   # 初始资金100万
    
    # 量价比策略参数
    VOL_PRICE_RATIO_PERIOD = 3     # 进一步缩短，提高灵敏度
    VOL_MA_PERIOD = 3              # 与量价比周期保持一致
    PRICE_MA_PERIOD = 8            # 短期价格趋势
    
    # 信号阈值
    OVERSOLD_THRESHOLD = 0.92      # 略微放宽买入条件
    OVERBOUGHT_THRESHOLD = 1.5     # 大幅提高卖出阈值，避免过早卖出
    
    # 仓位控制
    POSITION_SIZE = 0.5            # 首次建仓比例
    MAX_POSITIONS = 1              # 最大仓位保持不变
    
    # 输出配置
    OUTPUT_DIR = "backtest_results" 