import React, { useState, useEffect } from 'react';
import axios from 'axios';

const PlayerView = () => {
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const token = localStorage.getItem('scout_token');
                const response = await axios.get('http://localhost:8000/profile/me', {
                    headers: { Authorization: `Bearer ${token}` }
                });
                console.log("Данные из БД:", response.data);
                setProfile(response.data);
            } catch (err) {
                console.error("Ошибка запроса:", err.response);
            } finally {
                setLoading(false);
            }
        };
        fetchProfile();
    }, []);

    if (loading) return <div>Загрузка данных...</div>;
    if (!profile) return <div>Профиль не найден. Заполните данные во вкладке редактирования.</div>;

    return (
        <div className="container">
            <div className="card profile-card">
                <div className="profile-header">
                    <h2>Профиль Атлета: {profile.username}</h2>
                    <span className="badge">{profile.position || "Midfielder"}</span>
                </div>
                <hr />
                <div className="profile-stats">
                    <div className="stat-item"><strong>Рост:</strong> {profile.height} см</div>
                    <div className="stat-item"><strong>Вес:</strong> {profile.weight} кг</div>
                    <div className="stat-item"><strong>Национальность:</strong> {profile.nationality}</div>
                </div>
                <div className="profile-bio">
                    <h4>О себе</h4>
                    <p>{profile.bio || "Информация не заполнена"}</p>
                </div>
            </div>
        </div>
    );
};

export default PlayerView;