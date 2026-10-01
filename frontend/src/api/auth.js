import axios from 'axios';

const API_URL = "http://localhost:8000";

export const authService = {
    // Регистрация
    register: async (username, password, role) => {
        const response = await axios.post(`${API_URL}/register`, {
            username,
            password,
            role
        });
        return response.data;
    },

    // Логин
    login: async (username, password) => {
        const response = await axios.post(`${API_URL}/login`, {
            username,
            password
        });
        return response.data; // Тут придет токен и роль
    }
};