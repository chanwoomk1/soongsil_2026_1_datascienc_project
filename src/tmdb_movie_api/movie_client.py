# src/tmdb_movie_api/movie_client.py
import requests
from collections import defaultdict
from typing import List, Tuple, Optional, Any
from UTILS import URL, HEADERS

class DiscoverMovieApiDTO:
    """TMDB Discover API 요청 파ام터를 유연하게 캡슐화하는 DTO"""
    def __init__(self, release_date: str, end_date: str):
        self.language = "ko-KR"
        self.release_date = release_date
        self.end_date = end_date
        self.region = "KR"

    def get_discoverAPI_param(self, page: int) -> dict:
        return {
            "language": self.language,
            "primary_release_date.gte": self.release_date,
            "primary_release_date.lte": self.end_date,
            "region": self.region,
            "sort_by": "primary_release_date.desc",
            "page": page
        }

def get_data_by_release_date_total_page(params: dict) -> int:
    """조건에 맞는 영화 디스커버리 쿼리의 전체 페이지 수 반환"""
    discover_url = f"{URL}3/discover/movie"
    response = requests.get(discover_url, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json().get("total_pages", 1)
    return 0

def get_data_by_release_date(params: dict, page: int) -> List[dict]:
    """[보완] .copy()를 사용하여 원본 파라미터 오염을 방지하고 특정 페이지 데이터 조회"""
    safe_params = params.copy()
    safe_params["page"] = page
    
    discover_url = f"{URL}3/discover/movie"
    response = requests.get(discover_url, headers=HEADERS, params=safe_params)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def get_movie_name(movie_id: int) -> Optional[dict]:
    """영화 상세 정보 및 오리지널 타이틀 반환"""
    detail_url = f"{URL}3/movie/{movie_id}"
    response = requests.get(detail_url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return None

def get_movie_provider(movie_id: int, dict_area_and_category: Optional[dict] = None) -> defaultdict:
    """영화의 스트리밍/렌트/구매 프로바이더 플랫폼 목록 추출 (소문자 표준화 처리)"""
    if dict_area_and_category is None:
        dict_area_and_category = {"KR": ["flatrate", "rent", "buy"]}
        
    provider_url = f"{URL}3/movie/{movie_id}/watch/providers"
    response = requests.get(provider_url, headers=HEADERS)
    res = defaultdict(lambda: defaultdict(list))
    
    if response.status_code == 200:
        data = response.json().get("results", {})
        for area, categories in dict_area_and_category.items():
            area_data = data.get(area, {})
            for cat in categories:
                providers = area_data.get(cat, [])
                for p in providers:
                    # 원-핫 인코딩 시 문자열 매칭 공백 오류를 막기 위해 .lower() 및 .strip() 처리 권장
                    provider_name = p.get("provider_name", "").lower().strip()
                    res[area][cat].append(provider_name)
    return res

def get_release_data_list(movie_id: int) -> List[dict]:
    """영화의 전세계 국가별/타입별 세부 개봉 일정 raw 데이터 리스트 확보"""
    dates_url = f"{URL}3/movie/{movie_id}/release_dates"
    response = requests.get(dates_url, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json().get("results", []) 
        data_li = [
            {
                "movie_id": str(movie_id),
                "iso_3166_1": d["iso_3166_1"],
                "release_dates": r["release_date"],
                "type": r["type"],
                "note": r["note"]
            } 
            for d in data for r in d.get("release_dates", [])
        ]
        return data_li
    return []

def get_kr_detailed_dates(movie_id: int) -> Tuple[str, str, str, str]:
    """[추가] 홀드백 계산의 핵심이 되는 한국 로컬 극장 개봉일 및 VOD 출시일 정밀 파싱 함수"""
    dates_url = f"{URL}3/movie/{movie_id}/release_dates"
    theater_date, theater_note, digital_date, digital_note = "", "", "", ""
    
    try:
        response = requests.get(dates_url, headers=HEADERS)
        if response.status_code == 200:
            results = response.json().get("results", [])
            releases = []
            for country_data in results:
                if country_data.get("iso_3166_1") == "KR":
                    releases = country_data.get("release_dates", [])
                    for rel in releases:
                        release_type = rel.get("type")
                        date_str = rel.get("release_date", "").split("T")[0]
                        note_str = rel.get("note", "").strip()
                        
                        if release_type == 3:    # 정식 극장 개봉
                            theater_date = date_str
                            theater_note = note_str
                        elif release_type == 4:  # 디지털 / VOD 출시
                            digital_date = date_str
                            digital_note = note_str
            
            # 한국 데이터는 있으나 타입 분류(3, 4)가 누락된 예외 케이스 방어 로직
            if releases:
                if not theater_date:
                    theater_date = releases[0].get("release_date", "").split("T")[0]
                    theater_note = releases[0].get("note", "").strip()
                if not digital_date and len(releases) > 1:
                    digital_date = releases[-1].get("release_date", "").split("T")[0]
                    digital_note = releases[-1].get("note", "").strip()
    except Exception:
        pass
        
    return theater_date, theater_note, digital_date, digital_note

def get_movie_list(params: dict, total_page: int) -> List[dict]:
    """[보완] 파라미터 복사본을 사용하여 다중 페이지 영화 기본 정보(ID, Title) 리스트 일괄 획득"""
    movie_list = []
    discover_url = f"{URL}3/discover/movie"
    
    safe_params = params.copy()
    for page in range(1, total_page + 1):
        safe_params["page"] = page
        response = requests.get(discover_url, params=safe_params, headers=HEADERS)
        if response.status_code == 200:
            movies = response.json().get("results", [])
            movie_list += [{"title": m["title"], "id": m["id"]} for m in movies]
        else:
            print(f"⚠️ Page {page} 로드 실패 (Status: {response.status_code})")
            
    return movie_list