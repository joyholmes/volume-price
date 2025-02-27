import pandas as pd
import numpy as np
from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, DateFormatter
import seaborn as sns
from config import TrendMomentumConfig

class TrendMomentumStrategy:
    def __init__(self):
        self.config = TrendMomentumConfig()
        self.positions = 0
        self.trades = []
        self.current_stop_loss = 0
        
    def calculate_indicators(self, data):
        """计算技术指标"""
        # 计算移动平均线
        data['ma_fast'] = data['close'].rolling(window=self.config.FAST_MA).mean()
        data['ma_mid'] = data['close'].rolling(window=self.config.MID_MA).mean()
        data['ma_slow'] = data['close'].rolling(window=self.config.SLOW_MA).mean()
        
        # 计算ROC
        data['roc'] = data['close'].pct_change(periods=self.config.ROC_PERIOD)
        
        # 计算RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config.RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.RSI_PERIOD).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # 计算MACD
        exp1 = data['close'].ewm(span=self.config.MACD_FAST).mean()
        exp2 = data['close'].ewm(span=self.config.MACD_SLOW).mean()
        data['macd'] = exp1 - exp2
        data['signal'] = data['macd'].ewm(span=self.config.MACD_SIGNAL).mean()
        data['macd_hist'] = data['macd'] - data['signal']
        
        # 计算ATR
        data['tr'] = np.maximum(
            data['high'] - data['low'],
            np.maximum(
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            )
        )
        data['atr'] = data['tr'].rolling(window=self.config.ATR_PERIOD).mean()
        
        return data
        
    def generate_signals(self, data):
        """生成交易信号"""
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        
        # 趋势确认
        trend_up = (data['ma_fast'] > data['ma_mid']) & \
                  (data['ma_mid'] > data['ma_slow']) & \
                  (data['close'] > data['ma_mid'])
        
        trend_down = (data['ma_fast'] < data['ma_mid']) & \
                    (data['ma_mid'] < data['ma_slow']) & \
                    (data['close'] < data['ma_mid'])
        
        # 动量确认
        momentum_strong = (data['roc'] > self.config.TREND_THRESHOLD) & \
                        (data['rsi'] > self.config.RSI_OVERSOLD) & \
                        (data['macd_hist'] > 0)
        
        momentum_weak = (data['roc'] < -self.config.TREND_THRESHOLD) & \
                       (data['rsi'] < self.config.RSI_OVERBOUGHT) & \
                       (data['macd_hist'] < 0)
        
        # 波动率过滤
        volatility_suitable = data['atr'] < data['atr'].rolling(
            window=self.config.VOLATILITY_MA).mean()
        
        # 生成信号
        buy_condition = trend_up & momentum_strong & volatility_suitable
        sell_condition = trend_down | momentum_weak
        
        signals.loc[buy_condition, 'signal'] = 1
        signals.loc[sell_condition, 'signal'] = -1
        
        return signals
        
    def calculate_position_size(self, data, current_price, current_position):
        """计算仓位大小"""
        if current_position == 0:
            return self.config.INITIAL_POSITION
        elif current_position < self.config.MAX_POSITIONS:
            # 检查是否满足加仓条件
            if (data['roc'].iloc[-1] > self.config.TREND_THRESHOLD and
                data['rsi'].iloc[-1] < self.config.RSI_OVERBOUGHT):
                return min(
                    self.config.MAX_POSITIONS - current_position,
                    self.config.POSITION_STEP
                )
        return 0
        
    def update_stop_loss(self, current_price, position_price):
        """更新止损价格"""
        fixed_stop = position_price * (1 - self.config.FIXED_STOP_LOSS)
        trailing_stop = current_price * (1 - self.config.TRAILING_STOP)
        self.current_stop_loss = max(fixed_stop, trailing_stop)
        
    def check_stop_loss(self, current_price):
        """检查是否触发止损"""
        return current_price < self.current_stop_loss if self.current_stop_loss > 0 else False
        
    def backtest(self, data):
        """执行回测"""
        print("开始回测...")
        
        # 计算技术指标
        data = self.calculate_indicators(data)
        signals = self.generate_signals(data)
        
        # 回测变量初始化
        dates = data.index.tolist()
        portfolio_values = []  # 组合总价值
        cash = self.config.INITIAL_CAPITAL  # 初始现金
        position = 0  # 持仓数量
        position_price = 0  # 持仓成本
        
        for i, date in enumerate(dates):
            current_price = data.loc[date, 'close']
            
            # 检查止损
            if position > 0 and self.check_stop_loss(current_price):
                # 触发止损，清空仓位
                sell_amount = position * current_price
                cash += sell_amount
                
                self.trades.append({
                    'date': date,
                    'type': 'STOP_LOSS',
                    'price': current_price,
                    'amount': sell_amount,
                    'position': position,
                    'indicators': {
                        'roc': data.loc[date, 'roc'],
                        'rsi': data.loc[date, 'rsi'],
                        'macd_hist': data.loc[date, 'macd_hist']
                    }
                })
                
                position = 0
                self.current_stop_loss = 0
            
            # 处理交易信号
            if signals.loc[date, 'signal'] == 1 and position < self.config.MAX_POSITIONS:
                # 计算买入仓位
                new_position = self.calculate_position_size(data.loc[:date], current_price, position)
                if new_position > 0:
                    buy_amount = cash * new_position
                    new_shares = buy_amount / current_price
                    position += new_shares
                    cash -= buy_amount
                    
                    # 更新持仓成本和止损价格
                    position_price = current_price
                    self.update_stop_loss(current_price, position_price)
                    
                    self.trades.append({
                        'date': date,
                        'type': 'BUY',
                        'price': current_price,
                        'amount': buy_amount,
                        'position': position,
                        'indicators': {
                            'roc': data.loc[date, 'roc'],
                            'rsi': data.loc[date, 'rsi'],
                            'macd_hist': data.loc[date, 'macd_hist']
                        }
                    })
                    
            elif signals.loc[date, 'signal'] == -1 and position > 0:
                # 卖出
                sell_amount = position * current_price
                cash += sell_amount
                
                self.trades.append({
                    'date': date,
                    'type': 'SELL',
                    'price': current_price,
                    'amount': sell_amount,
                    'position': position,
                    'indicators': {
                        'roc': data.loc[date, 'roc'],
                        'rsi': data.loc[date, 'rsi'],
                        'macd_hist': data.loc[date, 'macd_hist']
                    }
                })
                
                position = 0
                self.current_stop_loss = 0
            
            # 更新止损价格
            if position > 0:
                self.update_stop_loss(current_price, position_price)
            
            # 计算当前组合总价值
            portfolio_value = cash + (position * current_price)
            portfolio_values.append(portfolio_value)
        
        print(f"回测完成，共进行 {len(self.trades)} 笔交易")
        return pd.Series(portfolio_values, index=dates)
        
    def save_results(self, data, portfolio_value):
        """保存回测结果"""
        try:
            print("\n开始保存回测结果...")
            
            # 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"trading_strategies/trend_momentum/backtest_results/{timestamp}"  # 修改输出路径
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存交易记录
            trades_df = pd.DataFrame(self.trades)
            if not trades_df.empty:
                trades_df['returns'] = trades_df.apply(
                    lambda x: x['amount'] / self.config.INITIAL_CAPITAL - 1 
                    if x['type'] == 'SELL' or x['type'] == 'STOP_LOSS'
                    else 0, axis=1
                )
                trades_df.to_csv(f"{output_dir}/交易记录.csv", index=False)
            
            # 计算策略绩效指标
            benchmark_value = data['close'] / data['close'].iloc[0] * self.config.INITIAL_CAPITAL
            
            # 绘制回测结果图表
            self.plot_results(data, portfolio_value, benchmark_value, output_dir)
            
            # 保存策略参数和绩效指标
            with open(f"{output_dir}/策略参数.txt", "w", encoding='utf-8') as f:
                f.write("趋势动量策略参数说明：\n")
                f.write("="*50 + "\n")
                f.write(f"初始资金: {self.config.INITIAL_CAPITAL:,}元\n")
                f.write(f"交易品种: {self.config.SYMBOL_NAME} ({self.config.SYMBOL})\n")
                f.write(f"回测区间: {data.index[0].strftime('%Y-%m-%d')} 至 {data.index[-1].strftime('%Y-%m-%d')}\n\n")
                
                f.write("策略参数：\n")
                f.write(f"快速均线周期: {self.config.FAST_MA}日\n")
                f.write(f"中均线周期: {self.config.MID_MA}日\n")
                f.write(f"慢均线周期: {self.config.SLOW_MA}日\n")
                f.write(f"ROC周期: {self.config.ROC_PERIOD}日\n")
                f.write(f"RSI周期: {self.config.RSI_PERIOD}日\n")
                f.write(f"MACD快速线周期: {self.config.MACD_FAST}日\n")
                f.write(f"MACDSlow线周期: {self.config.MACD_SLOW}日\n")
                f.write(f"MACDSignal线周期: {self.config.MACD_SIGNAL}日\n")
                f.write(f"ATR周期: {self.config.ATR_PERIOD}日\n")
                f.write(f"波动率均线周期: {self.config.VOLATILITY_MA}日\n")
                f.write(f"趋势阈值: {self.config.TREND_THRESHOLD}\n")
                f.write(f"RSI超卖阈值: {self.config.RSI_OVERSOLD}\n")
                f.write(f"RSI超买阈值: {self.config.RSI_OVERBOUGHT}\n")
                f.write(f"最大持仓比例: {self.config.MAX_POSITIONS*100}%\n")
                f.write(f"单次交易仓位: {self.config.POSITION_STEP*100}%\n\n")
                
                f.write("策略绩效分析：\n")
                f.write("="*50 + "\n")
                f.write(f"策略总收益率: {(portfolio_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL*100:.2f}%\n")
                f.write(f"基准总收益率: {(benchmark_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL*100:.2f}%\n")
                f.write(f"策略最大回撤: {(portfolio_value - portfolio_value.cummax()) / portfolio_value.cummax()).min()*100:.2f}%\n")
                f.write(f"基准最大回撤: {(benchmark_value - benchmark_value.cummax()) / benchmark_value.cummax()).min()*100:.2f}%\n")
                f.write(f"策略夏普比率: {((portfolio_value.pct_change().dropna().mean() * np.sqrt(252)) / portfolio_value.pct_change().dropna().std()) * 100):.2f}%\n")
                f.write(f"基准夏普比率: {((benchmark_value.pct_change().dropna().mean() * np.sqrt(252)) / benchmark_value.pct_change().dropna().std()) * 100):.2f}%\n")
                f.write(f"超额收益: {(portfolio_value.iloc[-1] - benchmark_value.iloc[-1]) / self.config.INITIAL_CAPITAL * 100:.2f}%\n")
                f.write(f"交易次数: {len(trades_df)}笔\n")
            
            print(f"回测结果已保存至: {output_dir}")
            
        except Exception as e:
            print(f"保存结果时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def plot_results(self, data, portfolio_value, benchmark_value, output_dir):
        """绘制回测结果图表"""
        try:
            sns.set_style("whitegrid")  # 使用 seaborn 的样式设置
            fig = plt.figure(figsize=(15, 20))
            
            # 1. 价格和均线
            ax1 = plt.subplot(411)
            ax1.plot(data.index, data['close'], label='价格', color='blue')
            ax1.plot(data.index, data['ma_fast'], label=f'{self.config.FAST_MA}日均线', color='red')
            ax1.plot(data.index, data['ma_mid'], label=f'{self.config.MID_MA}日均线', color='orange')
            ax1.plot(data.index, data['ma_slow'], label=f'{self.config.SLOW_MA}日均线', color='green')
            
            # 标注交易点
            for trade in self.trades:
                if trade['type'] == 'BUY':
                    ax1.scatter(trade['date'], trade['price'], color='red', marker='^', s=100)
                elif trade['type'] == 'SELL':
                    ax1.scatter(trade['date'], trade['price'], color='green', marker='v', s=100)
                elif trade['type'] == 'STOP_LOSS':
                    ax1.scatter(trade['date'], trade['price'], color='black', marker='x', s=100)
            
            ax1.set_title('价格走势与交易信号')
            ax1.legend(loc='best')
            ax1.grid(True)
            
            # 2. RSI
            ax2 = plt.subplot(412)
            ax2.plot(data.index, data['rsi'], label='RSI', color='purple')
            ax2.axhline(y=self.config.RSI_OVERSOLD, color='g', linestyle='--')
            ax2.axhline(y=self.config.RSI_OVERBOUGHT, color='r', linestyle='--')
            ax2.set_title('RSI指标')
            ax2.legend(loc='best')
            ax2.grid(True)
            
            # 3. MACD
            ax3 = plt.subplot(413)
            ax3.plot(data.index, data['macd'], label='MACD', color='blue')
            ax3.plot(data.index, data['signal'], label='Signal', color='orange')
            ax3.bar(data.index, data['macd_hist'], label='Histogram', color='gray', alpha=0.3)
            ax3.set_title('MACD指标')
            ax3.legend(loc='best')
            ax3.grid(True)
            
            # 4. 收益对比
            ax4 = plt.subplot(414)
            ax4.plot(data.index, portfolio_value, label='策略收益', color='red')
            ax4.plot(data.index, benchmark_value, label='基准收益', color='blue')
            ax4.set_title('策略收益与基准对比')
            ax4.legend(loc='best')
            ax4.grid(True)
            
            # 添加收益率标注
            strategy_returns = (portfolio_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            benchmark_returns = (benchmark_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            ax4.text(0.02, 0.98, 
                    f'策略收益率: {strategy_returns*100:.2f}%\n基准收益率: {benchmark_returns*100:.2f}%', 
                    transform=ax4.transAxes, 
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # 添加日期格式化
            for ax in [ax1, ax2, ax3, ax4]:
                ax.xaxis.set_major_locator(YearLocator())
                ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
                plt.setp(ax.get_xticklabels(), rotation=45)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/回测结果.png", dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"绘制图表时出错: {str(e)}")
            import traceback
            traceback.print_exc() 