import base64
import sqlite3
from flask import Flask, render_template, session, request, redirect, url_for, flash, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

app = Flask(__name__)
application = app

app.config['SECRET_KEY'] = '6342eb430febed6def4d4063a2fa717907fb4911143de1891c59dca9e0519bd8'

app.config['DATABASE'] = r'gamemerch.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth"
login_manager.login_message = "Войдите, чтобы просматривать содержимое данной страницы"
login_manager.login_message_category = "warning"


class User(UserMixin):
    def __init__(self, user_id, login, role):
        self.id = user_id
        self.login = login
        self.role = role

    def is_admin(self):
        return self.role == 'admin'

    def is_user(self):
        return self.role == 'user'


CREATE_GAME_FIELDS = ['game_name', 'game_genre', 'game_descr']
EDIT_GAME_FIELDS = ['game_name', 'game_genre', 'game_descr']

CREATE_MERCH_FIELDS = ['game_name', 'game_genre', 'game_descr']
EDIT_MERCH_FIELDS = ['game_name', 'game_genre', 'game_descr']


@login_manager.user_loader
def load_user(user_id):
    query = "SELECT user_id, login, role FROM users WHERE user_id = ?"
    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user[0], user[1], user[2])
    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/auth', methods=["GET", "POST"])
def auth():
    if request.method == "GET":
        return render_template("auth.html")

    login_input = request.form.get("login", "")
    password = request.form.get("password", "")
    
    query = "SELECT user_id, login, role FROM users WHERE login = ? AND password = ?"
    user = None  

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(query, (login_input, password))
        user = cursor.fetchone()
        cursor.close() 
    except Exception as e:
        print(f"Ошибка при соединении с базой данных: {e}")

    if user:  
        login_user(User(user[0], user[1], user[2]))
        flash("Успешная авторизация", category="success")
        target_page = request.args.get("next", url_for("index"))
        return redirect(target_page)

    flash("Введены некорректные учётные данные пользователя", category="danger")
    return render_template("auth.html")


@app.route('/games')
def games():
    page = request.args.get('page', 1, type=int)
    per_page = 8  
    offset = (page - 1) * per_page

    query = "SELECT game_id, game_name, game_genre, game_descr FROM games LIMIT ? OFFSET ?"
    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, (per_page, offset))
    games_data = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    cursor.close()

    total_pages = (total_games + per_page - 1) // per_page

    return render_template('games.html', games=games_data, page=page, total_pages=total_pages)


@app.route('/users')
@login_required  
def users():
    print("Информация о текущем пользователе:")
    print(f"ID пользователя: {current_user.id}")
    print(f"Логин: {current_user.login}")
    print(f"Роль: {current_user.role}")
    
    user_info = {
        'user_id': current_user.id,
        'login': current_user.login,
        'role': current_user.role,
    }
    return render_template('users.html', user=user_info)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
       
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

     
        if new_password != confirm_password:
            flash("Новый пароль и подтверждение пароля не совпадают!", category="danger")
            return redirect(url_for('change_password'))

        db = get_db()
        cursor = db.cursor()
        query = "SELECT password FROM users WHERE user_id = ?"
        cursor.execute(query, (current_user.id,))
        user_record = cursor.fetchone()
        if not user_record:
            flash("Пользователь не найден!", category="danger")
            cursor.close()
            return redirect(url_for('users'))
        
        if current_password != user_record['password']:
            flash("Текущий пароль введён неверно!", category="danger")
            cursor.close()
            return redirect(url_for('change_password'))

        update_query = "UPDATE users SET password = ? WHERE user_id = ?"
        cursor.execute(update_query, (new_password, current_user.id))
        db.commit()
        cursor.close()

        flash("Пароль успешно изменён!", category="success")
        return redirect(url_for('users'))

    return render_template('change_password.html')


@app.route('/create_game', methods=["GET", "POST"])
@login_required 
def create_game():
    if request.method == "POST":
        game_id = request.form.get('game_id', type=int)
        game_name = request.form.get('game_name')
        game_genre = request.form.get('game_genre')
        game_descr = request.form.get('game_descr')

        # Обработка загрузки изображения
        game_image = request.files.get('game_image')
        base64_image = None

        if game_image:
            image_data = game_image.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')

        db = get_db()
        cursor = db.cursor()

        # Вставка данных игры в таблицу games
        query = "INSERT INTO games (game_id, game_name, game_genre, game_descr) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (game_id, game_name, game_genre, game_descr))
        db.commit()
        
        # Вставка изображения в таблицу game_images
        if base64_image:
            query_image = "INSERT INTO game_images (game_id, base_64) VALUES (?, ?)"
            cursor.execute(query_image, (game_id, base64_image))
            db.commit()

        cursor.close()

        flash("Игра успешно создана!", category="success")
        return redirect(url_for('games'))

    return render_template('create_game.html')


