def test_login_success(client):
    response = client.post('/auth/login', data={
        'login_id': 'admin@test.com',
        'password': 'Admin@12345'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Welcome back, Test Admin!' in response.data


def test_login_invalid_password(client):
    response = client.post('/auth/login', data={
        'login_id': 'admin@test.com',
        'password': 'WrongPassword123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid email/username or password' in response.data


def test_logout(admin_client):
    response = admin_client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'successfully logged out' in response.data


def test_unauthenticated_redirect(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']


def test_admin_access_allowed(admin_client):
    res_admin = admin_client.get('/auth/users')
    assert res_admin.status_code == 200


def test_teacher_admin_access_forbidden(teacher_client):
    res_teacher = teacher_client.get('/auth/users')
    assert res_teacher.status_code == 403
