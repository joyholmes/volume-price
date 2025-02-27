import pandas as pd
import tushare as ts

def get_stock_data(symbol, config):
    """根据配置获取股票数据"""
    print(f"获取 {symbol} 数据...")
    
    # 初始化tushare
    ts.set_token(config.TUSHARE_TOKEN)
    pro = ts.pro_api()
    
    try:
        # 获取数据
        if symbol.endswith('.SH') or symbol.endswith('.SZ'):
            # 尝试获取ETF数据
            if symbol.startswith('51') or symbol.startswith('15'):
                print("尝试获取ETF数据...")
                df = pro.fund_daily(
                    ts_code=symbol,
                    start_date=config.START_DATE.replace('-', ''),
                    end_date=config.END_DATE.replace('-', '')
                )
            else:
                # 尝试获取指数数据
                print("尝试获取指数数据...")
                df = pro.index_daily(
                    ts_code=symbol,
                    start_date=config.START_DATE.replace('-', ''),
                    end_date=config.END_DATE.replace('-', '')
                )
        else:  # 股票数据
            print("尝试获取股票数据...")
            df = pro.daily(
                ts_code=symbol,
                start_date=config.START_DATE.replace('-', ''),
                end_date=config.END_DATE.replace('-', '')
            )
        
        # 检查数据是否为空
        if df.empty:
            print(f"警告: 未获取到 {symbol} 的数据，请检查代码和日期范围")
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
        return pd.DataFrame(columns=['close', 'volume']) 