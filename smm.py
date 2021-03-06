# -*- coding: utf-8 -*-
from datetime import datetime, time
from math import sqrt
from flyerbots.strategy import Strategy
from flyerbots.indicator import *

no_trade_time_range = [
    # (time( 7,55), time( 8, 5)), # JST 16:55-17:05
    # (time( 8,55), time( 9, 5)), # JST 17:55-18:05
    # (time( 9,55), time(10, 5)), # JST 18:55-19:05
    # (time(10,55), time(11, 5)), # JST 19:55-20:05
    # (time(11,55), time(12, 5)), # JST 20:55-21:05
    # (time(12,55), time(13, 5)), # JST 21:55-22:05
    # (time(13,55), time(14, 5)), # JST 22:55-23:05
    # (time(14,55), time(15, 5)), # JST 23:55-00:05
    # (time(15,55), time(23, 5)), # JST 00:55-08:05
    (time(18,55), time(19, 55)), # JST 03:55-04:55 Bitflyerメンテナンスタイム
]

def stdev(src):
    average = sum(src) / len(src)
    average_sq = sum(p**2 for p in src) / len(src)
    var = average_sq - (average * average)
    dev = sqrt(var)
    return dev

def zscore(source):
    average = sum(source)/len(source)
    average_sq = sum(p**2 for p in source) / len(source)
    variance = average_sq - (average * average)
    std = sqrt(variance)
    return (source[-1]-average)/std if std else 0

class simple_market_maker:

    def __init__(self):
        pass

    def loop(self, ohlcv, ticker, strategy, **other):

        # メンテナンス時刻
        t = datetime.utcnow().time()
        coffee_break = False
        for s, e in no_trade_time_range:
            if t >= s and t <= e:
                logger.info('Coffee break ...')
                coffee_break = True
                break

        # エントリー
        if not coffee_break:
            # 遅延評価
            dist = ohlcv.distribution_delay[-3:]
            delay = sorted(dist)[int(len(dist)/2)]

            # 指値幅計算
            spr = min(max(stdev(ohlcv.close),1000),5000)
            pairs = [(0.01, spr*0.7, '2', 9.5), (0.01, spr*0.35, '1', 4.5)]
            maxsize = sum(p[0] for p in pairs)
            buymax = sellmax = strategy.position_size
            mid = ohlcv.close[-1]
            z = zscore(ohlcv.volume_imbalance)
            ofs = z*9

            if delay>2.5:
                if strategy.position_size>=0.01:
                    strategy.order('Lc', 'sell', qty=0.01)
                elif strategy.position_size<=-0.01:
                    strategy.order('Sc', 'buy', qty=0.01)
                for _, _,suffix,_ in pairs:
                    strategy.cancel('L'+suffix)
                    strategy.cancel('S'+suffix)
            else:
                for size, width, suffix, period in pairs:
                    buyid = 'L'+suffix
                    sellid = 'S'+suffix
                    buysize = min(maxsize-buymax,size)
                    if buymax+buysize <= maxsize:
                        strategy.order(buyid, 'buy', qty=buysize, limit=int(mid-width+ofs),
                            seconds_to_keep_order=period, minute_to_expire=1)
                        buymax += buysize
                    else:
                        strategy.cancel(buyid)
                    sellsize = min(maxsize+sellmax,size)
                    if sellmax-sellsize >= -maxsize:
                        strategy.order(sellid, 'sell', qty=sellsize, limit=int(mid+width+ofs),
                            seconds_to_keep_order=period, minute_to_expire=1)
                        sellmax -= sellsize
                    else:
                        strategy.cancel(sellid)
        else:
            strategy.cancel_order_all()
            strategy.close_position()

if __name__ == "__main__":
    import settings
    import argparse
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('simple_market_maker.log'))
    logger = logging.getLogger("simple_market_maker")

    strategy = Strategy(simple_market_maker().loop, 5)
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.settings.max_ohlcv_size = 12*10
    strategy.settings.disable_rich_ohlcv = True
    strategy.risk.max_position_size = 0.02
    strategy.start()
