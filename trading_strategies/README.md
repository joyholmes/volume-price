# 交易策略集合

本项目包含两个交易策略：

1. 量价比策略 (vol_price_ratio)
2. 趋势动量策略 (trend_momentum)

## 目录结构
```
trading_strategies/
├── README.md
├── common/              # 共用工具
│   └── utils.py        # 数据获取等通用函数
├── vol_price_ratio/    # 量价比策略
│   ├── config.py       # 策略配置
│   ├── strategy.py     # 策略实现
│   └── run_backtest.py # 回测入口
└── trend_momentum/     # 趋势动量策略
    ├── config.py       # 策略配置
    ├── strategy.py     # 策略实现
    └── run_backtest.py # 回测入口
```

## 使用方法

1. 运行量价比策略：
```bash
cd trading_strategies/vol_price_ratio
python run_backtest.py
```

2. 运行趋势动量策略：
```bash
cd trading_strategies/trend_momentum
python run_backtest.py
``` 