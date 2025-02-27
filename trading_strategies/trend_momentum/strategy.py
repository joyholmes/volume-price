import pandas as pd
import numpy as np
from datetime import datetime
import os
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, DateFormatter
import seaborn as sns
from config import TrendMomentumConfig
from matplotlib.font_manager import FontProperties

class TrendMomentumStrategy:
    def __init__(self):
        self.config = TrendMomentumConfig()
        self.positions = 0
        self.trades = []
        self.current_stop_loss = 0
        self.data = None
        
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
        
        # 使用收盘价变化计算ATR
        data['tr'] = abs(data['close'] - data['close'].shift(1))
        data['atr'] = data['tr'].rolling(window=self.config.ATR_PERIOD).mean()
        data['atr_ma'] = data['atr'].rolling(window=self.config.ATR_MA).mean()
        
        # 添加均线斜率
        data['ma_fast_slope'] = data['ma_fast'].diff(self.config.TREND_CONFIRM_DAYS)
        data['ma_mid_slope'] = data['ma_mid'].diff(self.config.TREND_CONFIRM_DAYS)
        data['ma_slow_slope'] = data['ma_slow'].diff(self.config.TREND_CONFIRM_DAYS)
        
        # 添加成交量分析
        data['volume_ma'] = data['volume'].rolling(window=self.config.VOLUME_MA).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        return data
        
    def generate_signals(self, data):
        """生成交易信号"""
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        
        # 1. 添加短期趋势判断
        short_trend = (
            (data['close'].pct_change(3) > 0) &  # 3日涨幅为正
            (data['volume'].pct_change(3) > 0)    # 3日成交量放大
        )
        
        # 2. 添加突破判断
        breakout = (
            (data['close'] > data['close'].rolling(20).max().shift(1)) &  # 创20日新高
            (data['volume'] > data['volume'].rolling(20).mean() * 1.5)    # 成交量是20日均量的1.5倍
        )
        
        # 3. 放宽趋势判断条件
        trend_up = (
            (data['ma_fast'] > data['ma_mid']) |  # 快线上穿中线
            (data['close'] > data['ma_fast']) |   # 价格在快线上方
            short_trend |                         # 短期趋势向上
            breakout                              # 突破信号
        )
        
        # 4. 优化动量判断
        momentum_strong = (
            (data['roc'] > 0) |                  # ROC为正
            (data['trend_strength'] > 0) |       # 趋势为正
            (data['close'].pct_change(5) > 0.03) # 5日涨幅超过3%
        )
        
        # 5. 优化成交量判断
        volume_active = (
            (data['volume'] > data['volume_ma']) |  # 成交量大于均线
            (data['volume'].pct_change() > 0.5)     # 成交量单日放大50%
        )
        
        # 6. 生成买入信号
        buy_condition = (
            trend_up & 
            (momentum_strong | volume_active)  # 动量或成交量满足一个即可
        )
        
        # 打印调试信息
        print("\n条件满足统计：")
        print(f"短期趋势条件满足次数: {short_trend.sum()}")
        print(f"突破条件满足次数: {breakout.sum()}")
        print(f"趋势向上条件满足次数: {trend_up.sum()}")
        print(f"动量条件满足次数: {momentum_strong.sum()}")
        print(f"成交量条件满足次数: {volume_active.sum()}")
        
        # 生成卖出信号 - 优化卖出条件
        sell_condition = (
            (data['close'] < data['ma_mid']) &  # 价格跌破中线
            (
                (data['trend_strength'] < -0.001) |  # 趋势转弱
                (data['rsi'] > self.config.RSI_OVERBOUGHT) |  # RSI超买
                (
                    (data['close'] < data['ma_fast']) &  # 价格跌破快线
                    (data['volume'] > data['volume_ma'] * 1.2)  # 放量下跌
                )
            )
        )
        
        signals.loc[buy_condition, 'signal'] = 1
        signals.loc[sell_condition, 'signal'] = -1
        
        # 打印信号统计
        print(f"\n信号统计：")
        print(f"买入信号数量: {(signals['signal'] == 1).sum()}")
        print(f"卖出信号数量: {(signals['signal'] == -1).sum()}")
        
        # 打印趋势强度统计
        print("\n趋势强度统计：")
        print(f"趋势强度大于阈值的天数: {(data['trend_strength'] > self.config.TREND_THRESHOLD).sum()}")
        print(f"趋势强度最大值: {data['trend_strength'].max():.4f}")
        print(f"趋势强度最小值: {data['trend_strength'].min():.4f}")
        print(f"趋势强度均值: {data['trend_strength'].mean():.4f}")
        
        # 打印一些关键时点的数据
        print("\n关键指标样本：")
        sample_dates = data.index[::50]  # 每50天取一个样本
        for date in sample_dates:
            print(f"\n日期: {date}")
            print(f"收盘价: {data.loc[date, 'close']:.3f}")
            print(f"RSI: {data.loc[date, 'rsi']:.2f}")
            print(f"趋势强度: {data.loc[date, 'trend_strength']:.4f}")
            print(f"MACD柱: {data.loc[date, 'macd_hist']:.4f}")
        
        return signals
        
    def calculate_position_size(self, data, current_price, current_position):
        """计算仓位大小"""
        if current_position == 0:
            trend_strength = data['trend_strength'].iloc[-1]
            rsi = data['rsi'].iloc[-1]
            price_change = data['close'].pct_change(5).iloc[-1]  # 5日涨跌幅
            
            # 突破行情 - 更激进的仓位
            if price_change > 0.05 and data['volume'].iloc[-1] > data['volume_ma'].iloc[-1] * 1.5:
                return self.config.INITIAL_POSITION * 1.2  # 加大仓位
            
            # 强趋势 - 标准仓位
            elif trend_strength > self.config.TREND_THRESHOLD * 2:
                if rsi < 60:
                    return self.config.INITIAL_POSITION
                return self.config.INITIAL_POSITION * 0.8
            
            # 普通趋势 - 谨慎仓位
            elif trend_strength > 0:
                if rsi < 50:
                    return self.config.INITIAL_POSITION * 0.7
                return self.config.INITIAL_POSITION * 0.5
            
            return 0
        
        elif current_position < self.config.MAX_POSITIONS:
            # 加仓条件 - 更积极的加仓
            if (data['trend_strength'].iloc[-1] > 0 and  # 趋势为正
                data['rsi'].iloc[-1] < 60 and  # RSI不太高
                data['close'].pct_change(3).iloc[-1] > 0):  # 3日上涨
                
                return min(
                    self.config.MAX_POSITIONS - current_position,
                    self.config.POSITION_STEP
                )
        
        return 0
        
    def update_stop_loss(self, current_price, position_price):
        """更新止损价格"""
        trend_strength = self.data['trend_strength'].iloc[-1]
        rsi = self.data['rsi'].iloc[-1]
        price_change = self.data['close'].pct_change(5).iloc[-1]  # 5日涨跌幅
        
        # 动态调整止损比例
        if trend_strength > self.config.TREND_THRESHOLD * 2:  # 强趋势
            if price_change > 0.05:  # 5日涨幅超过5%
                stop_ratio = self.config.TRAILING_STOP * 1.5  # 大幅放宽止损
            elif rsi < 60:  # RSI不太高
                stop_ratio = self.config.TRAILING_STOP * 1.2  # 适度放宽止损
            else:
                stop_ratio = self.config.TRAILING_STOP
        else:  # 普通趋势
            if price_change < -0.03:  # 5日跌幅超过3%
                stop_ratio = self.config.TRAILING_STOP * 0.7  # 显著收紧止损
            elif rsi > 70:  # RSI较高
                stop_ratio = self.config.TRAILING_STOP * 0.8  # 适度收紧止损
            else:
                stop_ratio = self.config.TRAILING_STOP
        
        fixed_stop = position_price * (1 - self.config.FIXED_STOP_LOSS)
        trailing_stop = current_price * (1 - stop_ratio)
        
        self.current_stop_loss = max(fixed_stop, trailing_stop)
        
    def check_stop_loss(self, current_price):
        """检查是否触发止损"""
        return current_price < self.current_stop_loss if self.current_stop_loss > 0 else False
        
    def backtest(self, data):
        """执行回测"""
        print("开始回测...")
        
        self.data = data.copy()
        data = self.calculate_indicators(data)
        
        # 使用ffill()代替fillna(method='ffill')
        data = data.ffill()
        
        # 检查数据
        print("\n数据检查：")
        print(f"数据起始日期: {data.index[0]}")
        print(f"数据结束日期: {data.index[-1]}")
        print(f"数据条数: {len(data)}")
        
        # 检查空值
        null_counts = data.isnull().sum()
        print("\n空值统计：")
        print(null_counts[null_counts > 0])
        
        # 计算趋势强度 - 移到这里
        data['trend_strength'] = self.calculate_trend_strength(data)
        self.data = data  # 更新self.data，确保包含trend_strength
        
        # 生成交易信号
        signals = self.generate_signals(data)
        
        # 市场环境判断
        data['market_trend'] = (
            (data['close'] > data['ma_mid']) | 
            (data['volume'] > data['volume_ma'])
        ).astype(int)
        
        data['market_strength'] = data['market_trend'].rolling(5).mean().fillna(0)
        
        # 打印市场环境统计
        print("\n市场环境统计：")
        print(f"市场强势天数: {(data['market_strength'] > 0.2).sum()}")
        
        dates = data.index.tolist()
        portfolio_values = []
        cash = self.config.INITIAL_CAPITAL
        position = 0
        position_price = 0
        
        for i, date in enumerate(dates):
            current_price = data.loc[date, 'close']
            
            # 更细致的市场环境判断
            market_condition = (
                (data.loc[date, 'trend_strength'] > 0) or  # 趋势为正
                (data.loc[date, 'close'] > data.loc[date, 'ma_mid']) or  # 价格在中线上方
                (data.loc[date, 'rsi'] < 60)  # RSI不太高
            )
            
            # 检查止损
            if position > 0:
                if self.check_stop_loss(current_price):
                    sell_amount = position * current_price
                    cash += sell_amount
                    self.trades.append({
                        'date': date,
                        'type': 'STOP_LOSS',
                        'price': current_price,
                        'amount': sell_amount,
                        'position': position,
                        'market_condition': market_condition,
                        'indicators': {
                            'roc': data.loc[date, 'roc'],
                            'rsi': data.loc[date, 'rsi'],
                            'macd_hist': data.loc[date, 'macd_hist'],
                            'market_strength': data.loc[date, 'market_strength'],
                            'trend_strength': data.loc[date, 'trend_strength']  # 添加趋势强度
                        }
                    })
                    position = 0
                    self.current_stop_loss = 0
                
                # 添加主动卖出逻辑
                elif signals.loc[date, 'signal'] == -1:
                    sell_amount = position * current_price
                    cash += sell_amount
                    self.trades.append({
                        'date': date,
                        'type': 'SELL',
                        'price': current_price,
                        'amount': sell_amount,
                        'position': position,
                        'market_condition': market_condition,
                        'indicators': {
                            'roc': data.loc[date, 'roc'],
                            'rsi': data.loc[date, 'rsi'],
                            'macd_hist': data.loc[date, 'macd_hist'],
                            'market_strength': data.loc[date, 'market_strength']
                        }
                    })
                    position = 0
                    self.current_stop_loss = 0
            
            # 买入逻辑
            if signals.loc[date, 'signal'] == 1 and position == 0:  # 移除market_condition判断
                new_position = self.calculate_position_size(data.loc[:date], current_price, position)
                if new_position > 0:
                    buy_amount = cash * new_position
                    new_shares = buy_amount / current_price
                    position += new_shares
                    cash -= buy_amount
                    position_price = current_price
                    self.update_stop_loss(current_price, position_price)
                    self.trades.append({
                        'date': date,
                        'type': 'BUY',
                        'price': current_price,
                        'amount': buy_amount,
                        'position': position,
                        'market_condition': market_condition,
                        'indicators': {
                            'roc': data.loc[date, 'roc'],
                            'rsi': data.loc[date, 'rsi'],
                            'macd_hist': data.loc[date, 'macd_hist'],
                            'market_strength': data.loc[date, 'market_strength']
                        }
                    })
            
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
                f.write(f"波动率均线周期: {self.config.ATR_MA}日\n")
                f.write(f"趋势阈值: {self.config.TREND_THRESHOLD}\n")
                f.write(f"RSI超卖阈值: {self.config.RSI_OVERSOLD}\n")
                f.write(f"RSI超买阈值: {self.config.RSI_OVERBOUGHT}\n")
                f.write(f"最大持仓比例: {self.config.MAX_POSITIONS*100}%\n")
                f.write(f"单次交易仓位: {self.config.POSITION_STEP*100}%\n\n")
                
                f.write("策略绩效分析：\n")
                f.write("="*50 + "\n")
                f.write(f"策略总收益率: {(portfolio_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL*100:.2f}%\n")
                f.write(f"基准总收益率: {(benchmark_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL*100:.2f}%\n")
                f.write(f"策略最大回撤: {((portfolio_value - portfolio_value.cummax()) / portfolio_value.cummax()).min()*100:.2f}%\n")
                f.write(f"基准最大回撤: {((benchmark_value - benchmark_value.cummax()) / benchmark_value.cummax()).min()*100:.2f}%\n")
                f.write(f"策略夏普比率: {((portfolio_value.pct_change().dropna().mean() * np.sqrt(252)) / portfolio_value.pct_change().dropna().std()) * 100:.2f}%\n")
                f.write(f"基准夏普比率: {((benchmark_value.pct_change().dropna().mean() * np.sqrt(252)) / benchmark_value.pct_change().dropna().std()) * 100:.2f}%\n")
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
            # 尝试加载中文字体
            try:
                font = FontProperties(fname=r'C:\Windows\Fonts\SimHei.ttf')  # Windows系统
            except:
                try:
                    font = FontProperties(fname=r'/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf')  # Linux系统
                except:
                    font = FontProperties(family='sans-serif')  # 降级方案
            
            # 设置全局字体
            plt.rcParams['font.family'] = font.get_family()
            plt.rcParams['axes.unicode_minus'] = False
            
            # 创建图表
            fig = plt.figure(figsize=(15, 20))
            
            # 确保所有数据使用相同的索引
            common_index = data.index
            portfolio_value = portfolio_value.reindex(common_index)
            benchmark_value = benchmark_value.reindex(common_index)
            
            # 1. 价格和均线
            ax1 = plt.subplot(411)
            ax1.plot(common_index, data['close'], label='价格', color='blue', linewidth=1.5)
            ax1.plot(common_index, data['ma_fast'], 
                    label=f'{self.config.FAST_MA}日均线', 
                    color='red', linestyle='--', alpha=0.8)
            ax1.plot(common_index, data['ma_mid'], 
                    label=f'{self.config.MID_MA}日均线', 
                    color='orange', linestyle='--', alpha=0.8)
            ax1.plot(common_index, data['ma_slow'], 
                    label=f'{self.config.SLOW_MA}日均线', 
                    color='green', linestyle='--', alpha=0.8)
            
            # 标注交易点
            buy_label = sell_label = stop_label = False
            for trade in self.trades:
                if trade['type'] == 'BUY' and not buy_label:
                    ax1.scatter(trade['date'], trade['price'], color='red', marker='^', 
                              s=100, label='买入')
                    buy_label = True
                elif trade['type'] == 'SELL' and not sell_label:
                    ax1.scatter(trade['date'], trade['price'], color='green', marker='v', 
                              s=100, label='卖出')
                    sell_label = True
                elif trade['type'] == 'STOP_LOSS' and not stop_label:
                    ax1.scatter(trade['date'], trade['price'], color='black', marker='x', 
                              s=100, label='止损')
                    stop_label = True
                else:
                    ax1.scatter(trade['date'], trade['price'], 
                              color={'BUY': 'red', 'SELL': 'green', 'STOP_LOSS': 'black'}[trade['type']], 
                              marker={
                                  'BUY': '^', 
                                  'SELL': 'v', 
                                  'STOP_LOSS': 'x'
                              }[trade['type']], 
                              s=100)
            
            # 设置标题和图例
            ax1.set_title('价格走势与交易信号', fontproperties=font, fontsize=12, pad=15)
            ax1.legend(prop=font, loc='best', fontsize=10, framealpha=0.8)
            ax1.grid(True, alpha=0.4)
            
            # 2. RSI
            ax2 = plt.subplot(412)
            ax2.plot(common_index, data['rsi'], label='RSI', color='purple', linewidth=1.5)
            ax2.axhline(y=self.config.RSI_OVERSOLD, color='g', linestyle='--', alpha=0.8)
            ax2.axhline(y=self.config.RSI_OVERBOUGHT, color='r', linestyle='--', alpha=0.8)
            ax2.set_title('RSI指标', fontproperties=font, fontsize=12, pad=15)
            ax2.legend(prop=font, loc='best', fontsize=10, framealpha=0.8)
            ax2.grid(True, alpha=0.4)
            
            # 3. MACD
            ax3 = plt.subplot(413)
            ax3.plot(common_index, data['macd'], label='MACD', color='blue', linewidth=1.5)
            ax3.plot(common_index, data['signal'], label='Signal', color='orange', linewidth=1.5)
            ax3.bar(common_index, data['macd_hist'], label='Histogram', color='gray', alpha=0.3)
            ax3.set_title('MACD指标', fontproperties=font, fontsize=12, pad=15)
            ax3.legend(prop=font, loc='best', fontsize=10, framealpha=0.8)
            ax3.grid(True, alpha=0.4)
            
            # 4. 收益对比
            ax4 = plt.subplot(414)
            ax4.plot(common_index, portfolio_value, label='策略收益', color='red', linewidth=1.5)
            ax4.plot(common_index, benchmark_value, label='基准收益', color='blue', linewidth=1.5)
            ax4.set_title('策略收益与基准对比', fontproperties=font, fontsize=12, pad=15)
            ax4.legend(prop=font, loc='best', fontsize=10, framealpha=0.8)
            ax4.grid(True, alpha=0.4)
            
            # 添加收益率标注
            strategy_returns = (portfolio_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            benchmark_returns = (benchmark_value.iloc[-1] - self.config.INITIAL_CAPITAL) / self.config.INITIAL_CAPITAL
            ax4.text(0.02, 0.98, 
                    f'策略收益率: {strategy_returns*100:.2f}%\n基准收益率: {benchmark_returns*100:.2f}%', 
                    transform=ax4.transAxes, 
                    verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                    fontsize=10,
                    fontproperties=font)
            
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

    def calculate_trend_strength(self, data):
        """计算趋势强度"""
        # 计算均线斜率 - 缩短周期
        ma_slopes = data['ma_fast'].diff(3) / data['ma_fast'].shift(3)
        
        # 计算价格动能
        price_momentum = data['close'].pct_change(5)
        
        # 计算RSI动能
        rsi_momentum = (data['rsi'] - 50) / 50  # 归一化RSI
        
        # 综合评分 - 调整权重
        trend_score = (
            ma_slopes * 0.4 + 
            price_momentum * 0.4 + 
            rsi_momentum * 0.2
        )
        
        return trend_score 