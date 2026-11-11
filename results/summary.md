# Results: NVDA daily, 2013-01-02 to 2026-11-10

Cost per fill: 0.10% (commission + slippage). Signals at the close, fills at the next open.

| Strategy        | Total return   | CAGR   | Max drawdown   | Volatility   |   Sharpe |   Sortino |   Calmar | Time in market   |   Trades | Win rate   | Avg trade   | Profit factor   | Avg trading days held   |
|:----------------|:---------------|:-------|:---------------|:-------------|---------:|----------:|---------:|:-----------------|---------:|:-----------|:------------|:----------------|:------------------------|
| SMC + WaveTrend | 1,690.9%       | 23.2%  | -50.6%         | 28.1%        |     0.88 |      0.83 |     0.46 | 43.9%            |       67 | 50.7%      | 5.4%        | 2.63            | 22.85                   |
| WaveTrend only  | 3,247.4%       | 28.8%  | -58.7%         | 33.0%        |     0.93 |      0.99 |     0.49 | 55.5%            |       89 | 49.4%      | 5.0%        | 2.44            | 21.74                   |
| SMC only        | 15,629.2%      | 44.1%  | -56.0%         | 39.1%        |     1.13 |      1.43 |     0.79 | 81.1%            |        3 | 66.7%      | 1,370.1%    | 470.61          | 942.00                  |
| Buy & hold NVDA | 58,267.5%      | 58.4%  | -66.3%         | 45.4%        |     1.24 |      1.81 |     0.88 | 100.0%           |        0 | -          | -           | -               | -                       |
| Buy & hold SPY  | 551.7%         | 14.5%  | -33.7%         | 16.8%        |     0.89 |      1.09 |     0.43 | 100.0%           |        0 | -          | -           | -               | -                       |

## Robustness: two halves of the sample

| Period                                 | Strategy CAGR   | Strategy max DD   | Buy & hold CAGR   | Buy & hold max DD   |
|:---------------------------------------|:----------------|:------------------|:------------------|:--------------------|
| First half (2013-01-02 to 2019-12-03)  | 33.1%           | -50.6%            | 51.7%             | -56.0%              |
| Second half (2019-12-04 to 2026-11-10) | 14.0%           | -34.0%            | 65.0%             | -66.3%              |

## Parameters

|                |   value |
|:---------------|--------:|
| swing_len      |      50 |
| internal_len   |       5 |
| entry_wt_max   |       0 |
| div_level      |     -40 |
| use_divergence |       1 |
| exit_wt_level  |      60 |
| use_stop       |       1 |
| stop_lookback  |      10 |
