import pytest
from webgame.app import app

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client
# 1
def test_auth_success(client):
    response = client.post('/auth', data={
        'login': 'admin',
        'password': 'admin123'
    }, follow_redirects=True)
    assert 'Успешная авторизация'.encode('utf-8') in response.data
# 2
def test_auth_failure(client):
    response = client.post('/auth', data={
        'login': 'wrong_user',
        'password': 'wrong_password'
    }, follow_redirects=True)
    assert 'Введены некорректные учётные данные'.encode('utf-8') in response.data
# 3
def test_create_game_with_id_1(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    
    response = client.post('/create_game', data={
        'game_id': 1,
        'game_name': 'Test Game',
        'game_genre': 'Adventure',
        'game_descr': 'Test description for game'
    }, follow_redirects=True)
    
    assert 'Игра успешно создана'.encode('utf-8') in response.data

    response_view = client.get('/view_game/1')
    assert response_view.status_code == 200
    assert b'Test Game' in response_view.data

# 4. Тест просмотра конкретной игры
def test_view_game(client):
    response = client.get('/view_game/1')
    assert response.status_code == 200
    assert b'<h1>' in response.data  # Проверка наличия заголовка

# 5. Тест доступа к защищённой странице /users без авторизации
def test_users_redirect_if_not_logged_in(client):
    response = client.get('/users', follow_redirects=True)
    assert 'Войдите, чтобы просматривать содержимое данной страницы'.encode('utf-8') in response.data

# 6. Тест доступа к защищённой странице /users с авторизацией
def test_users_access_with_login(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.get('/users')
    assert response.status_code == 200
    assert 'ID пользователя'.encode('utf-8') in response.data

# 7. Тест добавления нового контента (добавление товара)
def test_add_content(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.post('/add_content/1', data={
        'game_merch_name': 'Test Merch',
        'amount': 10,
        'value': 100
    }, follow_redirects=True)
    assert 'Контент успешно добавлен'.encode('utf-8') in response.data

# 8. Тест редактирования игры (смена названия на "testname2")
def test_edit_game_name(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.post('/edit_game/3', data={
        'game_name': 'testname2',
        'game_genre': 'Adventure',
        'game_descr': 'Updated description'
    }, follow_redirects=True)
    assert 'Игра успешно обновлена' in response.data.decode('utf-8')


# 9. Тест удаления игры
def test_delete_game(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.post('/delete_game/1', follow_redirects=True)
    assert 'Игра успешно удалена' in response.data.decode('utf-8')

# 10. Тест выхода из системы
def test_logout(client):
    client.post('/auth', data={'login': 'admin', 'password': 'admin123'})
    response = client.get('/logout', follow_redirects=True)
    assert b'index.html' in response.data or response.status_code == 200

# 11
def test_get_games_list(client):
    response = client.get('/games?page=1')
    assert response.status_code == 200

