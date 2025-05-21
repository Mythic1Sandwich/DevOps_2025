import pytest
import sqlite3
from webgame.app import app, get_db

class GameObject:
    def __init__(self, data):
        if isinstance(data, tuple):
            self.game_id = data[0]
            self.game_name = data[1]
            self.game_genre = data[2]
            self.game_descr = data[3]
        elif isinstance(data, dict):
            for key, value in data.items():
                setattr(self, key, value)

def init_db():
    db = sqlite3.connect(':memory:')
    cursor = db.cursor()
    cursor.executescript('''
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_name TEXT NOT NULL,
            game_genre TEXT NOT NULL,
            game_descr TEXT NOT NULL
        );
        CREATE TABLE game_merch (
            game_merch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            game_merch_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            value INTEGER NOT NULL,
            FOREIGN KEY (game_id) REFERENCES games (game_id)
        );
        CREATE TABLE game_images (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            base_64 TEXT,
            FOREIGN KEY (game_id) REFERENCES games (game_id)
        );
    ''')

    cursor.execute("INSERT INTO users (login, password, role) VALUES ('admin', 'admin123', 'admin')")
    cursor.execute("INSERT INTO games (game_name, game_genre, game_descr) VALUES ('Test Game', 'Adventure', 'Test description')")
    db.commit()
    return db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db = init_db()
        app.config['DATABASE'] = ':memory:'
        app.config['DB_CONN'] = db

        original_get_db = get_db
        
        def get_test_db():
            return db
        
        import webgame.app
        webgame.app.get_db = get_test_db

        with app.test_client() as client:
            yield client

        webgame.app.get_db = original_get_db
        db.close()

# Тесты
def test_auth_success(client):
    response = client.post('/auth', data={
        'login': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)
    assert 'Успешная авторизация'.encode('utf-8') in response.data

def test_auth_failure(client):
    response = client.post('/auth', data={
        'login': 'wrong_user',
        'password': 'wrong_password'
    }, follow_redirects=True)
    assert 'Введены некорректные учётные данные'.encode('utf-8') in response.data

def test_view_game(client):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO games (game_name, game_genre, game_descr) VALUES ('View Test', 'RPG', 'Desc')")
    game_id = cursor.lastrowid
    db.commit()
    cursor.close()

    response = client.get(f'/view_game/{game_id}')
    assert response.status_code == 200
    assert b'View Test' in response.data

def test_users_redirect_if_not_logged_in(client):
    response = client.get('/users', follow_redirects=True)
    assert 'Войдите, чтобы просматривать содержимое данной страницы'.encode('utf-8') in response.data

def test_users_access_with_login(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.get('/users')
    assert response.status_code == 200
    assert 'ID пользователя'.encode('utf-8') in response.data

def test_add_content(client):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO games (game_name, game_genre, game_descr) VALUES ('Content Game', 'Action', 'Desc')")
    game_id = cursor.lastrowid
    db.commit()
    cursor.close()

    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.post(f'/add_content/{game_id}', data={
        'game_merch_name': 'Test Item',
        'amount': '5',
        'value': '100'
    }, follow_redirects=True)
    assert 'Контент успешно добавлен'.encode('utf-8') in response.data

def test_create_game(client):

    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})

    response = client.post('/create_game', data={
        'game_name': 'New Test Game',
        'game_genre': 'Puzzle',
        'game_descr': 'A fun puzzle game.'
    }, follow_redirects=True)

    assert 'Игра успешно создана!'.encode('utf-8') in response.data

    response = client.get('/games')
    assert b'New Test Game' in response.data

def test_delete_game(client):

    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO games (game_name, game_genre, game_descr) VALUES ('Game to Delete', 'Action', 'This game will be deleted')")
    game_id = cursor.lastrowid
    db.commit()
    cursor.close()

  
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})

  
    response = client.post(f'/delete_game/{game_id}', follow_redirects=True)

    assert 'Игра успешно удалена!'.encode('utf-8') in response.data

    response = client.get('/games')
    assert b'Game to Delete' not in response.data

def test_logout(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
