# src/tmdb_movie_api/collector.py
import os
import time
import pandas as pd

from UTILS import URL, HEADERS
from src.tmdb_movie_api.movie_client import get_movie_list, get_movie_provider,get_data_by_release_date_total_page

def run_streaming_movie_collector(params,output_path,
        target_providers = ["Netflix", "netflix", "Watcha", "Disney"]):
    
    release_date=params["primary_release_date.gte"]
    end_date=params["primary_release_date.lte"]
    print(f"{release_date} ~ {end_date} 기간 내 영화 기본 목록 조회 추출 시작...")
    # 원본 파일에서 total_page=700 줬던 묵직한 탐색 가동
    
    
    total_page=get_data_by_release_date_total_page(params)
    
    
    movies = get_movie_list(params, total_page=total_page)
    
    total_len = len(movies)
    print(f"총 {total_len}개의 영화 후보군 확보 완료. 로컬 구독(Flatrate) 유통 스크리닝 시작...")
    
    list_streamed_movie = []
    
    # 2. OTT 입점 여부 루프 필터링
    for idx, m in enumerate(movies, 1):
        movie_id = m["id"]
        
        # 안전하게 세부 프로바이더 데이터 조회
        provider_data = get_movie_provider(movie_id, {"KR": ["flatrate"]})
        kr_flatrates = provider_data.get("KR", {}).get("flatrate", [])
        
        # 타겟 스트리밍 서비스에 하나라도 걸리는지 확인
        if any(sp in s for s in kr_flatrates for sp in target_providers):
            list_streamed_movie.append(m)
            
        # 10개 단위 로깅
        if idx % 10 == 0:
            print(f"🔄 처리 진행률: [{idx} / {total_len}] - 현재까지 매칭 타겟 수: {len(list_streamed_movie)}개")
            
        # API 매너 타임 디레이 추가
        time.sleep(0.05)

    print("\n🏁 전수 스크리닝 완료! 판다스 마이그레이션 데이터셋 정제 진입...")

    # 3. 판다스 변형 및 메타정보 이식
    if list_streamed_movie:
        df = pd.DataFrame(list_streamed_movie)
        df["__release_date"] = release_date
        df["__end_date"] = end_date
        
        # 데이터 타입 안정성 확보
        df["title"] = df["title"].astype(str)
        df["__release_date"] = df["__release_date"].astype(str)
        df["__end_date"] = df["__end_date"].astype(str)
        
        # 4. 화이트리스트 최상단 구조에 선언한 data/ 폴더 하위로 타겟팅 자동 경로 생성
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"[성공] 최종 필터링 데이터셋이 안전하게 적재되었습니다: {output_path}")
    else:
        print("타겟 조건(OTT 입점)을 만족하는 영화가 존재하지 않아 수집을 종료합니다.")

if __name__ == "__main__":
    run_streaming_movie_collector()