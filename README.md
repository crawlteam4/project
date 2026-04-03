# D-DAS : 대드론 방어체계 최적지 선정 서비스
> **Drone Defense Allocation Service**  
> 국내 도심 환경을 고려한 대드론 방어체계(C-UAS) 최적 입지 분석 웹 서비스

![Python](https://img.shields.io/badge/Python-3.14+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?logo=streamlit)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql)

---

## 프로젝트 소개

D-DAS는 서울시 도심 내 드론 위협에 대응하기 위한 **대드론 방어 무기 최적 배치 지점**을 자동으로 산출하는 웹 서비스입니다.  
사용자가 격자 크기, 사정거리, 시설 가중치 등 조건을 직접 설정하면, 알고리즘이 최적 후보지를 지도 위에 시각화합니다.

---

## 폴더 구조
```
project/
├── DDAS.py              # 메인 앱 (로그인 & 홈)
├── setup.py / setup.bat # 환경 설정 스크립트
├── utils.py             # 공통 유틸 함수
├── pages/               # Streamlit 멀티페이지
│   ├── 1_입지 분석.py
│   ├── 2_후보지 조건 설정.py
│   ├── 3_후보지 계산.py
│   └── ...
├── get/                 # 데이터 크롤링 모듈
├── calculate/           # 최적 입지 계산 알고리즘
├── visualize/           # 시각화 모듈
├── db/                  # DB push 모듈 
├── data/                # 원본 데이터
├── final_data/          # 전처리 완료 데이터
└── images/              # 이미지 리소스
```

---

## 실행 방법

### 1. 저장소 클론
```bash
git clone https://github.com/crawlteam4/project.git
cd project
```

### 2. 환경설정 (가상환경 생성 + 패키지 설치)
```bash
python setup.py
```

### 3. DB config 설정
`.streamlit/secrets.toml` 파일을 생성하고 아래 내용을 입력합니다:
```toml
[mysql]
host = "your_host"
port = 3306
user = "your_user"
password = "your_password"
database = "your_database"
```

### 4. 앱 실행
```bash
streamlit run DDAS.py
```

---

## 분석 흐름

| 단계 | 페이지 | 설명 |
|------|--------|------|
| 1  | 데이터 탐색 | 서울시 Raw Data를 지도에서 확인 |
| 2 | 후보지 조건 설정 | 격자 생성, 사정거리 및 가중치 설정 |
| 3 | 후보지 계산 | 알고리즘으로 최적 배치 지점 자동 산출 |
| 4 | 결과 요약 | 상세 점수 확인 및 결과 시각화 |
| 5 | 시나리오 분석 | 상이한 변수를 설정한 시나리오 간 상호 비교 |

---

## 기술 스택

- **Frontend/UI**: Streamlit
- **Backend**: Python, pymysql, sklearn, pandas, numpy
- **Database**: MySQL
- **데이터 수집**: BeautifulSoup / Selenium (크롤링)
- **시각화**: Folium, Plotly 등

---

## 팀원

| 이름 | 역할 |
|------|------|
| 안찬이 | 프로젝트 매니저 |
| 주진성 | 알고리즘 개발 |
| 김민주 | UI/UX 디자인 |
| 권희성 | 데이터 크롤링 |

---