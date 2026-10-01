import React, { useState } from 'react';
import axios from 'axios';

const VideoUpload = () => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState('');
    // Добавляем состояние для ID задачи
    const [taskId, setTaskId] = useState(null);

    const handleFileChange = (e) => {
        setFile(e.target.files[0]);
    };

    const handleUpload = async () => {
        if (!file) return alert("Выберите файл!");

        const formData = new FormData();
        // ВАЖНО: имя поля 'video' должно совпадать с бэкендом
        formData.append('video', file);

        setUploading(true);
        setMessage("Загрузка и запуск анализа...");
        setTaskId(null);

        try {
            const token = localStorage.getItem('scout_token');
            // ВАЖНО: Новый адрес эндпоинта
            const response = await axios.post('http://localhost:8000/upload-video-and-analyze', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'Authorization': `Bearer ${token}`
                }
            });

            setMessage(response.data.message);
            setTaskId(response.data.file_id); // Сохраняем ID задачи
            alert(`Анализ запущен! ID задачи: ${response.data.file_id}. Скоро можно будет проверить результат.`);

        } catch (err) {
            console.error(err);
            if (err.response?.status === 404) {
                setMessage("Ошибка 404: Эндпоинт не найден. Проверь адрес в axios.post");
            } else if (err.response?.status === 422) {
                setMessage("Ошибка валидации данных. Возможно, неверное имя поля в FormData.");
            } else {
                setMessage("Ошибка при загрузке: " + (err.response?.data?.detail || err.message));
            }
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="container">
            <div className="card">
                <h3>Анализ матча нейросетью</h3>
                <input type="file" accept="video/*" onChange={handleFileChange} className="file-input" />

                <button onClick={handleUpload} disabled={uploading || !file} className="btn-primary">
                    {uploading ? "Загрузка и старт..." : "Начать анализ"}
                </button>

                {message && <p className="status-msg" style={{marginTop: '20px', fontWeight: 'bold', color: 'var(--primary)'}}>{message}</p>}

                {/* В будущем здесь можно добавить кнопку "Проверить статус" используя taskId */}
                {taskId && <p style={{fontSize: '12px', color: 'gray'}}>Task ID: {taskId}</p>}
            </div>
        </div>
    );
};

export default VideoUpload;