@app.route('/delete_game/<int:game_id>', methods=["POST"])
@login_required 
def delete_game(game_id):
    query = "DELETE FROM games WHERE game_id = ?"
    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, (game_id,))
    db.commit()
    cursor.close()

    flash("Игра успешно удалена!", category="success")
    return redirect(url_for('games'))


@app.route('/view_game/<int:game_id>')
def view_game(game_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
    game = cursor.fetchone()

    cursor.execute("SELECT base_64 FROM game_images WHERE game_id = ?", (game_id,))
    game_image = cursor.fetchone()

    cursor.execute("SELECT * FROM game_merch WHERE game_id = ?", (game_id,))
    game_content = cursor.fetchall()

    cursor.close()

    return render_template('view_game.html', game=game, game_content=game_content, game_image=game_image)


@app.route('/edit_game/<int:game_id>', methods=['GET', 'POST'])
@login_required  
def edit_game(game_id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        game_name = request.form['game_name']
        game_genre = request.form['game_genre']
        game_descr = request.form['game_descr']

        query = "UPDATE games SET game_name = ?, game_genre = ?, game_descr = ? WHERE game_id = ?"
        cursor.execute(query, (game_name, game_genre, game_descr, game_id))
        db.commit()
        cursor.close()

        flash("Игра успешно обновлена!", category="success")
        return redirect(url_for('view_game', game_id=game_id))

    query = "SELECT * FROM games WHERE game_id = ?"
    cursor.execute(query, (game_id,))
    game = cursor.fetchone()
    cursor.close()

    if game:
        return render_template('edit_game.html', game=game)
    else:
        flash("Игра не найдена!", category="danger")
        return redirect(url_for('games'))


@app.route('/add_content/<int:game_id>', methods=['GET', 'POST'])
@login_required  
def add_content(game_id):
    if request.method == 'POST':
        game_merch_name = request.form['game_merch_name']
        amount = request.form['amount']
        value = request.form['value']

        db = get_db()
        cursor = db.cursor()
        query = "INSERT INTO game_merch (game_id, game_merch_name, amount, value) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (game_id, game_merch_name, amount, value))
        db.commit()
        cursor.close()

        flash("Контент успешно добавлен!", category="success")
        return redirect(url_for('view_game', game_id=game_id))

    return render_template('add_content.html', game_id=game_id)

@app.route('/edit_content/<int:content_id>', methods=['GET', 'POST'])
@login_required  
def edit_content(content_id):
    db = get_db()
    cursor = db.cursor()

    if request.method == 'POST':
        game_merch_name = request.form['game_merch_name']
        amount = request.form['amount']
        value = request.form['value']

        query = "UPDATE game_merch SET game_merch_name = ?, amount = ?, value = ? WHERE game_merch_id = ?"
        cursor.execute(query, (game_merch_name, amount, value, content_id))
        db.commit()
        cursor.close()

        flash("Контент успешно обновлён!", category="success")
        return redirect(url_for('view_game', game_id=request.args.get('game_id')))

    query = "SELECT * FROM game_merch WHERE game_merch_id = ?"
    cursor.execute(query, (content_id,))
    content = cursor.fetchone()
    cursor.close()

    if content:
        return render_template('edit_content.html', content=content)
    else:
        flash("Контент не найден!", category="danger")
        return redirect(url_for('games'))


@app.route('/delete_content/<int:content_id>', methods=["POST"])
@login_required 
def delete_content(content_id):
    query = "DELETE FROM game_merch WHERE game_merch_id = ?"
    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, (content_id,))
    db.commit()
    cursor.close()

    flash("Контент успешно удалён!", category="success")
    return redirect(url_for('view_game', game_id=request.args.get('game_id')))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for("index"))


def get_db():
    """
    Функция для получения подключения к базе данных SQLite, сохранённой в g.
    """
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            g.db = None
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """
    Закрытие подключения к базе данных, если оно существует.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


if __name__ == '__main__':
    app.run(debug=True)
