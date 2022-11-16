import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import time
import os
import re

# from IPython.display import clear_output

# 기본 설정
binance = ccxt.binance(config={
    'options': {"defaultType" : "future"}
})

### 데이터 다운 및 업데이트 하기
def Save_and_Update_Data(coin, save_path):
    file_name = coin.replace("/USDT","_M") # 이름 수정
    
    if os.path.exists(os.path.join(save_path, f"{file_name}.xlsx"))==True: # 파일이 존재할 경우
        df = pd.read_excel(os.path.join(save_path,f"{file_name}.xlsx"),index_col=0)
        past = datetime.datetime.strptime(str(df.iloc[-1].name), f'%Y-%m-%d %H:%M:00')
        now = datetime.datetime.now().strftime(f'%Y-%m-%d %H:%M:00')
        now = datetime.datetime.strptime(now, f'%Y-%m-%d %H:%M:00')
        diff = str(now-past)
        h, m, s = list(map(int, diff.split(":")))
        total_time_diff = (h * 60) + m + s # 분으로 환산
        total_time_diff

        if total_time_diff > 0: # 1분 이상 차이 날 경우
            new_ohlcv = binance.fetch_ohlcv(
                f'{coin}', 
                timeframe='1m',
                params={"startTime":df.index[-1]},
                limit=total_time_diff
            )
            new_df = pd.DataFrame(new_ohlcv, columns=['datetime','open','high','low','close','volume'])
            Cal_DataFrame(new_df) # OHCLV 값 기반으로 계산
            new_df['datetime'] = pd.to_datetime(new_df['datetime'], unit='ms') + datetime.timedelta(hours=9)
            new_df.set_index('datetime',inplace=True)
            df = pd.concat([df,new_df])
            print(f"[{coin}] Update {total_time_diff} minutes")
        else: # 1분 이하로 초단위로 차이 날 경우, 맨 마지막 행 업데이트
            new_ohlcv = binance.fetch_ohlcv(f'{coin}', timeframe='1m',limit=1)
            new_df = pd.DataFrame(new_ohlcv, columns=['datetime','open','high','low','close','volume'])
            Cal_DataFrame(new_df) # OHCLV 값 기반으로 계산
            new_df['datetime'] = pd.to_datetime(new_df['datetime'], unit='ms') + datetime.timedelta(hours=9)
            new_df.set_index('datetime',inplace=True)
            df = pd.concat([df[:-1],new_df])
#             print(f"[{coin}] Update Under 1 minutes")
    else: # 파일이 존재하지 않을 경우
        ### Data가 없을 때 1500개 1분봉 데이터 다운
#         print(f"[{coin}] New Data Saving . . .")
        ohlcv = binance.fetch_ohlcv(f'{coin}', timeframe='1m',limit=1500)
        df = pd.DataFrame(ohlcv, columns=['datetime','open','high','low','close','volume'])
        Cal_DataFrame(df) # OHCLV 값 기반으로 계산
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms') + datetime.timedelta(hours=9)
        df.set_index('datetime',inplace=True)
        time.sleep(0.5)

    df = df.loc[~df.index.duplicated(keep='last')] #최신행만 남겨두고 중복된 행 제거
    df.to_excel(f'{os.path.join(save_path, file_name)}.xlsx') # 엑셀 데이터로 저장
    
    return df
    
def Cal_DataFrame(DataFrame): #[time, open, high, low, close, volume]
    df = DataFrame
    
    # 가중치를 둔 거래대금
    df['Cal_Value'] = (df['open']*0.20+df['high']*0.15+df['low']*0.15+df['close']*0.50)*df['volume']/1000000
     

    return df

def Up_Sampling(DataFrame, date): # 1분봉 데이터프레임, 날짜 입력
    df = DataFrame.copy()
    new_df = DataFrame.copy()
    new_df['open'] = df.resample(f'{date}').first()['open'] # 시가
    new_df['high'] = df.resample(f'{date}').max()['high'] # 고가
    new_df['low'] = df.resample(f'{date}').min()['low'] # 저가
    new_df['close'] = df.resample(f'{date}').last()['close'] # 종가
    new_df['volume'] = df.resample(f'{date}').sum()['volume'] # 거래량
    new_df['Cal_Value'] = df.resample(f'{date}').sum()['Cal_Value'] # 거래대금

    new_df = new_df.resample(f'{date}').first()
    return new_df

