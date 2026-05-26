import os
from datetime import datetime
from functools import wraps
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-for-dev')

# 데이터베이스 커넥션 풀 초기화
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, os.getenv('DATABASE_URL'))
except Exception as e:
    print(f"Error connecting to database: {e}")
    db_pool = None

def execute_query(query, params=(), fetchall=False, fetchone=False, commit=False):
    """안전한 데이터베이스 쿼리 실행 헬퍼 함수"""
    conn = db_pool.getconn() if db_pool else psycopg2.connect(os.getenv('DATABASE_URL'))
    result = None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
            if fetchall:
                result = cur.fetchall()
            elif fetchone:
                result = cur.fetchone()
    except Exception as e:
        if commit:
            conn.rollback()
        raise e
    finally:
        if db_pool:
            db_pool.putconn(conn)
        else:
            conn.close()
    return result

@app.context_processor
def inject_user():
    """모든 템플릿에서 현재 로그인된 사용자 정보에 접근할 수 있도록 주입"""
    return dict(
        current_user_id=session.get('user_id'),
        current_user_nickname=session.get('nickname'),
        current_user_role=session.get('role')
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'db_id' not in session:
            flash('로그인이 필요한 서비스입니다.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'ADMIN':
            flash('관리자 권한이 필요합니다.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- Routes ---------------- #

@app.route('/')
def index():
    return redirect(url_for('post_list'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        nickname = request.form.get('nickname')
        
        user = execute_query("SELECT id FROM users WHERE user_id = %s", (user_id,), fetchone=True)
        if user:
            flash('이미 존재하는 아이디입니다.', 'danger')
        else:
            pw_hash = generate_password_hash(password)
            execute_query(
                "INSERT INTO users (user_id, password_hash, nickname) VALUES (%s, %s, %s)",
                (user_id, pw_hash, nickname), commit=True
            )
            flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        user = execute_query("SELECT * FROM users WHERE user_id = %s", (user_id,), fetchone=True)
        
        if user and check_password_hash(user['password_hash'], password):
            session['db_id'] = user['id']
            session['user_id'] = user['user_id']
            session['nickname'] = user['nickname']
            session['role'] = user['role']
            flash(f'{user["nickname"]}님 환영합니다.', 'success')
            return redirect(url_for('post_list'))
        else:
            flash('아이디 또는 비밀번호가 일치하지 않습니다.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('post_list'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        new_nickname = request.form.get('nickname')
        if new_nickname:
            execute_query("UPDATE users SET nickname = %s WHERE id = %s", (new_nickname, session['db_id']), commit=True)
            session['nickname'] = new_nickname
            flash('닉네임이 수정되었습니다.', 'success')
    return render_template('account.html')

@app.route('/account/delete', methods=['POST'])
@login_required
def account_delete():
    execute_query("DELETE FROM users WHERE id = %s", (session['db_id'],), commit=True)
    session.clear()
    flash('계정이 탈퇴되었습니다. 이용해 주셔서 감사합니다.', 'info')
    return redirect(url_for('index'))

@app.route('/posts')
def post_list():
    tab_id = request.args.get('tab_id', type=int)
    search_query = request.args.get('search', '')
    
    tabs = execute_query("SELECT * FROM board_tabs ORDER BY id ASC", fetchall=True)
    
    query = """
        SELECT p.*, u.nickname as author, t.name as tab_name,
               (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) as comment_count,
               (SELECT COUNT(*) FROM reactions r WHERE r.post_id = p.id AND r.reaction_type = 'LIKE') as like_count,
               (SELECT COUNT(*) FROM reactions r WHERE r.post_id = p.id AND r.reaction_type = 'DISLIKE') as dislike_count
        FROM posts p
        LEFT JOIN users u ON p.user_id = u.id
        LEFT JOIN board_tabs t ON p.tab_id = t.id
        WHERE 1=1
    """
    params = []
    
    if tab_id:
        query += " AND p.tab_id = %s"
        params.append(tab_id)
        
    if search_query:
        query += " AND (p.title ILIKE %s OR p.content ILIKE %s)"
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")
        
    query += " ORDER BY p.created_at DESC"
    
    posts = execute_query(query, tuple(params), fetchall=True)
    
    return render_template('posts.html', posts=posts, tabs=tabs, current_tab=tab_id, search_query=search_query)

@app.route('/posts/new', methods=['GET', 'POST'])
@login_required
def post_create():
    tabs = execute_query("SELECT * FROM board_tabs ORDER BY id ASC", fetchall=True)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        tab_id = request.form.get('tab_id', type=int)
        
        execute_query(
            "INSERT INTO posts (user_id, tab_id, title, content) VALUES (%s, %s, %s, %s)",
            (session['db_id'], tab_id, title, content), commit=True
        )
        flash('게시글이 작성되었습니다.', 'success')
        return redirect(url_for('post_list'))
        
    return render_template('post_form.html', tabs=tabs, post=None)

@app.route('/posts/<int:post_id>')
def post_detail(post_id):
    post = execute_query("""
        SELECT p.*, u.nickname as author, t.name as tab_name,
               (SELECT COUNT(*) FROM reactions r WHERE r.post_id = p.id AND r.reaction_type = 'LIKE') as like_count,
               (SELECT COUNT(*) FROM reactions r WHERE r.post_id = p.id AND r.reaction_type = 'DISLIKE') as dislike_count
        FROM posts p
        LEFT JOIN users u ON p.user_id = u.id
        LEFT JOIN board_tabs t ON p.tab_id = t.id
        WHERE p.id = %s
    """, (post_id,), fetchone=True)
    
    if not post:
        abort(404)
        
    comments = execute_query("""
        SELECT c.*, u.nickname as author 
        FROM comments c 
        LEFT JOIN users u ON c.user_id = u.id 
        WHERE c.post_id = %s 
        ORDER BY COALESCE(c.parent_id, c.id) ASC, c.created_at ASC
    """, (post_id,), fetchall=True)
    
    # 계층형 댓글 트리 생성
    comment_tree = []
    comment_map = {}
    
    for c in comments:
        c['replies'] = []
        comment_map[c['id']] = c
        if c['parent_id'] is None:
            comment_tree.append(c)
            
    for c in comments:
        if c['parent_id'] is not None and c['parent_id'] in comment_map:
            comment_map[c['parent_id']]['replies'].append(c)
            
    # 현재 로그인된 유저의 좋아요/싫어요 반응 확인
    user_reaction = None
    if 'db_id' in session:
        ur = execute_query("SELECT reaction_type FROM reactions WHERE post_id = %s AND user_id = %s", 
                           (post_id, session['db_id']), fetchone=True)
        if ur:
            user_reaction = ur['reaction_type']

    return render_template('post_detail.html', post=post, comments=comment_tree, user_reaction=user_reaction)

@app.route('/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def post_edit(post_id):
    post = execute_query("SELECT * FROM posts WHERE id = %s", (post_id,), fetchone=True)
    if not post:
        abort(404)
        
    if post['user_id'] != session['db_id'] and session.get('role') != 'ADMIN':
        flash('권한이 없습니다.', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))
        
    tabs = execute_query("SELECT * FROM board_tabs ORDER BY id ASC", fetchall=True)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        tab_id = request.form.get('tab_id', type=int)
        
        execute_query(
            "UPDATE posts SET title = %s, content = %s, tab_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (title, content, tab_id, post_id), commit=True
        )
        flash('게시글이 수정되었습니다.', 'success')
        return redirect(url_for('post_detail', post_id=post_id))
        
    return render_template('post_form.html', tabs=tabs, post=post)

@app.route('/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def post_delete(post_id):
    post = execute_query("SELECT user_id FROM posts WHERE id = %s", (post_id,), fetchone=True)
    if not post:
        abort(404)
        
    if post['user_id'] != session['db_id'] and session.get('role') != 'ADMIN':
        flash('권한이 없습니다.', 'danger')
        return redirect(url_for('post_detail', post_id=post_id))
        
    execute_query("DELETE FROM posts WHERE id = %s", (post_id,), commit=True)
    flash('게시글이 삭제되었습니다.', 'success')
    return redirect(url_for('post_list'))

@app.route('/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_create(post_id):
    content = request.form.get('content')
    parent_id = request.form.get('parent_id')
    
    if not parent_id:
        parent_id = None
        
    execute_query(
        "INSERT INTO comments (post_id, user_id, parent_id, content) VALUES (%s, %s, %s, %s)",
        (post_id, session['db_id'], parent_id, content), commit=True
    )
    flash('댓글이 작성되었습니다.', 'success')
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def comment_delete(comment_id):
    comment = execute_query("SELECT user_id, post_id FROM comments WHERE id = %s", (comment_id,), fetchone=True)
    if not comment:
        abort(404)
        
    if comment['user_id'] != session['db_id'] and session.get('role') != 'ADMIN':
        flash('권한이 없습니다.', 'danger')
        return redirect(url_for('post_detail', post_id=comment['post_id']))
        
    execute_query("DELETE FROM comments WHERE id = %s", (comment_id,), commit=True)
    flash('댓글이 삭제되었습니다.', 'success')
    return redirect(url_for('post_detail', post_id=comment['post_id']))

@app.route('/posts/<int:post_id>/react', methods=['POST'])
@login_required
def post_react(post_id):
    data = request.get_json()
    reaction_type = data.get('type')
    
    if reaction_type not in ('LIKE', 'DISLIKE'):
        return jsonify({'error': '잘못된 반응 타입입니다.'}), 400
        
    existing = execute_query(
        "SELECT id, reaction_type FROM reactions WHERE post_id = %s AND user_id = %s",
        (post_id, session['db_id']), fetchone=True
    )
    
    if existing:
        if existing['reaction_type'] == reaction_type:
            # 취소
            execute_query("DELETE FROM reactions WHERE id = %s", (existing['id'],), commit=True)
            return jsonify({'message': 'Reaction removed'})
        else:
            # 변경
            execute_query(
                "UPDATE reactions SET reaction_type = %s WHERE id = %s",
                (reaction_type, existing['id']), commit=True
            )
            return jsonify({'message': 'Reaction updated'})
    else:
        # 새로 추가
        execute_query(
            "INSERT INTO reactions (post_id, user_id, reaction_type) VALUES (%s, %s, %s)",
            (post_id, session['db_id'], reaction_type), commit=True
        )
        return jsonify({'message': 'Reaction created'})

@app.route('/admin/tabs', methods=['GET', 'POST'])
@admin_required
def admin_tabs():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            execute_query("INSERT INTO board_tabs (name) VALUES (%s)", (name,), commit=True)
            flash('새 탭이 추가되었습니다.', 'success')
        return redirect(url_for('admin_tabs'))
        
    tabs = execute_query("SELECT * FROM board_tabs ORDER BY id ASC", fetchall=True)
    return render_template('admin_tabs.html', tabs=tabs)

@app.route('/admin/tabs/<int:tab_id>/edit', methods=['POST'])
@admin_required
def admin_tab_edit(tab_id):
    name = request.form.get('name')
    if name:
        execute_query("UPDATE board_tabs SET name = %s WHERE id = %s", (name, tab_id), commit=True)
        flash('탭 이름이 수정되었습니다.', 'success')
    return redirect(url_for('admin_tabs'))

@app.route('/admin/tabs/<int:tab_id>/delete', methods=['POST'])
@admin_required
def admin_tab_delete(tab_id):
    # DB에서 ON DELETE SET NULL 처리되므로 게시글의 tab_id는 NULL(분류 안됨) 상태로 안전하게 보존됨
    execute_query("DELETE FROM board_tabs WHERE id = %s", (tab_id,), commit=True)
    flash('탭이 삭제되었습니다. 관련 게시글은 이제 "기본 탭(분류 안됨)"으로 이동합니다.', 'success')
    return redirect(url_for('admin_tabs'))

if __name__ == '__main__':
    app.run(debug=True, port=8080)
