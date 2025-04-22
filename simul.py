import polars as pl
import com_func as CF
import statistics as stats

df_sise = pl.DataFrame([])

def step_down(DTM, PRC):
    global df_sise
    # 검증을 위한 데이터의 저장
    new_row = pl.DataFrame({
        "DTM": [DTM],
        "PRC": [PRC]
    })
    df_sise = df_sise.vstack(new_row)

    threshold = 5
    base_tick_step_down = 200
    seq_inc_cnt, seq_dec_cnt = (0,0)
    # 이전 V자 반등이 없었던 경우
    df_target = df_sise.tail(base_tick_step_down)
    # 최소 50개 최대 150개로 판단하자
    # 꼭대기 이후 몇번 내려왔는지로 하자. 오르락 내리락으로 조건을 만족하는 것을 방지하기 위함
    # list_sise_for_rebound = CF.get_sise_list_by_high_price(df_sise)
    list_sise_for_rebound = list(df_target["PRC"])
    seq_inc_cnt, seq_dec_cnt = CF.count_up_down_trends(list_sise_for_rebound, threshold)
    if df_target.height > base_tick_step_down * 0.75:
        # 최근 30분 급락 추출
        # 가장 오랜된 5개 평균과 가장 최근 5개 평균의 차이로
        front_avg = int(stats.mean(list(df_target.head(5)["PRC"])))
        rear_avg = int(stats.mean(list(df_target.tail(5)["PRC"])))
        front_rear_rt = CF.calc_earn_rt(front_avg, rear_avg)
        print(f"{DTM} [{df_target.head(1)['DTM'][0]} ~ {df_target.tail(1)['DTM'][0]}] : {front_avg}, {rear_avg}, {front_rear_rt}  -  {seq_inc_cnt}, {seq_dec_cnt}")
        # 90% 이상 빠졌다면
        if front_rear_rt > 0.61:
            step_down_up_tf = True
            print(DTM, PRC)
            return True

    return False

LIST_SISE_PRICE = []
def side_step(DTM, PRC):
    global df_sise
    # 검증을 위한 데이터의 저장
    new_row = pl.DataFrame({
        "DTM": [DTM],
        "PRC": [PRC]
    })
    df_sise = df_sise.vstack(new_row)

    
    LIST_SISE_PRICE.append(PRC)
    inc_tf, dec_tf = CF.check_trend(LIST_SISE_PRICE[-5:], div='all')

    if len(LIST_SISE_PRICE) < 50:
                pass
    else:
        # 최근 5틱이 모두 상승이면서
        if inc_tf:
            base_tick = 150
            # 최근 150틱을 기준으로
            base_max_prc = max(LIST_SISE_PRICE[-base_tick:])
            base_min_prc = min(LIST_SISE_PRICE[-base_tick:])
            median_prc = stats.median(LIST_SISE_PRICE[-base_tick:])
            min_max_rt = CF.calc_earn_rt(base_max_prc, base_min_prc)
            median_prc = stats.median(LIST_SISE_PRICE[-base_tick:])
            # 0.3% 미만 상승 했거나 중간값 대비 위 아래로 0.3% 범위 내인 경우
            if (min_max_rt < 0.3) or (base_min_prc > median_prc * 0.997 and base_max_prc < median_prc * 1.003):
                slack_msg_sideways = f'### {base_tick}틱 횡보장 최소값 대비 최대 값 비율 {min_max_rt}% 및 {base_min_prc} ~ {base_max_prc} 구간 및 중간값({median_prc}) 0.3% 이내 후 상승. 매수!!!'
                print(f"{DTM} {PRC:,} :{slack_msg_sideways}")
                print(f"{DTM} {inc_tf} {PRC:,} : {min_max_rt},  {int(median_prc * 0.997)} VS {base_min_prc}, {base_max_prc} VS {int(median_prc * 1.003)}")
            
        
    return False


if __name__ == "__main__":
    df = pl.read_csv('./data/log_data_20250422.csv')
    # print(min(list(df['PRC'])))
    for row_dict in df.to_dicts():
        if side_step(row_dict['DTM'], row_dict['PRC']):
            break
    