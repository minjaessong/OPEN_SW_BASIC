-- 기본 탭 데이터 추가
INSERT INTO board_tabs (name) VALUES 
('자유'), 
('질문'), 
('정보'), 
('홍보');

-- 유의: 관리자 계정 추가는 setup_db.py 스크립트에서 비밀번호 해싱과 함께 처리됩니다.
-- SQL만으로 추가하고자 할 때는 아래와 같이 사용할 수 있으나 해시된 비밀번호 값이 필요합니다.
-- INSERT INTO users (user_id, password_hash, nickname, role) 
-- VALUES ('admin', '해시값', '관리자', 'ADMIN');
