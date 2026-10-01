import axios from 'axios';

const API_URL = "http://127.0.0.1:8000";

export const registerPlayer = async (username, password) => {
    return await axios.post(`${API_URL}/register`, { username, password, role: 'player' });
};

export const updateProfile = async (profileData) => {
    // Здесь мы отправляем данные роста/веса в базу
    return await axios.put(`${API_URL}/profile/me`, profileData);
};