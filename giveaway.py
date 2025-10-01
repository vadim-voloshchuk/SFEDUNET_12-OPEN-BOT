#!/usr/bin/env python3
"""Страница розыгрыша для Sfedunet 12."""

import os
import random
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем единый менеджер состояния
from realtime_state import get_state_manager

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('GIVEAWAY_SECRET_KEY', 'giveaway-secret-key')

# Получаем глобальный менеджер состояния
state_manager = get_state_manager()

print("[Giveaway] Initialized with realtime state manager")

# HTML шаблон страницы розыгрыша
GIVEAWAY_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎁 Розыгрыш Sfedunet 12</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
        }
        .header {
            margin-bottom: 40px;
        }
        .title {
            font-size: 3em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .stats-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin: 30px 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat {
            display: inline-block;
            margin: 20px;
            text-align: center;
        }
        .stat-number {
            font-size: 3em;
            font-weight: bold;
            display: block;
            color: #FFD700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stat-label {
            font-size: 1.1em;
            opacity: 0.9;
            margin-top: 10px;
        }
        .participants {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            max-height: 400px;
            overflow-y: auto;
        }
        .participant {
            background: rgba(255,255,255,0.1);
            margin: 10px 0;
            padding: 15px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .participant-name {
            font-weight: bold;
            font-size: 1.1em;
        }
        .participant-vk {
            opacity: 0.8;
            font-size: 0.9em;
        }
        .winner-section {
            margin-top: 40px;
        }
        .btn {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 1.2em;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            margin: 10px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .winner {
            background: linear-gradient(45deg, #FFD700, #FFA500);
            color: #333;
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            font-size: 1.5em;
            font-weight: bold;
            animation: glow 2s infinite alternate;
        }
        @keyframes glow {
            from { box-shadow: 0 0 20px #FFD700; }
            to { box-shadow: 0 0 30px #FFA500, 0 0 40px #FFD700; }
        }
        .auto-refresh {
            margin: 20px 0;
            opacity: 0.7;
            font-size: 0.9em;
        }
        .countdown {
            font-size: 1.5em;
            margin: 20px 0;
            color: #FFD700;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">🎁 Розыгрыш Sfedunet 12</h1>
            <p class="subtitle">Призы ждут своих победителей!</p>
        </div>

        <div class="stats-card">
            <div class="stat">
                <span class="stat-number" id="total-participants">0</span>
                <div class="stat-label">Всего участников</div>
            </div>
            <div class="stat">
                <span class="stat-number" id="qualified-participants">0</span>
                <div class="stat-label">Квалифицированы</div>
            </div>
            <div class="stat">
                <span class="stat-number" id="completion-rate">0%</span>
                <div class="stat-label">Процент завершения</div>
            </div>
        </div>

        <div class="auto-refresh">
            🔄 Обновление каждые 3 секунды | Последнее обновление: <span id="last-update">загрузка...</span>
        </div>

        <div class="winner-section">
            <h2>🏆 Розыгрыш призов</h2>
            <button class="btn" onclick="drawWinner()" id="draw-btn">🎲 Разыграть приз</button>
            <div id="winner-result"></div>
        </div>

        <h3>👥 Участники розыгрыша</h3>
        <div class="participants" id="participants-list">
            <p>Загрузка участников...</p>
        </div>
    </div>

    <script>
        let participants = [];

        async function loadData() {
            try {
                const response = await fetch('/api/giveaway/stats');
                const data = await response.json();

                document.getElementById('total-participants').textContent = data.total_participants;
                document.getElementById('qualified-participants').textContent = data.qualified_participants;
                document.getElementById('completion-rate').textContent = Math.round(data.completion_rate) + '%';

                participants = data.participants;
                renderParticipants();

                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();

                // Включаем/выключаем кнопку розыгрыша
                const drawBtn = document.getElementById('draw-btn');
                drawBtn.disabled = data.qualified_participants === 0;

            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        function renderParticipants() {
            const container = document.getElementById('participants-list');

            if (participants.length === 0) {
                container.innerHTML = '<p>Пока нет участников розыгрыша</p>';
                return;
            }

            const html = participants.map((participant, index) => `
                <div class="participant">
                    <div>
                        <div class="participant-name">${participant.full_name}</div>
                        <div class="participant-vk">📱 ${participant.vk_profile}</div>
                    </div>
                    <div>
                        🏆 ${participant.completed_stands}/${participant.total_stands} стендов
                    </div>
                </div>
            `).join('');

            container.innerHTML = html;
        }

        async function drawWinner() {
            if (participants.length === 0) {
                alert('Нет участников для розыгрыша!');
                return;
            }

            const drawBtn = document.getElementById('draw-btn');
            const resultDiv = document.getElementById('winner-result');

            drawBtn.disabled = true;
            drawBtn.textContent = '🎲 Розыгрыш...';

            // Анимация розыгрыша
            let counter = 0;
            const animationInterval = setInterval(() => {
                const randomParticipant = participants[Math.floor(Math.random() * participants.length)];
                resultDiv.innerHTML = `
                    <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin: 10px 0;">
                        🎲 ${randomParticipant.full_name}
                    </div>
                `;
                counter++;

                if (counter > 20) {
                    clearInterval(animationInterval);

                    // Выбираем финального победителя
                    const winner = participants[Math.floor(Math.random() * participants.length)];
                    resultDiv.innerHTML = `
                        <div class="winner">
                            🏆 ПОБЕДИТЕЛЬ: ${winner.full_name}
                            <div style="font-size: 0.8em; margin-top: 10px;">
                                📱 ${winner.vk_profile}
                            </div>
                        </div>
                    `;

                    drawBtn.disabled = false;
                    drawBtn.textContent = '🎲 Разыграть еще раз';
                }
            }, 100);
        }

        // Автообновление каждые 3 секунды
        setInterval(loadData, 3000);

        // Первоначальная загрузка
        loadData();
    </script>
</body>
</html>
"""

@app.route('/')
def giveaway_page():
    """Главная страница розыгрыша."""
    return render_template_string(GIVEAWAY_TEMPLATE)

@app.route('/api/giveaway/stats', methods=['GET'])
def get_giveaway_stats():
    """Получить статистику для розыгрыша."""
    users = state_manager.get_all_users()

    # Импортируем актуальную конфигурацию стендов
    try:
        from config import load_stands
        stands = load_stands()
        total_stands = len(stands)
    except:
        total_stands = 5

    total_participants = len(users)
    qualified_participants = []

    for user_id, user_data in users.items():
        if not user_data.get('full_name'):
            continue

        completed = sum(1 for status in user_data.get('stand_status', {}).values() if status.get('done', False))
        total_user_stands = len(user_data.get('stand_status', {}))

        # Квалифицированные участники - те кто прошел все стенды И добавил ВК
        if completed >= total_stands and user_data.get('vk_verified', False):
            qualified_participants.append({
                'user_id': user_id,
                'full_name': user_data.get('full_name'),
                'vk_profile': user_data.get('vk_profile'),
                'completed_stands': completed,
                'total_stands': total_user_stands
            })

    completion_rate = (len(qualified_participants) / total_participants * 100) if total_participants > 0 else 0

    return jsonify({
        'total_participants': total_participants,
        'qualified_participants': len(qualified_participants),
        'completion_rate': completion_rate,
        'participants': qualified_participants,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    """Проверка здоровья сервиса."""
    return jsonify({
        'status': 'healthy',
        'service': 'giveaway',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    import signal
    import sys

    def signal_handler(sig, frame):
        print('\n[Giveaway] Shutting down...')
        state_manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    port = int(os.environ.get('GIVEAWAY_PORT', 5001))
    print(f"[Giveaway] Starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)