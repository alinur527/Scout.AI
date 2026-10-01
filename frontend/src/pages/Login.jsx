import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';

const Login = ({ onLogin }) => {
    const [formData, setFormData] = useState({
        username: '',
        password: ''
    });
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            // 1. Отправляем запрос на твой локальный бэкенд FastAPI
            const response = await axios.post('http://localhost:8000/login', {
                username: formData.username,
                password: formData.password
            });

            // 2. Если логин успешен, получаем токен и данные пользователя
            const userData = response.data;

            // 3. Вызываем функцию из App.jsx для обновления глобального состояния
            onLogin(userData);

            // 4. Логика перенаправления на основе роли из БД
            // Игроки (например, полузащитники) попадают в профиль, остальные — в дашборд
            if (userData.role === 'player') {
                navigate('/profile');
            } else {
                navigate('/dashboard');
            }

        } catch (err) {
            // Обработка типичных ошибок API
            if (err.response) {
                setError(err.response.data.detail || 'Неверный логин или пароль');
            } else {
                setError('Сервер ScoutAI недоступен. Проверьте терминал с FastAPI.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container" style={{ maxWidth: '400px', marginTop: '100px' }}>
            <div className="card">
                <h2 style={{ textAlign: 'center' }}>Вход в ScoutAI</h2>
                <p style={{ textAlign: 'center', fontSize: '12px', color: '#666', marginBottom: '20px' }}>
                    Software Engineering | AITU 2026
                </p>

                {error && (
                    <div style={{ color: 'red', marginBottom: '15px', textAlign: 'center', fontSize: '14px' }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Username</label>
                        <input
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            placeholder="Введите ваш никнейм"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label>Password</label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="Введите пароль"
                            required
                        />
                    </div>

                    <button type="submit" disabled={loading}>
                        {loading ? 'Загрузка...' : 'Войти'}
                    </button>
                </form>

                <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '14px' }}>
                    Нет аккаунта? <Link to="/register" style={{ fontWeight: 'bold' }}>Зарегистрироваться</Link>
                </div>
            </div>
        </div>
    );
};

export default Login;