import sys
import os
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import get_stock_data
from config import TrendMomentumConfig
from strategy import TrendMomentumStrategy

def get_market_data(config):
    """获取主交易品种和板块指数数据"""
    # 获取ETF数据
    etf_data = get_stock_data(config.SYMBOL, config)
    
    # 获取板块指数数据
    index_data = get_stock_data(config.INDEX_SYMBOL, config)
    
    # 合并数据
    data = pd.DataFrame(index=etf_data.index)
    data['close'] = etf_data['close']
    data['volume'] = etf_data['volume']
    data['index_close'] = index_data['close'].reindex(etf_data.index)
    data['index_volume'] = index_data['volume'].reindex(etf_data.index)
    
    return data

def main():
    try:
        print("开始趋势动量策略回测...")
        config = TrendMomentumConfig()
        
        # 获取数据
        data = get_market_data(config)
        
        # 创建策略实例
        strategy = TrendMomentumStrategy()
        
        # 运行回测
        portfolio_value = strategy.backtest(data)
        
        # 保存结果
        strategy.save_results(data, portfolio_value)
        
    except Exception as e:
        print(f"运行出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 