# 단국대 자유게시판 웹 서비스

이 프로젝트는 단국대학교 학생들을 위한 자유게시판 웹 서비스입니다. 
제안서 요구사항을 바탕으로 Python Flask와 Supabase(PostgreSQL)를 사용하여 구현되었습니다.

## 기술 스택
- **Backend:** Python Flask
- **Frontend:** HTML, CSS, JavaScript (바닐라)
- **Database:** Supabase PostgreSQL

## 주요 기능
- 회원가입 / 로그인 / 계정 관리 (비밀번호 해시 적용)
- 게시글 CRUD (탭 필터링 및 검색)
- 댓글 및 대댓글 (계층형)
- 좋아요/싫어요 반응 기능
- 관리자 권한 (게시판 탭 관리 및 모든 글/댓글 삭제 권한)

## 로컬 실행 방법

### 1. 가상환경 및 패키지 설치
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 환경 변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 내용을 알맞게 채웁니다.
```bash
cp .env.example .env
```
`.env` 파일에 발급받은 Supabase의 `DATABASE_URL`을 입력하세요.
(예: `postgresql://postgres.xxx:password@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres`)

### 3. 데이터베이스 초기화 및 관리자 계정 생성
다음 스크립트를 실행하면 테이블 생성, 기본 탭 삽입, **기본 관리자 계정** 생성이 자동으로 진행됩니다.
```bash
python database/setup_db.py
```
> **초기 관리자 계정 정보:**
> - ID: `admin`
> - PW: `admin1234`
> - Role: `ADMIN`
> 
> *주의: 실제 서비스로 운영할 경우 반드시 로그인 후 비밀번호를 변경하시거나 관리자 계정을 새로 생성하여 사용하세요.*

### 4. 서버 실행
```bash
python app.py
```
실행 후 `http://127.0.0.1:5000` 에 접속하여 서비스를 이용할 수 있습니다.

## Render 배포 방법
1. Render(https://render.com)에 로그인 후 "New Web Service"를 선택합니다.
2. 이 코드가 저장된 GitHub 저장소를 연결합니다.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `gunicorn app:app` (루트 경로에 app.py가 있을 경우)
5. **Environment Variables:** 설정 탭에서 `DATABASE_URL`과 `SECRET_KEY` 값을 추가합니다.

배포가 완료되면 Render에서 제공하는 `.onrender.com` 도메인을 통해 접속할 수 있습니다.
