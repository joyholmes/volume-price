import pandas as pd
import numpy as np
from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, DateFormatter
from config import Config

class VolPriceRatioStrategy:
    def __init__(self):
        self.config = Config()
        self.positions = 0
        self.trades = []
        
    def calculate_indicators(self, data):
        # 计算成交量MA
        data['volume_ma'] = data['volume'].rolling(
            window=self.config.VOL_MA_PERIOD).mean()
            
        # 计算价格MA
        data['price_ma'] = data['close'].rolling(
            window=self.config.PRICE_MA_PERIOD).mean()
            
        # 计算量价比
        data['vol_price_ratio'] = (data['volume'] / data['volume_ma']) / \
                                 (data['close'] / data['price_ma'])
        
        # 计算量价比的MA
        data['vpr_ma'] = data['vol_price_ratio'].rolling(
            window=self.config.VOL_PRICE_RATIO_PERIOD).mean()
        
        return data
    
    def generate_signals(self, data):
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        
        # 生成买入信号
        signals.loc[data['vol_price_ratio'] < self.config.OVERSOLD_THRESHOLD, 'signal'] = 1
        
        # 生成卖出信号
        signals.loc[data['vol_price_ratio'] > self.config.OVERBOUGHT_THRESHOLD, 'signal'] = -1
        
        return signals
    
    def backtest(self, data):
        # 计算指标
        data = self.calculate_indicators(data)
        signals = self.generate_signals(data)
        
        # 回测
        dates = data.index.tolist()
        portfolio_values = []  # 组合总价值
        cash = self.config.INITIAL_CAPITAL  # 初始现金
        position = 0  # 持仓数量
        
        for i, date in enumerate(dates):
            close_price = data.loc[date, 'close']
            
            if signals.loc[date, 'signal'] == 1 and position < self.config.MAX_POSITIONS:
                # 买入
                buy_amount = cash * self.config.POSITION_SIZE  # 买入金额
                position = buy_amount / close_price  # 买入数量
                cash -= buy_amount  # 减少现金
                
                self.trades.append({
                    'date': date,
                    'type': 'BUY',
                    'price': close_price,
                    'amount': buy_amount,
                    'position': position,
                    'vol_price_ratio': data.loc[date, 'vol_price_ratio']
                })
                
            elif signals.loc[date, 'signal'] == -1 and position > 0:
                # 卖出
                sell_amount = position * close_price  # 卖出金额
                cash += sell_amount  # 增加现金
                
                self.trades.append({
                    'date': date,
                    'type': 'SELL',
                    'price': close_price,
                    'amount': sell_amount,
                    'position': position,
                    'vol_price_ratio': data.loc[date, 'vol_price_ratio']
                })
                position = 0  # 清空持仓
            
            # 计算当前组合总价值（现金 + 持仓市值）
            portfolio_value = cash + (position * close_price)
            portfolio_values.append(portfolio_value)
        
        return pd.Series(portfolio_values, index=dates)
    
    def calculate_benchmark_returns(self, data):
        """计算基准收益"""
        if len(data) == 0:
            print("警告: 数据集为空，无法计算基准收益")
            # 返回一个与portfolio_value相同长度的空Series
            return pd.Series(index=data.index)
        
        # 确保数据不为空后再计算
        first_close = data['close'].iloc[0] if not data.empty else 1.0
        benchmark_returns = (data['close'] / first_close) * self.config.INITIAL_CAPITAL
        return benchmark_returns

    def calculate_performance_metrics(self, portfolio_values, benchmark_values):
        """计算策略表现指标"""
        # 计算收益率
        strategy_returns = (portfolio_values.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
        benchmark_returns = (benchmark_values.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
        
        # 计算年化收益率
        days = (portfolio_values.index[-1] - portfolio_values.index[0]).days
        strategy_annual_returns = (1 + strategy_returns) ** (365/days) - 1
        benchmark_annual_returns = (1 + benchmark_returns) ** (365/days) - 1
        
        # 计算最大回撤
        strategy_max_drawdown = self.calculate_max_drawdown(portfolio_values)
        benchmark_max_drawdown = self.calculate_max_drawdown(benchmark_values)
        
        # 计算夏普比率
        strategy_daily_returns = portfolio_values.pct_change().dropna()
        benchmark_daily_returns = benchmark_values.pct_change().dropna()
        
        strategy_sharpe = np.sqrt(252) * (strategy_daily_returns.mean() / strategy_daily_returns.std())
        benchmark_sharpe = np.sqrt(252) * (benchmark_daily_returns.mean() / benchmark_daily_returns.std())
        
        return {
            'strategy_returns': strategy_returns,
            'benchmark_returns': benchmark_returns,
            'strategy_annual_returns': strategy_annual_returns,
            'benchmark_annual_returns': benchmark_annual_returns,
            'strategy_max_drawdown': strategy_max_drawdown,
            'benchmark_max_drawdown': benchmark_max_drawdown,
            'strategy_sharpe': strategy_sharpe,
            'benchmark_sharpe': benchmark_sharpe
        }

    def calculate_max_drawdown(self, values):
        """计算最大回撤"""
        cummax = values.cummax()
        drawdown = (values - cummax) / cummax
        return abs(drawdown.min())

    def save_results(self, data, portfolio_value):
        try:
            print("\n开始保存回测结果...")
            
            # 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"{self.config.OUTPUT_DIR}/{timestamp}"
            os.makedirs(output_dir, exist_ok=True)
            print(f"创建输出目录: {output_dir}")
            
            # 计算每笔交易的收益
            print("计算交易收益...")
            trades_with_profits = []
            for i in range(0, len(self.trades)-1, 2):  # 每两个交易为一组（买入和卖出）
                if i+1 < len(self.trades):
                    buy_trade = self.trades[i]
                    sell_trade = self.trades[i+1]
                    profit = (sell_trade['amount'] - buy_trade['amount'])
                    trades_with_profits.extend([
                        {**buy_trade, '收益': 0, '累计收益率': 0},
                        {**sell_trade, '收益': profit, '累计收益率': 0}
                    ])
            
            # 计算累计收益率
            total_profit = 0
            for trade in trades_with_profits:
                if trade['type'] == 'SELL':
                    total_profit += trade['收益']
                    trade['累计收益率'] = total_profit / self.config.INITIAL_CAPITAL * 100
            
            # 保存交易记录
            print("保存交易记录...")
            trades_df = pd.DataFrame(trades_with_profits)
            trades_df.to_csv(f"{output_dir}/交易记录.csv", encoding='utf-8-sig')
            print("交易记录已保存")
            
            # 计算基准收益
            benchmark_value = self.calculate_benchmark_returns(data)
            
            # 计算性能指标
            metrics = self.calculate_performance_metrics(portfolio_value, benchmark_value)
            
            # 保存参数配置和绩效分析
            print("保存策略参数...")
            with open(f"{output_dir}/策略参数.txt", 'w', encoding='utf-8') as f:
                f.write("量价比策略参数说明：\n")
                f.write("=" * 50 + "\n")
                f.write(f"初始资金: {self.config.INITIAL_CAPITAL:,.0f}元\n")
                f.write(f"交易品种: {self.config.SYMBOL_NAME} ({self.config.SYMBOL})\n")
                f.write(f"回测区间: {self.config.START_DATE} 至 {self.config.END_DATE}\n")
                f.write("\n策略参数：\n")
                f.write(f"量价比计算周期: {self.config.VOL_PRICE_RATIO_PERIOD}日\n")
                f.write(f"成交量均线周期: {self.config.VOL_MA_PERIOD}日\n")
                f.write(f"价格均线周期: {self.config.PRICE_MA_PERIOD}日\n")
                f.write(f"超买阈值: {self.config.OVERBOUGHT_THRESHOLD}\n")
                f.write(f"超卖阈值: {self.config.OVERSOLD_THRESHOLD}\n")
                f.write(f"最大持仓比例: {self.config.MAX_POSITIONS * 100}%\n")
                f.write(f"单次交易仓位: {self.config.POSITION_SIZE * 100}%\n")
                
                f.write("\n策略绩效分析：\n")
                f.write("=" * 50 + "\n")
                f.write(f"策略总收益率: {metrics['strategy_returns']*100:.2f}%\n")
                f.write(f"基准总收益率: {metrics['benchmark_returns']*100:.2f}%\n")
                f.write(f"策略年化收益率: {metrics['strategy_annual_returns']*100:.2f}%\n")
                f.write(f"基准年化收益率: {metrics['benchmark_annual_returns']*100:.2f}%\n")
                f.write(f"策略最大回撤: {metrics['strategy_max_drawdown']*100:.2f}%\n")
                f.write(f"基准最大回撤: {metrics['benchmark_max_drawdown']*100:.2f}%\n")
                f.write(f"策略夏普比率: {metrics['strategy_sharpe']:.2f}\n")
                f.write(f"基准夏普比率: {metrics['benchmark_sharpe']:.2f}\n")
                f.write(f"\n超额收益: {(metrics['strategy_returns']-metrics['benchmark_returns'])*100:.2f}%\n")
                f.write(f"交易次数: {len(self.trades)}笔\n")
                
                # 计算胜率
                profits = [t['收益'] for t in trades_with_profits if t['type'] == 'SELL']
                win_rate = len([p for p in profits if p > 0]) / len(profits) if profits else 0
                f.write(f"交易胜率: {win_rate*100:.2f}%\n")
            
            print("策略参数已保存")
            
            # 绘制并保存图表
            print("\n开始绘制图表...")
            self.plot_results(data, portfolio_value, output_dir)
            
        except Exception as e:
            print(f"保存结果时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def plot_results(self, data, portfolio_value, output_dir):
        try:
            print("开始生成图表...")
            print(f"数据长度: {len(data)}")
            print(f"投资组合值长度: {len(portfolio_value)}")
            print(f"交易记录数量: {len(self.trades)}")
            
            # 计算基准收益
            benchmark_value = self.calculate_benchmark_returns(data)
            
            # 使用默认样式而不是seaborn
            plt.style.use('default')
            
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # 对于macOS
            plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
            
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 15))
            
            # 价格图
            print("绘制价格图...")
            ax1.plot(data.index, data['close'], label='价格', color='blue')
            ax1.plot(data.index, data['price_ma'], 
                     label=f'{self.config.PRICE_MA_PERIOD}日均线', 
                     color='orange')
            
            # 标注买卖点
            print("标注买卖点...")
            for trade in self.trades:
                if trade['type'] == 'BUY':
                    ax1.scatter(trade['date'], trade['price'], 
                               color='red', marker='^', s=100,
                               label='买入点' if '买入点' not in ax1.get_legend_handles_labels()[1] else '')
                else:
                    ax1.scatter(trade['date'], trade['price'], 
                               color='green', marker='v', s=100,
                               label='卖出点' if '卖出点' not in ax1.get_legend_handles_labels()[1] else '')
            
            ax1.set_title(f'{self.config.SYMBOL_NAME}价格走势')
            ax1.legend(loc='best')
            ax1.grid(True)
            
            # 量价比图
            print("绘制量价比图...")
            ax2.plot(data.index, data['vol_price_ratio'], label='量价比', color='purple')
            ax2.axhline(y=self.config.OVERSOLD_THRESHOLD, color='g', 
                        linestyle='--', label='超卖线')
            ax2.axhline(y=self.config.OVERBOUGHT_THRESHOLD, color='r', 
                        linestyle='--', label='超买线')
            ax2.set_title('量价比指标')
            ax2.legend(loc='best')
            ax2.grid(True)
            
            # 资金曲线
            print("绘制资金曲线...")
            ax3.plot(data.index, portfolio_value, label='策略收益', color='red')
            ax3.plot(data.index, benchmark_value, label=f'{self.config.SYMBOL_NAME}基准', color='blue', alpha=0.7)
            ax3.set_title('策略收益与基准对比')
            ax3.legend(loc='best')
            ax3.grid(True)
            
            # 添加收益率标注
            strategy_returns = (portfolio_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            benchmark_returns = (benchmark_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            ax3.text(0.02, 0.98, 
                    f'策略收益率: {strategy_returns*100:.2f}%\n基准收益率: {benchmark_returns*100:.2f}%', 
                    transform=ax3.transAxes, 
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # 添加网格线和日期格式化
            print("添加网格线和日期格式化...")
            for ax in [ax1, ax2, ax3]:
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.xaxis.set_major_locator(YearLocator())
                ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
            
            plt.tight_layout()
            print(f"保存图表到: {output_dir}/回测结果.png")
            plt.savefig(f"{output_dir}/回测结果.png", dpi=300, bbox_inches='tight')
            plt.close()
            print("图表生成完成!")
            
        except Exception as e:
            print(f"生成图表时出错: {str(e)}")
            import traceback
            traceback.print_exc() 