# 주문 거래 금액 비율, 시장 참여자들의 거래 비율
def Trades_Summary():
    trades = binance.fetchTrades("BTCUSDT",limit=1000) #1000개의 BTCUSDT를 거래 내역 가져온다
    Value_dics = {}
    
    
    buy_sum = 0 # 매수 총금액
    sell_sum = 0 # 매도 총금액
    taker_num = 0 # 시장가 숫자
    maker_num = 0 # 지정가 숫자
    
    for i in range(len(trades)):
        if trades[i]['side'] == "buy": #매수일 경우
            buy_sum += trades[i]['cost']
        elif trades[i]['side'] == "sell": # 매도일 경우
            sell_sum += trades[i]['cost']

        if trades[i]['info']['m'] == False: # 시장가일경우
            taker_num += 1
        elif trades[i]['info']['m'] == True: #지정가일경우
            maker_num +=1

    Value_dics['buy_sum'] = buy_sum
    Value_dics['sell_sum'] = sell_sum
    Value_dics['maker_num'] = maker_num
    Value_dics['taker_num'] = taker_num
    
    return Value_dics
    
    
    
        
def Values_Print(DataFrame, Total_Value_Dictionary):
    ### ---------------Data Preprocessing
    df_5 = Up_Sampling(DataFrame,'5T') # 1분봉을 5분봉으로 바꾸기
    
    # clear_output() #이전 print글자 지워주기 (주피터 환경)
#     os.system('cls') # 윈도우 환경

    ### ---------------Summary Values
    buy_sum = Total_Value_Dictionary['buy_sum']
    sell_sum = Total_Value_Dictionary['sell_sum']
    maker_num = Total_Value_Dictionary['maker_num']
    taker_num = Total_Value_Dictionary['taker_num']
    

    print("===============Summary===============")        
    print(f"[Buy / Sell] Cost Ratio  and : {round((buy_sum/sell_sum),2)}")
    print(f"[Buy - Sell] Cost : {round((buy_sum - sell_sum),2)}")
    print(f"[Maker / Taker] Number Ratio : {round((maker_num/taker_num),2)}")
    
    print("")
    if round((buy_sum/sell_sum),2) < 0.5:
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \nSell 금액 우세")
    elif round((buy_sum/sell_sum),2) > 1.5:
        print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \nBuy 금액 우세")

    
    ### --------------- OHLCV 출력
    if df_5.iloc[-1]['volume'] < df.iloc[-1]['volume']:
        print("거래량 급증 이전 5분보다 상승")
    if ((df['Cal_Value'][-2] + df['Cal_Value'][-3])/2*3) < df['Cal_Value'][-1]:
        print("거래대금 급증")
        print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    pass


def Drawing_Graph(Total_Value_Dictionary):
    global graph_x_line
    global graph_y_line
    global graph_index_num
    
    buy_sum = Total_Value_Dictionary['buy_sum']
    sell_sum = Total_Value_Dictionary['sell_sum']
    maker_num = Total_Value_Dictionary['maker_num']
    taker_num = Total_Value_Dictionary['taker_num']
    
    #----------------------------------------------------------------------------------#
    
    bs_ratio = round((buy_sum/sell_sum),2)
    mt_ratio = round((maker_num/taker_num),2)
    
    
    #----------------------------------------------------------------------------------#
    # 그래프 그리기
    graph_x_line.append(graph_index_num)
    graph_y_line.append(bs_ratio)
    
    # ax 에 그리기
    ax.plot(graph_x_line,graph_y_line,color='b')
    
    fig.canvas.draw()
    
    ax.set_xlim(left=max(0,graph_index_num-50),right=graph_index_num+50)


### 기본 설정
coin ='BTC/USDT'
path = os.path.join(os.getcwd(),"Save Data") # 데이터 저장 위치

### 그래프 설정
graph_index_num = 0
graph_x_line, graph_y_line = [], []


plt.rcParams['animation.html'] = 'jshtml'
fig = plt.figure()
ax = fig.add_subplot(111)
fig.show()

start_time = time.time()
print("*-------------Start-------------*")
while True:
    df = Save_and_Update_Data(coin,path) # 데이터 저장 및 업데이트
    
    summary_values = Trades_Summary() # 거래현형 요약본
    
    Values_Print(df, summary_values)
    Drawing_Graph(summary_values)
    time.sleep(0.5)
    
    
    end_time = time.time()
    
    if (end_time - start_time) > 60*30: # 30분 뒤 종료
        break
    graph_index_num +=1
print("*--------------End--------------*")