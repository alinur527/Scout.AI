import React, { useState } from 'react';
import axios from 'axios';

const PlayerProfile = ({ user }) => {
    const [profile, setProfile] = useState({
        height: '',
        weight: '',
        nationality: '',
        position: 'Midfielder', // Твоя позиция по умолчанию
        bio: ''
    });

    const handleSave = async () => {
        // Убедись, что ключ совпадает с тем, что в Login.jsx (например, 'scout_token')
        const token = localStorage.getItem('scout_token');

        // Дебаг: посмотри в консоль (F12), что именно отправляется
        console.log("Отправляемый токен:", token);

        if (!token) {
            alert("Вы не авторизованы. Пожалуйста, войдите в систему заново.");
            return;
        }

        try {
            const response = await axios.put('http://localhost:8000/profile/me', profile, {
                headers: {
                    // ВАЖНО: Пробел после Bearer обязателен!
                    Authorization: `Bearer ${token}`
                }
            });
            alert("Профиль успешно обновлен в PostgreSQL!");
        } catch (err) {
            if (err.response?.status === 401) {
                alert("Сессия истекла. Войдите снова.");
            } else {
                alert("Ошибка при сохранении данных.");
            }
        }
    };

    return (
        <div className="container">
            <div className="card">
                <h2>My Athletic Profile</h2>
                <div className="grid-form">
                    <input
                        type="number" placeholder="Height (cm)"
                        onChange={(e) => setProfile({...profile, height: e.target.value})}
                    />
                    <input
                        type="number" placeholder="Weight (kg)"
                        onChange={(e) => setProfile({...profile, weight: e.target.value})}
                    />
                </div>
                <input
                    type="text" placeholder="Nationality"
                    onChange={(e) => setProfile({...profile, nationality: e.target.value})}
                />
                <input
                    type="text" placeholder="Position (e.g. Midfielder)"
                    value={profile.position}
                    onChange={(e) => setProfile({...profile, position: e.target.value})}
                />
                <textarea
                    placeholder="About Me (Bio)"
                    onChange={(e) => setProfile({...profile, bio: e.target.value})}
                ></textarea>

                <button onClick={handleSave} className="btn-primary">Save Changes</button>
            </div>
        </div>
    );
};

export default PlayerProfile;