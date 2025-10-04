#!/usr/bin/env python3
"""Простая админ-панель с единым источником данных в реальном времени."""

import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

# Загружаем переменные окружения
load_dotenv()

# Импортируем единый менеджер состояния
from realtime_state import get_state_manager

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('ADMIN_SECRET_KEY', 'dev-secret-key')

# Получаем глобальный менеджер состояния
state_manager = get_state_manager()

print("[SimpleAdmin] Initialized with realtime state manager")

# Простой HTML шаблон
SIMPLE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sfedunet 12 Bot - Realtime Admin</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .stat { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .stat-number { font-size: 24px; font-weight: bold; color: #007bff; }
        .stat-label { color: #6c757d; margin-top: 5px; }
        .user { padding: 10px; border-bottom: 1px solid #eee; }
        .user:last-child { border-bottom: none; }
        .progress-bar { width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s; }
        .status-badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px; }
        .badge-pending { background: #fff3cd; color: #856404; }
        .badge-verified { background: #d4edda; color: #155724; }
        .badge-qualified { background: #d1ecf1; color: #0c5460; }
        .auto-refresh { margin: 20px 0; text-align: center; }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #0056b3; }
        .btn-danger { background: #dc3545; }
        .btn-danger:hover { background: #c82333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Sfedunet 12 Bot - Realtime Admin</h1>

        <div class="auto-refresh">
            <button class="btn" onclick="toggleAutoRefresh()">🔄 Auto Refresh: <span id="refresh-status">ON</span></button>
            <button class="btn" onclick="refreshNow()">↻ Refresh Now</button>
            <button class="btn" onclick="forceRefresh()">🔃 Force Refresh</button>
            <button class="btn btn-danger" onclick="clearAll()">🗑️ Clear All Data</button>
            <span id="last-update">Загрузка...</span>
        </div>

        <div class="card">
            <h2>📊 Статистика в реальном времени</h2>
            <div class="stats" id="stats-container">
                <!-- Статистика будет загружена динамически -->
            </div>
        </div>

        <div class="card">
            <h2>👥 Пользователи</h2>
            <div id="users-container">
                <!-- Пользователи будут загружены динамически -->
            </div>
        </div>

        <div class="card">
            <h2>🎯 Управление стендами</h2>
            <div style="margin-bottom: 20px;">
                <button class="btn" onclick="showAddStandForm()">➕ Добавить стенд</button>
                <button class="btn" onclick="reloadConfig()">🔄 Перезагрузить конфиг</button>
            </div>
            <div id="stands-container">
                <!-- Стенды будут загружены динамически -->
            </div>
        </div>

        <div class="card" id="edit-stand-form" style="display: none;">
            <h2>✏️ Редактирование стенда</h2>
            <form id="stand-form">
                <div style="margin: 10px 0;">
                    <label>ID стенда:</label>
                    <input type="text" id="stand-id" required style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Название:</label>
                    <input type="text" id="stand-title" required style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Описание:</label>
                    <input type="text" id="stand-description" required style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Emoji:</label>
                    <input type="text" id="stand-emoji" required style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Цвет:</label>
                    <input type="text" id="stand-color" required style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <div style="margin: 20px 0;">
                    <h3>Вопросы:</h3>
                    <div id="questions-container"></div>
                    <button type="button" class="btn" onclick="addQuestion()">➕ Добавить вопрос</button>
                </div>
                <div style="margin: 20px 0;">
                    <button type="button" class="btn" onclick="saveStand()">💾 Сохранить</button>
                    <button type="button" class="btn btn-danger" onclick="cancelEdit()">❌ Отмена</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let autoRefreshEnabled = true;
        let autoRefreshInterval;

        function updateLastUpdate() {
            document.getElementById('last-update').textContent = 'Обновлено: ' + new Date().toLocaleTimeString();
        }

        function toggleAutoRefresh() {
            autoRefreshEnabled = !autoRefreshEnabled;
            const status = document.getElementById('refresh-status');
            status.textContent = autoRefreshEnabled ? 'ON' : 'OFF';

            if (autoRefreshEnabled) {
                startAutoRefresh();
            } else {
                clearInterval(autoRefreshInterval);
            }
        }

        function startAutoRefresh() {
            autoRefreshInterval = setInterval(refreshNow, 1000); // Обновление каждую секунду для более быстрого отклика
        }

        async function refreshNow() {
            try {
                await Promise.all([loadStats(), loadUsers(), loadStands()]);
                updateLastUpdate();
            } catch (error) {
                console.error('Refresh error:', error);
            }
        }

        async function forceRefresh() {
            try {
                console.log('Force refreshing state...');
                const response = await fetch('/api/realtime/refresh', { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    console.log('Force refresh successful:', result.message);
                    await refreshNow();
                } else {
                    console.error('Force refresh failed:', result.error);
                    alert('Ошибка принудительного обновления: ' + result.error);
                }
            } catch (error) {
                console.error('Force refresh error:', error);
                alert('Ошибка: ' + error.message);
            }
        }

        async function loadStats() {
            try {
                const response = await fetch('/api/realtime/stats');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const stats = await response.json();

                document.getElementById('stats-container').innerHTML = `
                    <div class="stat">
                        <div class="stat-number">${stats.total_users || 0}</div>
                        <div class="stat-label">Всего пользователей</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${stats.average_progress || 0}%</div>
                        <div class="stat-label">Средний прогресс</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${stats.completed_users || 0}</div>
                        <div class="stat-label">Завершили все стенды</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${stats.qualified_users || 0}</div>
                        <div class="stat-label">Квалифицированы</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${stats.vk_verified_users || 0}</div>
                        <div class="stat-label">VK верифицированы</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">${stats.users_with_pending_questions || 0}</div>
                        <div class="stat-label">С активными вопросами</div>
                    </div>
                `;
                console.log('Stats loaded successfully:', stats);
            } catch (error) {
                console.error('Error loading stats:', error);
                document.getElementById('stats-container').innerHTML = `<p style="color: red;">Ошибка загрузки статистики: ${error.message}</p>`;
            }
        }

        async function loadUsers() {
            try {
                const response = await fetch('/api/realtime/users');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                const users = await response.json();

                const usersHtml = users.map(user => {
                    const progressPercent = user.progress_percent || 0;
                    let badges = '';

                    if (user.qualified) badges += '<span class="status-badge badge-qualified">🏆 Квалифицирован</span>';
                    else if (user.vk_verified) badges += '<span class="status-badge badge-verified">✅ VK подтвержден</span>';

                    if (user.has_pending_question) badges += '<span class="status-badge badge-pending">❓ Активный вопрос</span>';

                    return `
                        <div class="user">
                            <div><strong>${user.full_name || 'Без имени'}</strong> (ID: ${user.user_id}) ${badges}</div>
                            <div>Прогресс: ${user.completed_stands}/${user.total_stands} стендов</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${progressPercent}%"></div>
                            </div>
                            <small>Обновлен: ${new Date(user.updated_at).toLocaleString()}</small>
                        </div>
                    `;
                }).join('');

                document.getElementById('users-container').innerHTML = usersHtml || '<p>Нет пользователей</p>';
                console.log(`Loaded ${users.length} users successfully`);
            } catch (error) {
                console.error('Error loading users:', error);
                document.getElementById('users-container').innerHTML = `<p style="color: red;">Ошибка загрузки пользователей: ${error.message}</p>`;
            }
        }

        async function loadStands() {
            try {
                console.log('Loading stands...');
                const response = await fetch('/api/realtime/stands');

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const stands = await response.json();
                console.log('Loaded stands:', stands);

                if (!Array.isArray(stands)) {
                    throw new Error('Invalid stands data received');
                }

                const standsHtml = stands.map((stand, index) => {
                    if (!stand.id) {
                        console.warn('Stand without ID found:', stand);
                        return '';
                    }

                    return `
                        <div style="padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${stand.emoji || '❓'} ${stand.title || 'Без названия'}</strong> (ID: ${stand.id})
                                <br><small>${stand.description || 'Без описания'}</small>
                                <br><small>Вопросов: ${stand.questions ? stand.questions.length : 0}</small>
                            </div>
                            <div>
                                <button class="btn" onclick="editStand('${stand.id}')" style="margin: 2px;">✏️ Изменить</button>
                                <button class="btn btn-danger" onclick="deleteStand('${stand.id}')" style="margin: 2px;">🗑️ Удалить</button>
                            </div>
                        </div>
                    `;
                }).filter(html => html).join('');

                document.getElementById('stands-container').innerHTML = standsHtml || '<p>Нет стендов</p>';
                console.log('Stands loaded successfully');
            } catch (error) {
                console.error('Error loading stands:', error);
                document.getElementById('stands-container').innerHTML = `<p style="color: red;">Ошибка загрузки стендов: ${error.message}</p>`;
            }
        }

        let editingStandId = null;
        let currentStands = [];

        function showAddStandForm() {
            editingStandId = null;
            document.getElementById('edit-stand-form').style.display = 'block';
            clearForm();
            addQuestion(); // Добавляем один вопрос по умолчанию
        }

        async function editStand(standId) {
            try {
                console.log('Editing stand:', standId);
                const response = await fetch('/api/realtime/stands');

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                currentStands = await response.json();
                console.log('Loaded stands:', currentStands);

                const stand = currentStands.find(s => s.id === standId);
                if (!stand) {
                    alert('Стенд не найден!');
                    return;
                }

                editingStandId = standId;
                document.getElementById('edit-stand-form').style.display = 'block';

                // Заполняем форму
                document.getElementById('stand-id').value = stand.id;
                document.getElementById('stand-title').value = stand.title || '';
                document.getElementById('stand-description').value = stand.description || '';
                document.getElementById('stand-emoji').value = stand.emoji || '';
                document.getElementById('stand-color').value = stand.color || '';

                // Загружаем вопросы
                clearQuestions();
                if (stand.questions && stand.questions.length > 0) {
                    stand.questions.forEach(question => {
                        addQuestion(question);
                    });
                } else {
                    addQuestion(); // Добавляем пустой вопрос
                }

                console.log('Stand form filled successfully');
            } catch (error) {
                console.error('Error editing stand:', error);
                alert('Ошибка при загрузке стенда: ' + error.message);
            }
        }

        function clearForm() {
            document.getElementById('stand-id').value = '';
            document.getElementById('stand-title').value = '';
            document.getElementById('stand-description').value = '';
            document.getElementById('stand-emoji').value = '';
            document.getElementById('stand-color').value = '';
            clearQuestions();
        }

        function clearQuestions() {
            document.getElementById('questions-container').innerHTML = '';
        }

        function addQuestion(questionData = null) {
            const container = document.getElementById('questions-container');
            const questionIndex = container.children.length;

            const questionDiv = document.createElement('div');
            questionDiv.style.cssText = 'border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;';

            questionDiv.innerHTML = `
                <div style="margin: 10px 0;">
                    <label>Вопрос:</label>
                    <input type="text" class="question-text" value="${questionData ? questionData.question : ''}" style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Ответы (через запятую):</label>
                    <input type="text" class="question-answers" value="${questionData ? questionData.answers.join(', ') : ''}" style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <div style="margin: 10px 0;">
                    <label>Подсказка:</label>
                    <input type="text" class="question-hint" value="${questionData ? (questionData.hint || '') : ''}" style="width: 100%; padding: 8px; margin: 5px 0;">
                </div>
                <button type="button" class="btn btn-danger" onclick="removeQuestion(this)">🗑️ Удалить вопрос</button>
            `;

            container.appendChild(questionDiv);
        }

        function removeQuestion(button) {
            button.parentElement.remove();
        }

        async function saveStand() {
            try {
                console.log('Saving stand...');

                const standData = {
                    id: document.getElementById('stand-id').value.trim(),
                    title: document.getElementById('stand-title').value.trim(),
                    description: document.getElementById('stand-description').value.trim(),
                    emoji: document.getElementById('stand-emoji').value.trim(),
                    color: document.getElementById('stand-color').value.trim(),
                    questions: []
                };

                // Валидация обязательных полей
                if (!standData.id || !standData.title || !standData.description) {
                    alert('Пожалуйста, заполните все обязательные поля: ID, название и описание');
                    return;
                }

                // Собираем вопросы
                const questionDivs = document.querySelectorAll('#questions-container > div');
                questionDivs.forEach(div => {
                    const questionElement = div.querySelector('.question-text');
                    const answersElement = div.querySelector('.question-answers');
                    const hintElement = div.querySelector('.question-hint');

                    if (questionElement && answersElement) {
                        const question = questionElement.value.trim();
                        const answersText = answersElement.value.trim();
                        const hint = hintElement ? hintElement.value.trim() : '';

                        if (question && answersText) {
                            standData.questions.push({
                                question: question,
                                answers: answersText.split(',').map(a => a.trim()).filter(a => a),
                                hint: hint || 'Нет подсказки'
                            });
                        }
                    }
                });

                console.log('Stand data to save:', standData);

                const url = editingStandId ? '/api/stands/update' : '/api/stands/create';
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(standData)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                console.log('Save result:', result);

                if (result.success) {
                    alert(editingStandId ? 'Стенд обновлен!' : 'Стенд создан!');
                    cancelEdit();
                    refreshNow();
                } else {
                    alert('Ошибка: ' + result.error);
                }
            } catch (error) {
                console.error('Error saving stand:', error);
                alert('Ошибка: ' + error.message);
            }
        }

        async function deleteStand(standId) {
            console.log('Deleting stand:', standId);

            if (!confirm(`Вы уверены, что хотите удалить стенд "${standId}"?`)) {
                return;
            }

            try {
                const response = await fetch('/api/stands/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: standId })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                console.log('Delete result:', result);

                if (result.success) {
                    alert('Стенд удален!');
                    refreshNow();
                } else {
                    alert('Ошибка: ' + result.error);
                }
            } catch (error) {
                console.error('Error deleting stand:', error);
                alert('Ошибка: ' + error.message);
            }
        }

        function cancelEdit() {
            document.getElementById('edit-stand-form').style.display = 'none';
            editingStandId = null;
        }

        async function reloadConfig() {
            try {
                const response = await fetch('/api/stands/reload', { method: 'POST' });
                const result = await response.json();
                alert(result.message);
                refreshNow();
            } catch (error) {
                alert('Ошибка: ' + error.message);
            }
        }

        async function clearAll() {
            if (confirm('Вы уверены, что хотите удалить ВСЕ данные пользователей?')) {
                try {
                    const response = await fetch('/api/realtime/clear', { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    refreshNow();
                } catch (error) {
                    alert('Ошибка: ' + error.message);
                }
            }
        }

        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {
            refreshNow();
            startAutoRefresh();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def admin_panel():
    """Главная страница админ-панели."""
    return render_template_string(SIMPLE_TEMPLATE)

@app.route('/api/realtime/stats', methods=['GET'])
def get_realtime_stats():
    """Получить актуальную статистику."""
    stats = state_manager.get_stats()
    return jsonify(stats)

@app.route('/api/realtime/users', methods=['GET'])
def get_realtime_users():
    """Получить всех пользователей с актуальными данными."""
    users = state_manager.get_all_users()

    # Импортируем актуальную конфигурацию
    try:
        from config import load_stands
        stands = load_stands()
        total_stands = len(stands)
    except:
        total_stands = 5

    result = []
    for user_id, user_data in users.items():
        completed = sum(1 for status in user_data.get('stand_status', {}).values() if status.get('done', False))
        total_user_stands = len(user_data.get('stand_status', {}))

        result.append({
            'user_id': user_id,
            'full_name': user_data.get('full_name'),
            'completed_stands': completed,
            'total_stands': total_user_stands,
            'progress_percent': round((completed / total_user_stands * 100) if total_user_stands > 0 else 0, 1),
            'vk_verified': user_data.get('vk_verified', False),
            'vk_profile': user_data.get('vk_profile'),
            'has_pending_question': user_data.get('pending_question') is not None,
            'pending_question_stand': user_data.get('pending_question', {}).get('stand_id') if user_data.get('pending_question') else None,
            'qualified': user_data.get('vk_verified', False) and completed >= total_stands,
            'awaiting_name': user_data.get('awaiting_name', False),
            'awaiting_vk_link': user_data.get('awaiting_vk_link', False),
            'created_at': user_data.get('created_at'),
            'updated_at': user_data.get('updated_at', datetime.now().isoformat())
        })

    # Сортируем по времени последнего обновления
    result.sort(key=lambda x: x['updated_at'], reverse=True)
    return jsonify(result)

@app.route('/api/realtime/stands', methods=['GET'])
def get_realtime_stands():
    """Получить актуальную конфигурацию стендов."""
    try:
        from config import load_stands
        stands = load_stands()
        return jsonify(stands)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/realtime/clear', methods=['POST'])
def clear_realtime_state():
    """Очистить все данные."""
    try:
        state_manager.clear_all()
        return jsonify({'success': True, 'message': 'Все данные пользователей удалены'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/realtime/refresh', methods=['POST'])
def force_refresh_state():
    """Принудительно обновить состояние из файла."""
    try:
        state_manager._load()
        return jsonify({'success': True, 'message': 'Состояние обновлено из файла'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stands/create', methods=['POST'])
def create_stand():
    """Создать новый стенд."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        # Загружаем текущие стенды из JSON
        from config import load_stands, save_stands
        stands = load_stands()

        # Проверяем, что стенда с таким ID еще нет
        if any(stand['id'] == data['id'] for stand in stands):
            return jsonify({'success': False, 'error': 'Стенд с таким ID уже существует'}), 400

        # Добавляем новый стенд
        new_stand = {
            'id': data['id'],
            'title': data['title'],
            'description': data['description'],
            'emoji': data['emoji'],
            'color': data['color'],
            'questions': data.get('questions', [])
        }

        stands.append(new_stand)

        # Сохраняем в JSON файл
        if save_stands(stands):
            return jsonify({'success': True, 'message': 'Стенд создан'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stands/update', methods=['POST'])
def update_stand():
    """Обновить существующий стенд."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        # Загружаем текущие стенды из JSON
        from config import load_stands, save_stands
        stands = load_stands()

        # Ищем стенд для обновления
        stand_index = None
        for i, stand in enumerate(stands):
            if stand['id'] == data['id']:
                stand_index = i
                break

        if stand_index is None:
            return jsonify({'success': False, 'error': 'Стенд не найден'}), 404

        # Обновляем стенд
        stands[stand_index] = {
            'id': data['id'],
            'title': data['title'],
            'description': data['description'],
            'emoji': data['emoji'],
            'color': data['color'],
            'questions': data.get('questions', [])
        }

        # Сохраняем в JSON файл
        if save_stands(stands):
            return jsonify({'success': True, 'message': 'Стенд обновлен'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stands/delete', methods=['POST'])
def delete_stand():
    """Удалить стенд."""
    try:
        data = request.get_json()
        if not data or 'id' not in data:
            return jsonify({'success': False, 'error': 'Нет ID стенда'}), 400

        # Загружаем текущие стенды из JSON
        from config import load_stands, save_stands
        stands = load_stands()

        # Удаляем стенд
        original_length = len(stands)
        stands = [stand for stand in stands if stand['id'] != data['id']]

        if len(stands) == original_length:
            return jsonify({'success': False, 'error': 'Стенд не найден'}), 404

        # Сохраняем в JSON файл
        if save_stands(stands):
            return jsonify({'success': True, 'message': 'Стенд удален'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка сохранения'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stands/reload', methods=['POST'])
def reload_config():
    """Перезагрузить конфигурацию стендов."""
    try:
        from config import load_stands
        stands = load_stands()
        return jsonify({'success': True, 'message': f'Конфигурация перезагружена. Загружено {len(stands)} стендов'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Проверка здоровья сервиса."""
    stats = state_manager.get_stats()
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'users_count': stats['total_users']
    })

if __name__ == '__main__':
    import signal
    import sys

    def signal_handler(sig, frame):
        print('\n[SimpleAdmin] Shutting down...')
        state_manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    port = int(os.environ.get('ADMIN_PORT', 5000))
    print(f"[SimpleAdmin] Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)