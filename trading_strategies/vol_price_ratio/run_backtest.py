import sys
import os
import pandas as pd  # 添加 pandas 导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.utils import get_stock_data
from config import Config
from strategy import VolPriceRatioStrategy

def main():
    try:
        print("开始量价比策略回测...")
        config = Config()
        
        # 获取数据
        data = get_stock_data(config.SYMBOL, config)
        
        # 创建策略实例
        strategy = VolPriceRatioStrategy()
        
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