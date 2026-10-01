import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {authService} from "../api/auth.js";

const Register = () => {
    const [formData, setFormData] = useState({ username: '', password: '', role: 'player' });
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await authService.register(formData.username, formData.password, formData.role);
            alert("Регистрация прошла успешно! Теперь войдите в аккаунт.");
            navigate('/login');
        } catch (err) {
            alert("Ошибка регистрации: " + (err.response?.data?.detail || "Сервер недоступен"));
        }
    };
    return (
        <div className="container" style={{maxWidth: '400px'}}>
            <div className="card">
                <h2>Регистрация в ScoutAI</h2>
                <form onSubmit={handleSubmit}>
                    <label>Придумайте Username</label>
                    <input type="text" onChange={(e) => setFormData({...formData, username: e.target.value})} required />

                    <label>Придумайте Password</label>
                    <input type="password" onChange={(e) => setFormData({...formData, password: e.target.value})} required />

                    <label>Кто вы?</label>
                    <select value={formData.role} onChange={(e) => setFormData({...formData, role: e.target.value})}>
                        <option value="player">Я игрок (загружаю видео)</option>
                        <option value="scout">Я скаут (ищу таланты)</option>
                    </select>

                    <button type="submit">Зарегистрироваться</button>
                </form>

                <p style={{marginTop: '15px', fontSize: '14px', textAlign: 'center'}}>
                    Уже есть аккаунт? <Link to="/login" style={{color: 'var(--primary)', fontWeight: 'bold'}}>Войти</Link>
                </p>
            </div>
        </div>
    );
};

export default Register;