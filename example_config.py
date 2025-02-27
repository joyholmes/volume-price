class Config:
    """配置文件样例
    请复制此文件为 config.py 并修改相应配置
    """
    
    # Tushare配置
    TUSHARE_TOKEN = "your_token_here"  # 请替换为您的token
    
    # 交易品种配置
    SYMBOL = "000300.SH"      # 交易标的代码，支持股票(.SZ/.SH)和指数(.SH)
    SYMBOL_NAME = "沪深300指数"  # 用于显示的标的名称
    
    # 回测时间配置
    START_DATE = "2020-01-01"  # 回测起始日期，建议至少覆盖2年以上
    END_DATE = "2023-12-31"    # 回测结束日期
    
    # 资金配置
    INITIAL_CAPITAL = 1000000  # 初始资金，建议100万以上以降低手续费影响
    
    # 量价比策略参数
    VOL_PRICE_RATIO_PERIOD = 20    # 量价比计算周期，推荐范围：10-30日
    VOL_MA_PERIOD = 20             # 成交量均线周期，推荐范围：10-30日
    PRICE_MA_PERIOD = 20           # 价格均线周期，推荐范围：10-30日
    
    # 信号阈值
    OVERSOLD_THRESHOLD = 0.8       # 超卖阈值，推荐范围：0.6-0.9
    OVERBOUGHT_THRESHOLD = 1.2     # 超买阈值，推荐范围：1.1-1.5
    
    # 仓位控制
    MAX_POSITIONS = 1              # 最大持仓数量，1表示最多100%仓位
    POSITION_SIZE = 1.0            # 每次交易仓位比例，1.0表示满仓，推荐范围：0.3-1.0
    
    # 输出配置
    OUTPUT_DIR = "backtest_results"  # 回测结果输出目录

    @classmethod
    def validate(cls):
        """验证配置参数的有效性"""
        assert cls.TUSHARE_TOKEN != "your_token_here", "请设置正确的Tushare Token"
        assert 0 < cls.INITIAL_CAPITAL, "初始资金必须大于0"
        assert 5 <= cls.VOL_PRICE_RATIO_PERIOD <= 60, "量价比周期建议在5-60日之间"
        assert 5 <= cls.VOL_MA_PERIOD <= 60, "成交量均线周期建议在5-60日之间"
        assert 5 <= cls.PRICE_MA_PERIOD <= 60, "价格均线周期建议在5-60日之间"
        assert 0 < cls.OVERSOLD_THRESHOLD < 1, "超卖阈值必须在0-1之间"
        assert cls.OVERBOUGHT_THRESHOLD > 1, "超买阈值必须大于1"
        assert 0 < cls.MAX_POSITIONS <= 1, "最大持仓必须在0-1之间"
        assert 0 < cls.POSITION_SIZE <= 1, "交易仓位必须在0-1之间" 