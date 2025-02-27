import pandas as pd
import numpy as np
from datetime import datetime
import os
import matplotlib.pyplot as plt
import seaborn as sns
from config import Config

class VolPriceRatioStrategy:
    def __init__(self):
        self.config = Config()
        self.positions = 0
        self.trades = []
        
    def calculate_indicators(self, data):
        """计算技术指标"""
        # 计算量价比
        data['vol_price_ratio'] = data['volume'] / data['close']
        
        # 计算移动平均
        data['vol_ma'] = data['volume'].rolling(window=self.config.VOL_MA_PERIOD).mean()
        data['price_ma'] = data['close'].rolling(window=self.config.PRICE_MA_PERIOD).mean()
        
        return data
        
    def generate_signals(self, data):
        """生成交易信号"""
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        
        # 计算相对量价比
        relative_ratio = data['vol_price_ratio'] / data['vol_price_ratio'].rolling(
            window=self.config.VOL_PRICE_RATIO_PERIOD).mean()
        
        # 生成信号
        signals.loc[relative_ratio < self.config.OVERSOLD_THRESHOLD, 'signal'] = 1
        signals.loc[relative_ratio > self.config.OVERBOUGHT_THRESHOLD, 'signal'] = -1
        
        return signals
        
    def backtest(self, data):
        """执行回测"""
        print("开始回测...")
        
        # 计算指标
        data = self.calculate_indicators(data)
        signals = self.generate_signals(data)
        
        # 回测变量初始化
        portfolio_values = []  # 组合总价值
        cash = self.config.INITIAL_CAPITAL  # 初始现金
        position = 0  # 持仓数量
        
        for i, date in enumerate(data.index):
            current_price = data.loc[date, 'close']
            signal = signals.loc[date, 'signal']
            
            # 处理买入信号
            if signal == 1 and position == 0:
                # 计算购买数量
                buy_amount = cash * self.config.POSITION_SIZE
                shares = buy_amount / current_price
                position = shares
                cash -= buy_amount
                
                self.trades.append({
                    'date': date,
                    'type': 'BUY',
                    'price': current_price,
                    'amount': buy_amount,
                    'position': position
                })
                
            # 处理卖出信号
            elif signal == -1 and position > 0:
                # 卖出全部持仓
                sell_amount = position * current_price
                cash += sell_amount
                
                self.trades.append({
                    'date': date,
                    'type': 'SELL',
                    'price': current_price,
                    'amount': sell_amount,
                    'position': position
                })
                
                position = 0
            
            # 计算当前组合总价值
            portfolio_value = cash + (position * current_price)
            portfolio_values.append(portfolio_value)
        
        print(f"回测完成，共进行 {len(self.trades)} 笔交易")
        return pd.Series(portfolio_values, index=data.index)
        
    def save_results(self, data, portfolio_value):
        """保存回测结果"""
        try:
            print("\n开始保存回测结果...")
            
            # 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"trading_strategies/vol_price_ratio/backtest_results/{timestamp}"  # 修改输出路径
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存交易记录
            trades_df = pd.DataFrame(self.trades)
            if not trades_df.empty:
                trades_df['returns'] = trades_df.apply(
                    lambda x: x['amount'] / self.config.INITIAL_CAPITAL - 1 
                    if x['type'] == 'SELL'
                    else 0, axis=1
                )
                trades_df.to_csv(f"{output_dir}/交易记录.csv", index=False)
            
            # 计算策略绩效指标
            strategy_returns = (portfolio_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            benchmark_returns = (data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]
            
            # 计算年化收益率
            days = (data.index[-1] - data.index[0]).days
            strategy_annual_returns = (1 + strategy_returns) ** (365/days) - 1
            benchmark_annual_returns = (1 + benchmark_returns) ** (365/days) - 1
            
            # 计算最大回撤
            strategy_drawdown = (portfolio_value - portfolio_value.cummax()) / portfolio_value.cummax()
            benchmark_drawdown = (data['close'] - data['close'].cummax()) / data['close'].cummax()
            
            # 计算夏普比率
            daily_returns = portfolio_value.pct_change().dropna()
            sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()
            
            benchmark_daily_returns = data['close'].pct_change().dropna()
            benchmark_sharpe = np.sqrt(252) * benchmark_daily_returns.mean() / benchmark_daily_returns.std()
            
            # 计算胜率
            winning_trades = trades_df[trades_df['returns'] > 0]
            win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            
            # 保存策略参数和绩效指标
            with open(f"{output_dir}/策略参数.txt", "w", encoding='utf-8') as f:
                f.write("量价比策略参数说明：\n")
                f.write("="*50 + "\n")
                f.write(f"初始资金: {self.config.INITIAL_CAPITAL:,}元\n")
                f.write(f"交易品种: {self.config.SYMBOL_NAME} ({self.config.SYMBOL})\n")
                f.write(f"回测区间: {data.index[0].strftime('%Y-%m-%d')} 至 {data.index[-1].strftime('%Y-%m-%d')}\n\n")
                
                f.write("策略参数：\n")
                f.write(f"量价比计算周期: {self.config.VOL_PRICE_RATIO_PERIOD}日\n")
                f.write(f"成交量均线周期: {self.config.VOL_MA_PERIOD}日\n")
                f.write(f"价格均线周期: {self.config.PRICE_MA_PERIOD}日\n")
                f.write(f"超买阈值: {self.config.OVERBOUGHT_THRESHOLD}\n")
                f.write(f"超卖阈值: {self.config.OVERSOLD_THRESHOLD}\n")
                f.write(f"最大持仓比例: {self.config.MAX_POSITIONS*100}%\n")
                f.write(f"单次交易仓位: {self.config.POSITION_SIZE*100}%\n\n")
                
                f.write("策略绩效分析：\n")
                f.write("="*50 + "\n")
                f.write(f"策略总收益率: {strategy_returns*100:.2f}%\n")
                f.write(f"基准总收益率: {benchmark_returns*100:.2f}%\n")
                f.write(f"策略年化收益率: {strategy_annual_returns*100:.2f}%\n")
                f.write(f"基准年化收益率: {benchmark_annual_returns*100:.2f}%\n")
                f.write(f"策略最大回撤: {abs(strategy_drawdown.min())*100:.2f}%\n")
                f.write(f"基准最大回撤: {abs(benchmark_drawdown.min())*100:.2f}%\n")
                f.write(f"策略夏普比率: {sharpe_ratio:.2f}\n")
                f.write(f"基准夏普比率: {benchmark_sharpe:.2f}\n\n")
                
                f.write(f"超额收益: {(strategy_returns-benchmark_returns)*100:.2f}%\n")
                f.write(f"交易次数: {len(trades_df)}笔\n")
                f.write(f"交易胜率: {win_rate:.2f}%\n")
            
            # 绘制回测结果图表
            self.plot_results(data, portfolio_value, output_dir)
            
            print(f"回测结果已保存至: {output_dir}")
            
        except Exception as e:
            print(f"保存结果时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def plot_results(self, data, portfolio_value, output_dir):
        """绘制回测结果图表"""
        try:
            sns.set_style("whitegrid")
            fig = plt.figure(figsize=(15, 10))
            
            # 1. 价格和交易点
            ax1 = plt.subplot(211)
            ax1.plot(data.index, data['close'], label='价格', color='blue')
            ax1.plot(data.index, data['price_ma'], label=f'{self.config.PRICE_MA_PERIOD}日均线', 
                    color='orange', alpha=0.7)
            
            # 标注交易点
            for trade in self.trades:
                if trade['type'] == 'BUY':
                    ax1.scatter(trade['date'], trade['price'], color='red', marker='^', s=100)
                else:  # SELL
                    ax1.scatter(trade['date'], trade['price'], color='green', marker='v', s=100)
            
            ax1.set_title('价格走势与交易信号')
            ax1.legend(loc='best')
            ax1.grid(True)
            
            # 2. 收益曲线
            ax2 = plt.subplot(212)
            ax2.plot(data.index, portfolio_value, label='策略收益', color='red')
            ax2.plot(data.index, data['close'] / data['close'][0] * self.config.INITIAL_CAPITAL, 
                    label='基准收益', color='blue')
            
            # 添加收益率标注
            strategy_returns = (portfolio_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            benchmark_returns = (data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]
            
            ax2.text(0.02, 0.98, 
                    f'策略收益率: {strategy_returns*100:.2f}%\n基准收益率: {benchmark_returns*100:.2f}%', 
                    transform=ax2.transAxes, 
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            ax2.set_title('收益对比')
            ax2.legend(loc='best')
            ax2.grid(True)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/回测结果.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制图表时出错: {str(e)}")
            import traceback
            traceback.print_exc() 