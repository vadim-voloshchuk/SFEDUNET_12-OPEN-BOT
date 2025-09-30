"""Веб-сервер для админ-панели управления ботом."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template_string, request, send_from_directory

from config import STANDS, STATE_FILE_PATH
from state import StateStore

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('ADMIN_SECRET_KEY', 'dev-secret-key')

# Инициализация state store
state_store = StateStore(Path(STATE_FILE_PATH))

# HTML шаблоны
ADMIN_PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Админ панель - Sfedunet 12 Bot</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .fade-in { animation: fadeIn 0.5s ease-in; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .question-card { transition: all 0.3s ease; }
        .question-card:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .nav-tabs .nav-link.active { background: linear-gradient(45deg, #007bff, #0056b3); color: white !important; }
    </style>
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-primary">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">
                <i class="fas fa-robot me-2"></i>Админ панель - Sfedunet 12 Bot
            </span>
            <span class="navbar-text">
                <i class="fas fa-calendar me-1"></i>{{ current_time }}
            </span>
        </div>
    </nav>

    <div class="container-fluid mt-4">
        <ul class="nav nav-tabs" id="adminTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="stands-tab" data-bs-toggle="tab" data-bs-target="#stands" type="button">
                    <i class="fas fa-map-marked-alt me-2"></i>Управление стендами
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="users-tab" data-bs-toggle="tab" data-bs-target="#users" type="button">
                    <i class="fas fa-users me-2"></i>Участники
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="giveaway-tab" data-bs-toggle="tab" data-bs-target="#giveaway" type="button">
                    <i class="fas fa-gift me-2"></i>Розыгрыш
                </button>
            </li>
        </ul>

        <div class="tab-content mt-4" id="adminTabsContent">
            <!-- Управление стендами -->
            <div class="tab-pane fade show active" id="stands" role="tabpanel">
                <div class="row">
                    <div class="col-12">
                        <div class="card shadow-sm">
                            <div class="card-header bg-primary text-white">
                                <h5 class="mb-0"><i class="fas fa-cog me-2"></i>Конфигурация стендов</h5>
                            </div>
                            <div class="card-body">
                                <div id="stands-container">
                                    <!-- Стенды будут загружены через JS -->
                                </div>
                                <button class="btn btn-success mt-3" onclick="addNewStand()">
                                    <i class="fas fa-plus me-2"></i>Добавить стенд
                                </button>
                                <button class="btn btn-primary mt-3 ms-2" onclick="saveStands()">
                                    <i class="fas fa-save me-2"></i>Сохранить изменения
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Участники -->
            <div class="tab-pane fade" id="users" role="tabpanel">
                <div class="row">
                    <div class="col-12">
                        <div class="card shadow-sm">
                            <div class="card-header bg-info text-white">
                                <h5 class="mb-0"><i class="fas fa-users me-2"></i>Статистика участников</h5>
                            </div>
                            <div class="card-body">
                                <div class="row mb-4">
                                    <div class="col-md-3">
                                        <div class="card text-center bg-primary text-white">
                                            <div class="card-body">
                                                <h3 id="total-users">0</h3>
                                                <p>Всего участников</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card text-center bg-success text-white">
                                            <div class="card-body">
                                                <h3 id="qualified-users">0</h3>
                                                <p>Квалифицированы</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card text-center bg-warning text-white">
                                            <div class="card-body">
                                                <h3 id="partial-users">0</h3>
                                                <p>Частично прошли</p>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card text-center bg-info text-white">
                                            <div class="card-body">
                                                <h3 id="new-users">0</h3>
                                                <p>Новички</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="table-responsive">
                                    <table class="table table-striped">
                                        <thead>
                                            <tr>
                                                <th>ID</th>
                                                <th>Имя</th>
                                                <th>VK профиль</th>
                                                <th>Прогресс</th>
                                                <th>Статус</th>
                                            </tr>
                                        </thead>
                                        <tbody id="users-table-body">
                                            <!-- Участники загружаются через JS -->
                                        </tbody>
                                    </table>
                                </div>
                                <div class="mt-3">
                                    <button class="btn btn-danger" onclick="clearState()" id="clear-state-btn">
                                        <i class="fas fa-trash me-2"></i>Очистить состояние бота
                                    </button>
                                    <small class="text-muted d-block mt-1">
                                        ⚠️ Это действие удалит всех пользователей и их прогресс!
                                    </small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Розыгрыш -->
            <div class="tab-pane fade" id="giveaway" role="tabpanel">
                <div class="row">
                    <div class="col-md-8">
                        <div class="card shadow-sm">
                            <div class="card-header bg-warning text-dark">
                                <h5 class="mb-0"><i class="fas fa-trophy me-2"></i>Розыгрыш призов</h5>
                            </div>
                            <div class="card-body">
                                <iframe src="/giveaway" width="100%" height="600" frameborder="0"></iframe>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card shadow-sm">
                            <div class="card-header bg-success text-white">
                                <h5 class="mb-0"><i class="fas fa-list me-2"></i>Участники розыгрыша</h5>
                            </div>
                            <div class="card-body">
                                <div id="qualified-participants">
                                    <!-- Список участников -->
                                </div>
                                <button class="btn btn-success w-100 mt-3" onclick="refreshGiveaway()">
                                    <i class="fas fa-sync me-2"></i>Обновить список
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Модальное окно для редактирования вопроса -->
    <div class="modal fade" id="questionModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Редактировать вопрос</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="questionForm">
                        <div class="mb-3">
                            <label class="form-label">Текст вопроса</label>
                            <textarea class="form-control" id="questionText" rows="3"></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Правильные ответы (каждый с новой строки)</label>
                            <textarea class="form-control" id="questionAnswers" rows="4"></textarea>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Подсказка</label>
                            <input type="text" class="form-control" id="questionHint">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                    <button type="button" class="btn btn-primary" onclick="saveQuestion()">Сохранить</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let stands = [];
        let currentStandIndex = -1;
        let currentQuestionIndex = -1;

        // Загрузка данных при загрузке страницы
        document.addEventListener('DOMContentLoaded', function() {
            loadStands();
            loadUsers();
            loadGiveawayParticipants();
        });

        // Загрузка стендов
        async function loadStands() {
            try {
                const response = await fetch('/api/stands');
                stands = await response.json();
                renderStands();
            } catch (error) {
                console.error('Ошибка загрузки стендов:', error);
            }
        }

        // Отображение стендов
        function renderStands() {
            const container = document.getElementById('stands-container');
            container.innerHTML = '';

            stands.forEach((stand, standIndex) => {
                const standHtml = `
                    <div class="card mb-3 question-card">
                        <div class="card-header bg-light">
                            <div class="row align-items-center">
                                <div class="col">
                                    <strong>${stand.emoji} ${stand.title}</strong>
                                    <small class="text-muted ms-2">(ID: ${stand.id})</small>
                                </div>
                                <div class="col-auto">
                                    <button class="btn btn-sm btn-outline-danger" onclick="removeStand(${standIndex})">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="form-label">Описание</label>
                                <input type="text" class="form-control" value="${stand.description}"
                                       onchange="updateStandField(${standIndex}, 'description', this.value)">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Эмодзи</label>
                                <input type="text" class="form-control" value="${stand.emoji}"
                                       onchange="updateStandField(${standIndex}, 'emoji', this.value)">
                            </div>
                            <div class="mb-3">
                                <strong>Вопросы:</strong>
                                <div id="questions-${standIndex}">
                                    ${stand.questions.map((q, qIndex) => `
                                        <div class="border rounded p-2 mb-2 bg-light">
                                            <div class="d-flex justify-content-between align-items-start">
                                                <div class="flex-grow-1">
                                                    <small class="text-muted">Вопрос ${qIndex + 1}:</small>
                                                    <div>${q.question}</div>
                                                    <small class="text-success">Ответы: ${q.answers.join(', ')}</small>
                                                </div>
                                                <div>
                                                    <button class="btn btn-sm btn-outline-primary me-1"
                                                            onclick="editQuestion(${standIndex}, ${qIndex})">
                                                        <i class="fas fa-edit"></i>
                                                    </button>
                                                    <button class="btn btn-sm btn-outline-danger"
                                                            onclick="removeQuestion(${standIndex}, ${qIndex})">
                                                        <i class="fas fa-trash"></i>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                                <button class="btn btn-sm btn-outline-success mt-2" onclick="addQuestion(${standIndex})">
                                    <i class="fas fa-plus me-1"></i>Добавить вопрос
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                container.innerHTML += standHtml;
            });
        }

        // Обновление поля стенда
        function updateStandField(standIndex, field, value) {
            stands[standIndex][field] = value;
        }

        // Добавление нового стенда
        function addNewStand() {
            const newStand = {
                id: `stand_${Date.now()}`,
                title: '🆕 Новый стенд',
                emoji: '🆕',
                description: 'Описание нового стенда',
                color: '🟦',
                questions: []
            };
            stands.push(newStand);
            renderStands();
        }

        // Удаление стенда
        function removeStand(standIndex) {
            if (confirm('Удалить этот стенд?')) {
                stands.splice(standIndex, 1);
                renderStands();
            }
        }

        // Добавление вопроса
        function addQuestion(standIndex) {
            currentStandIndex = standIndex;
            currentQuestionIndex = -1;
            document.getElementById('questionText').value = '';
            document.getElementById('questionAnswers').value = '';
            document.getElementById('questionHint').value = '';
            new bootstrap.Modal(document.getElementById('questionModal')).show();
        }

        // Редактирование вопроса
        function editQuestion(standIndex, questionIndex) {
            currentStandIndex = standIndex;
            currentQuestionIndex = questionIndex;
            const question = stands[standIndex].questions[questionIndex];
            document.getElementById('questionText').value = question.question;
            document.getElementById('questionAnswers').value = question.answers.join('\\n');
            document.getElementById('questionHint').value = question.hint || '';
            new bootstrap.Modal(document.getElementById('questionModal')).show();
        }

        // Сохранение вопроса
        function saveQuestion() {
            const question = {
                question: document.getElementById('questionText').value,
                answers: document.getElementById('questionAnswers').value.split('\\n').filter(a => a.trim()),
                hint: document.getElementById('questionHint').value
            };

            if (currentQuestionIndex === -1) {
                stands[currentStandIndex].questions.push(question);
            } else {
                stands[currentStandIndex].questions[currentQuestionIndex] = question;
            }

            bootstrap.Modal.getInstance(document.getElementById('questionModal')).hide();
            renderStands();
        }

        // Удаление вопроса
        function removeQuestion(standIndex, questionIndex) {
            if (confirm('Удалить этот вопрос?')) {
                stands[standIndex].questions.splice(questionIndex, 1);
                renderStands();
            }
        }

        // Сохранение стендов
        async function saveStands() {
            try {
                const response = await fetch('/api/stands', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(stands)
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.bot_notified) {
                        alert('✅ ' + result.message + '\\n\\n🔄 Бот автоматически обновлен!');
                    } else {
                        alert('⚠️ ' + result.message + '\\n\\n❌ Не удалось уведомить бота. Перезапустите бота вручную.');
                    }
                } else {
                    alert('❌ Ошибка сохранения стендов');
                }
            } catch (error) {
                console.error('Ошибка сохранения:', error);
                alert('Ошибка сохранения стендов');
            }
        }

        // Загрузка пользователей
        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                const users = await response.json();
                renderUsers(users);
        updateStats(users);
            } catch (error) {
                console.error('Ошибка загрузки пользователей:', error);
            }
        }

        // Обновление статистики
        function updateStats(users) {
            const stats = {
                total: users.length,
                qualified: 0,
                partial: 0,
                new: 0
            };

            users.forEach(user => {
                const completedStands = Object.values(user.stand_status).filter(s => s.done).length;
                const totalStands = stands.length;
                const isQualified = user.vk_verified && completedStands === totalStands;

                if (isQualified) stats.qualified++;
                else if (completedStands > 0) stats.partial++;
                else stats.new++;
            });

            // Обновляем статистику
            document.getElementById('total-users').textContent = stats.total;
            document.getElementById('qualified-users').textContent = stats.qualified;
            document.getElementById('partial-users').textContent = stats.partial;
            document.getElementById('new-users').textContent = stats.new;
        }

        // Отображение пользователей
        function renderUsers(users) {
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = '';

            users.forEach(user => {
                const completedStands = Object.values(user.stand_status).filter(s => s.done).length;
                const totalStands = stands.length;
                const isQualified = user.vk_verified && completedStands === totalStands;

                const statusBadge = isQualified ?
                    '<span class="badge bg-success">Квалифицирован</span>' :
                    completedStands > 0 ?
                    '<span class="badge bg-warning">В процессе</span>' :
                    '<span class="badge bg-secondary">Новичок</span>';

                const row = `
                    <tr>
                        <td>${user.user_id}</td>
                        <td>${user.full_name || 'Не указано'}</td>
                        <td>${user.vk_verified ? '✅' : '❌'}</td>
                        <td>${completedStands}/${totalStands}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });
        }

        // Загрузка участников розыгрыша
        async function loadGiveawayParticipants() {
            try {
                const response = await fetch('/api/qualified');
                const participants = await response.json();
                renderGiveawayParticipants(participants);
            } catch (error) {
                console.error('Ошибка загрузки участников:', error);
            }
        }

        // Отображение участников розыгрыша
        function renderGiveawayParticipants(participants) {
            const container = document.getElementById('qualified-participants');
            container.innerHTML = `
                <div class="alert alert-info">
                    <strong>${participants.length}</strong> участников квалифицировано для розыгрыша
                </div>
            `;

            participants.forEach(participant => {
                container.innerHTML += `
                    <div class="border rounded p-2 mb-2">
                        <strong>${participant.full_name}</strong><br>
                        <small class="text-muted">ID: ${participant.user_id}</small>
                    </div>
                `;
            });
        }

        // Обновление данных розыгрыша
        function refreshGiveaway() {
            loadGiveawayParticipants();
            // Обновляем iframe розыгрыша
            document.querySelector('#giveaway iframe').src = '/giveaway?t=' + Date.now();
        }

        // Очистка состояния бота
        async function clearState() {
            if (!confirm('⚠️ ВНИМАНИЕ! Это действие безвозвратно удалит всех пользователей и их прогресс. Продолжить?')) {
                return;
            }

            if (!confirm('Вы действительно уверены? Все данные будут потеряны!')) {
                return;
            }

            const btn = document.getElementById('clear-state-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Очищаю...';
            btn.disabled = true;

            try {
                const response = await fetch('/api/clear_state', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    alert('✅ Состояние бота успешно очищено!');
                    // Обновляем все данные
                    loadUsers();
                    loadGiveawayParticipants();
                } else {
                    const error = await response.text();
                    alert('❌ Ошибка при очистке состояния: ' + error);
                }
            } catch (error) {
                alert('❌ Произошла ошибка: ' + error.message);
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def admin_panel():
    """Главная страница админ-панели."""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template_string(ADMIN_PANEL_TEMPLATE, current_time=current_time)

@app.route('/giveaway')
def giveaway_page():
    """Страница розыгрыша."""
    return send_from_directory('.', 'admin_giveaway_fixed.html')

@app.route('/api/stands', methods=['GET'])
def get_stands():
    """Получить список стендов."""
    return jsonify(STANDS)

def notify_bot_config_changed():
    """Уведомляет бота об изменении конфигурации."""
    try:
        import requests
        # Уведомляем бота о перезагрузке конфигурации
        response = requests.post('http://localhost:8765/reload-config', timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f'Failed to notify bot: {e}')
        return False

@app.route('/api/stands', methods=['POST'])
def save_stands():
    """Сохранить стенды в config.py."""
    try:
        new_stands = request.json

        # Обновляем config.py
        config_path = Path('config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Заменяем массив STANDS
        import re
        stands_str = json.dumps(new_stands, ensure_ascii=False, indent=4)
        stands_str = stands_str.replace('true', 'True').replace('false', 'False').replace('null', 'None')

        pattern = r'STANDS = \[.*?\]'
        replacement = f'STANDS = {stands_str}'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Уведомляем бота об изменениях
        bot_notified = notify_bot_config_changed()

        return jsonify({
            'success': True,
            'bot_notified': bot_notified,
            'message': 'Конфигурация сохранена' + (' и бот уведомлен' if bot_notified else ', но бот не отвечает')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """Получить список пользователей."""
    users = []
    for user_id, user_data in state_store.data.items():
        if user_id != 'meta':
            user_info = user_data.copy()
            user_info['user_id'] = user_id
            users.append(user_info)
    return jsonify(users)

@app.route('/api/qualified', methods=['GET'])
def get_qualified_users():
    """Получить квалифицированных участников."""
    qualified = []
    for user_id, user_data in state_store.data.items():
        if user_id != 'meta':
            completed = sum(1 for status in user_data.get('stand_status', {}).values() if status.get('done', False))
            if user_data.get('vk_verified', False) and completed == 3:
                participant = {
                    'user_id': user_id,
                    'full_name': user_data.get('full_name', 'Неизвестно'),
                    'vk_profile': user_data.get('vk_profile', ''),
                }
                qualified.append(participant)
    return jsonify(qualified)

@app.route('/api/giveaway_data', methods=['GET'])
def get_giveaway_data():
    """Получить данные для розыгрыша в формате для HTML страницы."""
    qualified = []
    for user_id, user_data in state_store.data.items():
        if user_id != 'meta':
            completed = sum(1 for status in user_data.get('stand_status', {}).values() if status.get('done', False))
            if user_data.get('vk_verified', False) and completed == 3:
                participant = {
                    'id': int(user_id),
                    'username': user_data.get('full_name', f'User_{user_id}'),
                    'avatar': f'https://via.placeholder.com/100?text={user_data.get("full_name", "U")[0]}'
                }
                qualified.append(participant)
    return jsonify(qualified)

@app.route('/api/clear_state', methods=['POST'])
def clear_state():
    """Очистить состояние бота - удалить всех пользователей."""
    try:
        # Очищаем все данные, кроме метаинформации
        state_store.data = {}

        # Сохраняем пустое состояние
        state_store.save()

        # Также можно очистить физический файл для полной уверенности
        state_file_path = Path(STATE_FILE_PATH)
        if state_file_path.exists():
            with open(state_file_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

        return jsonify({'success': True, 'message': 'Состояние бота успешно очищено'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('ADMIN_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)