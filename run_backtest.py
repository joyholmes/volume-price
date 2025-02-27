import pandas as pd
import tushare as ts
from vol_price_ratio_strategy import VolPriceRatioStrategy
from config import Config
import os

def get_stock_data(config):
    """根据配置获取股票数据"""
    print(f"获取 {config.SYMBOL_NAME} 数据...")
    
    # 初始化tushare
    ts.set_token(config.TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    try:
        # 获取数据
        if config.SYMBOL.endswith('.SH') or config.SYMBOL.endswith('.SZ'):
            # 尝试获取ETF数据
            if config.SYMBOL.startswith('51') or config.SYMBOL.startswith('15'):
                print("尝试获取ETF数据...")
                df = pro.fund_daily(
                    ts_code=config.SYMBOL,
                    start_date=config.START_DATE.replace('-', ''),
                    end_date=config.END_DATE.replace('-', '')
                )
            else:
                # 尝试获取指数数据
                print("尝试获取指数数据...")
                df = pro.index_daily(
                    ts_code=config.SYMBOL,
                    start_date=config.START_DATE.replace('-', ''),
                    end_date=config.END_DATE.replace('-', '')
                )
        else:  # 股票数据
            print("尝试获取股票数据...")
            df = pro.daily(
                ts_code=config.SYMBOL,
                start_date=config.START_DATE.replace('-', ''),
                end_date=config.END_DATE.replace('-', '')
            )
        
        # 检查数据是否为空
        if df.empty:
            print(f"警告: 未获取到 {config.SYMBOL} 的数据，请检查代码和日期范围")
            return pd.DataFrame(columns=['close', 'volume'])
        
        # 重命名列并调整日期格式
        df = df.rename(columns={
            'trade_date': 'date',
            'close': 'close',
            'vol': 'volume'
        })
        
        # 设置日期索引
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.sort_index()  # 确保按日期正序排列
        
        print(f"获取到 {len(df)} 条数据")
        return df[['close', 'volume']]  # 只保留需要的列
        
    except Exception as e:
        print(f"获取数据时出错: {str(e)}")
        print("尝试使用备用方法获取数据...")
        
        # 备用方法：使用普通API获取数据
        try:
            df = ts.get_k_data(
                code=config.SYMBOL.split('.')[0],
                start=config.START_DATE,
                end=config.END_DATE
            )
            
            if df is not None and not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df = df.sort_index()
                print(f"使用备用方法获取到 {len(df)} 条数据")
                return df[['close', 'volume']]
            else:
                print("备用方法也未获取到数据")
                return pd.DataFrame(columns=['close', 'volume'])
                
        except Exception as e2:
            print(f"备用方法获取数据也失败: {str(e2)}")
            return pd.DataFrame(columns=['close', 'volume'])

def main():
    try:
        print("开始回测...")
        
        # 确保输出目录存在
        if not os.path.exists("backtest_results"):
            os.makedirs("backtest_results")
            print("创建backtest_results目录")
        
        # 加载配置
        config = Config()
        print(f"加载配置完成，回测区间: {config.START_DATE} 至 {config.END_DATE}")
        
        # 获取数据
        data = get_stock_data(config)  # 使用新的数据获取函数
        
        # 创建策略实例
        strategy = VolPriceRatioStrategy()
        
        # 运行回测
        print("开始策略回测...")
        portfolio_value = strategy.backtest(data)
        print("回测完成")
        
        # 保存结果
        print("保存回测结果...")
        strategy.save_results(data, portfolio_value)
        print("回测结果保存完成")
        
    except Exception as e:
        print(f"运行出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 