import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import PlayerProfile from './pages/PlayerProfile'; // Страница редактирования
import PlayerView from './pages/PlayerView';       // НОВАЯ: Просмотр профиля
import VideoUpload from './pages/VideoUpload';     // НОВАЯ: Загрузка видео
import Dashboard from './pages/Dashboard';
import './styles/theme.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('scout_user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('scout_user', JSON.stringify(userData));
    localStorage.setItem('scout_token', userData.access_token);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('scout_user');
    localStorage.removeItem('scout_token');
  };

  if (loading) return <div className="loader">Загрузка ScoutAI...</div>;

  return (
      <Router>
        {user && (
            <nav className="navbar">
              <div className="nav-content">
                <Link to="/" className="logo">ScoutAI</Link>
                <div className="nav-links">
                  {/* Ссылки для Игрока */}
                  {user.role === 'player' && (
                      <>
                        <Link to="/profile/view">Мой Профиль</Link>
                        <Link to="/profile/edit">Редактировать</Link>
                        <Link to="/upload">Анализ Видео</Link>
                      </>
                  )}
                  {/* Ссылки для Скаута */}
                  {(user.role === 'scout' || user.role === 'admin') && (
                      <Link to="/dashboard">Поиск Игроков</Link>
                  )}
                  <button onClick={handleLogout} className="logout-btn">Выйти ({user.username})</button>
                </div>
              </div>
            </nav>
        )}

        <Routes>
          <Route path="/login" element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/" />} />
          <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />

          {/* Главная перенаправляет в зависимости от роли */}
          <Route path="/" element={
            user ? (
                user.role === 'player' ? <Navigate to="/profile/view" /> : <Navigate to="/dashboard" />
            ) : <Navigate to="/login" />
          } />

          {/* Маршруты Игрока */}
          <Route path="/profile/view" element={user?.role === 'player' ? <PlayerView /> : <Navigate to="/login" />} />
          <Route path="/profile/edit" element={user?.role === 'player' ? <PlayerProfile user={user} /> : <Navigate to="/login" />} />
          <Route path="/upload" element={user?.role === 'player' ? <VideoUpload /> : <Navigate to="/login" />} />

          {/* Маршруты Скаута */}
          <Route path="/dashboard" element={user?.role === 'scout' || user?.role === 'admin' ? <Dashboard user={user} /> : <Navigate to="/login" />} />
        </Routes>
      </Router>
  );
}

export default App;