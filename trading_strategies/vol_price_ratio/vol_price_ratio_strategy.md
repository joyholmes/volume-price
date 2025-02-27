# 量化交易策略集合

本项目包含多个量化交易策略的实现，每个策略都有独立的配置和回测系统。

## 策略列表

1. [量价比策略](trading_strategies/vol_price_ratio/)
2. [趋势动量策略](trading_strategies/trend_momentum/)

## 项目结构

请参考 [trading_strategies/README.md](trading_strategies/README.md) 了解详细的项目结构。

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置 Tushare Token：
在各策略的 config.py 中设置你的 Tushare token。

3. 运行策略：
参考各策略目录下的说明文档 