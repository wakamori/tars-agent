/**
 * TARS - Collaborative Robot Safety System
 * Matter.js Physics Simulation + Gemini Vision AI
 */

// Matter.js aliases
const Engine = Matter.Engine;
const Render = Matter.Render;
const World = Matter.World;
const Bodies = Matter.Bodies;
const Body = Matter.Body;
const Events = Matter.Events;
const Runner = Matter.Runner;

// Global state
let engine;
let render;
let runner;
let world;
let worker;
let robot;
let safetyBarriers = [];
let isRunning = false;
let isPaused = false;
let startTime = 0;
let preventedAccidents = 0;
let analysisInProgress = false;

// Canvas dimensions
const CANVAS_WIDTH = 900;
const CANVAS_HEIGHT = 600;

// Initialize the simulation
function init() {
    // Create engine
    engine = Engine.create();
    world = engine.world;
    world.gravity.y = 0; // No gravity for top-down view

    // Create renderer
    render = Render.create({
        canvas: document.getElementById('gameCanvas'),
        engine: engine,
        options: {
            width: CANVAS_WIDTH,
            height: CANVAS_HEIGHT,
            wireframes: false,
            background: '#0a0e27'
        }
    });

    // Create factory floor
    createFactoryFloor();
    
    // Create entities
    createWorker();
    createRobot();
    
    // Create runner
    runner = Runner.create();
    
    // Render initial state
    Render.run(render);
    
    // Add collision detection
    Events.on(engine, 'collisionStart', handleCollision);
    
    logThinking('システム初期化完了');
}

// Create factory floor boundaries
function createFactoryFloor() {
    const wallOptions = {
        isStatic: true,
        render: {
            fillStyle: '#333333'
        }
    };

    // Walls
    const topWall = Bodies.rectangle(CANVAS_WIDTH / 2, 10, CANVAS_WIDTH, 20, wallOptions);
    const bottomWall = Bodies.rectangle(CANVAS_WIDTH / 2, CANVAS_HEIGHT - 10, CANVAS_WIDTH, 20, wallOptions);
    const leftWall = Bodies.rectangle(10, CANVAS_HEIGHT / 2, 20, CANVAS_HEIGHT, wallOptions);
    const rightWall = Bodies.rectangle(CANVAS_WIDTH - 10, CANVAS_HEIGHT / 2, 20, CANVAS_HEIGHT, wallOptions);

    World.add(world, [topWall, bottomWall, leftWall, rightWall]);

    // Add some static obstacles (workbenches, equipment)
    const obstacle1 = Bodies.rectangle(200, 150, 100, 80, {
        isStatic: true,
        render: {
            fillStyle: '#555555'
        },
        label: 'workbench'
    });

    const obstacle2 = Bodies.rectangle(700, 450, 120, 60, {
        isStatic: true,
        render: {
            fillStyle: '#555555'
        },
        label: 'equipment'
    });

    World.add(world, [obstacle1, obstacle2]);
}

// Create worker (blue circle)
function createWorker() {
    worker = Bodies.circle(150, 300, 20, {
        render: {
            fillStyle: '#4285F4'
        },
        label: 'worker',
        friction: 0.1,
        restitution: 0.3
    });

    World.add(world, worker);

    // Add random movement to worker
    setInterval(() => {
        if (isRunning && !isPaused) {
            const force = {
                x: (Math.random() - 0.5) * 0.001,
                y: (Math.random() - 0.5) * 0.001
            };
            Body.applyForce(worker, worker.position, force);
        }
    }, 100);
}

// Create robot (red rectangle)
function createRobot() {
    robot = Bodies.rectangle(700, 300, 80, 80, {
        render: {
            fillStyle: '#EA4335'
        },
        label: 'robot',
        friction: 0.05,
        restitution: 0.2
    });

    World.add(world, robot);

    // Robot movement pattern (back and forth)
    let robotDirection = 1;
    setInterval(() => {
        if (isRunning && !isPaused) {
            if (robot.position.x > 750) robotDirection = -1;
            if (robot.position.x < 550) robotDirection = 1;

            Body.setVelocity(robot, { x: robotDirection * 2, y: 0 });
        }
    }, 50);
}

// Handle collisions
function handleCollision(event) {
    const pairs = event.pairs;

    for (let pair of pairs) {
        const { bodyA, bodyB } = pair;

        // Check worker-robot collision
        if ((bodyA.label === 'worker' && bodyB.label === 'robot') ||
            (bodyA.label === 'robot' && bodyB.label === 'worker')) {
            
            // Check if there's a barrier preventing the collision
            const hasBarrier = safetyBarriers.some(barrier => {
                return isBetween(barrier.position, worker.position, robot.position);
            });

            if (hasBarrier) {
                preventedAccidents++;
                updatePreventedCount();
                logThinking('🛡️ 安全バリアが衝突を防ぎました！', 'success');
            } else {
                logThinking('⚠️ 衝突発生！', 'error');
            }
        }
    }
}

// Check if barrier is between two objects
function isBetween(barrierPos, pos1, pos2) {
    const dx = pos2.x - pos1.x;
    const dy = pos2.y - pos1.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    const barrierDist1 = Math.sqrt(
        Math.pow(barrierPos.x - pos1.x, 2) + 
        Math.pow(barrierPos.y - pos1.y, 2)
    );
    const barrierDist2 = Math.sqrt(
        Math.pow(barrierPos.x - pos2.x, 2) + 
        Math.pow(barrierPos.y - pos2.y, 2)
    );
    
    return (barrierDist1 + barrierDist2) < (dist * 1.2);
}

// Start simulation
function startSimulation() {
    if (!isRunning) {
        Runner.run(runner, engine);
        isRunning = true;
        isPaused = false;
        startTime = Date.now();
        
        document.getElementById('startBtn').disabled = true;
        document.getElementById('pauseBtn').disabled = false;
        document.getElementById('analyzeBtn').disabled = false;
        
        logThinking('シミュレーション開始', 'success');
        
        // Start time counter
        updateTime();
    }
}

// Pause simulation
function pauseSimulation() {
    if (isRunning && !isPaused) {
        Runner.stop(runner);
        isPaused = true;
        document.getElementById('pauseBtn').textContent = '▶ 再開';
        logThinking('シミュレーション一時停止');
    } else if (isPaused) {
        Runner.run(runner, engine);
        isPaused = false;
        document.getElementById('pauseBtn').textContent = '⏸ 一時停止';
        logThinking('シミュレーション再開', 'success');
    }
}

// Reset simulation
function resetSimulation() {
    // Remove all barriers
    safetyBarriers.forEach(barrier => World.remove(world, barrier));
    safetyBarriers = [];
    
    // Reset entities
    Body.setPosition(worker, { x: 150, y: 300 });
    Body.setVelocity(worker, { x: 0, y: 0 });
    Body.setPosition(robot, { x: 700, y: 300 });
    Body.setVelocity(robot, { x: 0, y: 0 });
    
    // Reset state
    isRunning = false;
    isPaused = false;
    preventedAccidents = 0;
    startTime = 0;
    
    // Reset UI
    document.getElementById('startBtn').disabled = false;
    document.getElementById('pauseBtn').disabled = true;
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('pauseBtn').textContent = '⏸ 一時停止';
    
    updatePreventedCount();
    updateRiskLevel('安全');
    clearWarnings();
    clearInterventions();
    
    logThinking('システムリセット完了', 'success');
}

// Capture canvas and send to AI for analysis
async function analyzeWithAI() {
    if (analysisInProgress) {
        logThinking('分析実行中...', 'warning');
        return;
    }

    analysisInProgress = true;
    const analyzeBtn = document.getElementById('analyzeBtn');
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '🧠 分析中...';
    analyzeBtn.classList.add('loading');
    
    logThinking('画像をキャプチャしています...');

    try {
        // Capture canvas as blob
        const canvas = document.getElementById('gameCanvas');
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        
        logThinking('Gemini Vision APIに送信中...');

        // Send to backend
        const formData = new FormData();
        formData.append('file', blob, 'factory-floor.png');

        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        const data = await response.json();
        
        logThinking('AI分析完了！', 'success');
        
        // Process analysis results
        processAnalysisResults(data);
        
        // Fetch updated memory stream
        await fetchMemoryStream();

    } catch (error) {
        console.error('Analysis error:', error);
        logThinking(`分析エラー: ${error.message}`, 'error');
        
        // Try mock endpoint as fallback
        try {
            logThinking('モックデータを使用します...', 'warning');
            
            const mockResponse = await fetch('/mock-analyze', {
                method: 'GET'
            });
            
            if (!mockResponse.ok) {
                throw new Error(`Mock API Error: ${mockResponse.status}`);
            }
            
            const mockData = await mockResponse.json();
            processAnalysisResults(mockData);
        } catch (mockError) {
            console.error('Mock analysis also failed:', mockError);
        }
    } finally {
        analysisInProgress = false;
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🧠 AI分析';
        analyzeBtn.classList.remove('loading');
    }
}

// Process analysis results from Gemini (Updated for AgentResponse)
function processAnalysisResults(data) {
    if (!data) {
        logThinking('分析データが空です', 'error');
        return;
    }
    
    // New AgentResponse format
    const { 
        self_inquiry, 
        entities, 
        discovered_patterns, 
        intervention_decision, 
        confidence,
        learning_note 
    } = data;
    
    // Update confidence
    updateConfidence(confidence || 0);
    
    // Display agent's thinking process
    if (self_inquiry) {
        displayThinkingProcess(self_inquiry);
    }
    
    // Display discovered patterns
    if (discovered_patterns && discovered_patterns.length > 0) {
        displayDiscoveredPatterns(discovered_patterns);
    }
    
    // Calculate risk level from entities
    const maxRisk = entities && entities.length > 0 
        ? Math.max(...entities.map(e => e.risk_level))
        : 0;
    
    if (maxRisk > 70) {
        updateRiskLevel('危険', 'high');
    } else if (maxRisk > 40) {
        updateRiskLevel('注意', 'low');
    } else {
        updateRiskLevel('安全', 'safe');
    }
    
    // Apply intervention decision
    if (intervention_decision) {
        applyInterventionDecision(intervention_decision);
    }
    
    // Log learning note
    if (learning_note) {
        logThinking(`学習: ${learning_note}`, 'info');
    }
    
    const entityCount = entities ? entities.length : 0;
    logThinking(`検出: ${entityCount}個のエンティティ, リスク最大値: ${maxRisk}, 優先度: ${intervention_decision?.priority || 0}`, 'success');
}

// Display agent's thinking process (Self-Inquiry)
function displayThinkingProcess(selfInquiry) {
    const container = document.getElementById('thinkingProcess');
    if (!container) return;
    
    let html = '<div class="self-inquiry">';
    
    // Observations
    if (selfInquiry.observations && selfInquiry.observations.length > 0) {
        html += '<div class="inquiry-section">';
        html += '<h4>🔍 観察</h4>';
        html += '<ul class="inquiry-list">';
        selfInquiry.observations.forEach(obs => {
            html += `<li>${obs}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Memory connections
    if (selfInquiry.memory_connections && selfInquiry.memory_connections.length > 0) {
        html += '<div class="inquiry-section">';
        html += '<h4>🧠 記憶との関連</h4>';
        html += '<ul class="inquiry-list">';
        selfInquiry.memory_connections.forEach(mem => {
            html += `<li>${mem}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Accident scenarios
    if (selfInquiry.accident_scenarios && selfInquiry.accident_scenarios.length > 0) {
        html += '<div class="inquiry-section">';
        html += '<h4>⚠️ 想定される事故シナリオ</h4>';
        selfInquiry.accident_scenarios.forEach(scenario => {
            const severityColor = scenario.severity > 7 ? '#ff4444' : 
                                   scenario.severity > 4 ? '#ff9800' : '#ffc107';
            const probability = Math.round(scenario.probability * 100);
            html += `<div class="scenario-card" style="border-left: 4px solid ${severityColor}">`;
            html += `<strong>${scenario.scenario}</strong><br>`;
            html += `<div class="scenario-meta">`;
            html += `確率: <span class="badge">${probability}%</span> | `;
            html += `深刻度: <span class="badge">${scenario.severity}/10</span>`;
            html += `</div>`;
            html += `<small class="scenario-reasoning">${scenario.reasoning}</small>`;
            html += `</div>`;
        });
        html += '</div>';
    }
    
    // Causal analysis
    if (selfInquiry.causal_analysis) {
        html += '<div class="inquiry-section">';
        html += '<h4>🔬 因果関係の分析</h4>';
        html += `<p class="causal-text">${selfInquiry.causal_analysis}</p>`;
        html += '</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

// Display discovered patterns
function displayDiscoveredPatterns(patterns) {
    const container = document.getElementById('discoveredPatterns');
    if (!container) return;
    
    let html = '';
    const novelPatterns = patterns.filter(p => p.is_novel);
    
    if (novelPatterns.length > 0) {
        html += '<div class="alert alert-success">';
        html += `<strong>🎉 新しいパターンを${novelPatterns.length}件発見しました！</strong>`;
        html += '</div>';
    }
    
    patterns.forEach(pattern => {
        const badgeClass = pattern.is_novel ? 'badge-new' : 'badge-known';
        html += `<div class="pattern-card ${badgeClass}">`;
        html += `<h4>${pattern.pattern_name} ${pattern.is_novel ? '<span class="badge-new-icon">🆕</span>' : ''}</h4>`;
        html += `<p>${pattern.description}</p>`;
        html += `<div class="indicators">`;
        html += `<strong>検出指標:</strong> ${pattern.indicators.join(', ')}`;
        html += `</div>`;
        html += `</div>`;
    });
    
    container.innerHTML = html;
}

// Apply intervention decision (with priority and alternatives)
function applyInterventionDecision(decision) {
    if (!decision || !decision.primary_action) {
        logThinking('介入は不要です');
        return;
    }

    clearInterventions();
    const interventionsList = document.getElementById('interventionsList');
    interventionsList.innerHTML = '';
    
    // Display priority
    const priorityBadge = getPriorityBadge(decision.priority);
    let html = `<div class="priority-indicator">${priorityBadge}</div>`;
    
    // Primary action
    const action = decision.primary_action;
    html += '<div class="intervention-primary">';
    html += '<h4>主要アクション</h4>';
    html += `<div class="intervention-card primary">`;
    html += `<div class="intervention-type">${getInterventionIcon(action.type)} ${getInterventionLabel(action.type)}</div>`;
    html += `<div class="intervention-reasoning">${action.reasoning}</div>`;
    html += `<div class="intervention-outcome">期待される結果: ${action.expected_outcome}</div>`;
    html += `</div>`;
    html += '</div>';
    
    // Create intervention in simulation
    if (action.type === 'barrier' && action.position) {
        createSafetyBarrier(
            action.position[0] * CANVAS_WIDTH,
            action.position[1] * CANVAS_HEIGHT
        );
    }
    
    // Alternative actions
    if (decision.alternative_actions && decision.alternative_actions.length > 0) {
        html += '<div class="intervention-alternatives">';
        html += '<h4>代替案</h4>';
        decision.alternative_actions.forEach(alt => {
            html += `<div class="intervention-card alternative">`;
            html += `<strong>${getInterventionIcon(alt.type)} ${getInterventionLabel(alt.type)}</strong>: ${alt.reasoning}`;
            html += `</div>`;
        });
        html += '</div>';
    }
    
    interventionsList.innerHTML = html;
    logThinking(`優先度 ${decision.priority}/10: ${action.type} を実施`, 'success');
}

// Get priority badge HTML
function getPriorityBadge(priority) {
    const level = priority >= 8 ? 'critical' : priority >= 5 ? 'high' : 'normal';
    const color = priority >= 8 ? '#ff4444' : priority >= 5 ? '#ff9800' : '#4CAF50';
    return `<div class="priority-badge priority-${level}" style="background-color: ${color}">優先度: ${priority}/10</div>`;
}

// Create safety barrier in simulation
function createSafetyBarrier(x, y) {
    const barrier = Bodies.rectangle(x, y, 100, 20, {
        isStatic: true,
        render: {
            fillStyle: '#34A853',
            strokeStyle: '#FFFFFF',
            lineWidth: 2
        },
        label: 'safety_barrier'
    });

    World.add(world, barrier);
    safetyBarriers.push(barrier);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        World.remove(world, barrier);
        safetyBarriers = safetyBarriers.filter(b => b !== barrier);
    }, 5000);
}

// Helper functions for UI updates
function updatePreventedCount() {
    document.getElementById('preventedCount').textContent = preventedAccidents;
}

function updateRiskLevel(level, risk = 'safe') {
    const elem = document.getElementById('riskLevel');
    elem.textContent = level;
    elem.className = `stat-value risk-${risk}`;
}

function updateConfidence(confidence) {
    const percent = Math.round(confidence * 100);
    document.getElementById('aiConfidence').textContent = `${percent}%`;
}

function updateWarnings(warnings) {
    const warningsList = document.getElementById('warningsList');
    warningsList.innerHTML = '';

    if (!warnings || warnings.length === 0) {
        warningsList.innerHTML = '<p class="no-warnings">現在、警告はありません</p>';
        return;
    }

    warnings.forEach(warning => {
        const item = document.createElement('div');
        item.className = 'warning-item';
        item.textContent = warning;
        warningsList.appendChild(item);
    });
}

function clearWarnings() {
    document.getElementById('warningsList').innerHTML = '<p class="no-warnings">現在、警告はありません</p>';
}

function clearInterventions() {
    document.getElementById('interventionsList').innerHTML = '<p class="no-interventions">介入なし</p>';
}

function logThinking(message, type = 'info') {
    const log = document.getElementById('thinkingLog');
    const item = document.createElement('p');
    item.className = `thinking-item ${type}`;
    const timestamp = new Date().toLocaleTimeString('ja-JP');
    item.textContent = `[${timestamp}] ${message}`;
    log.insertBefore(item, log.firstChild);
    
    // Keep only last 20 items
    while (log.children.length > 20) {
        log.removeChild(log.lastChild);
    }
}

function updateTime() {
    if (!isRunning) return;
    
    const elapsed = (Date.now() - startTime) / 1000;
    document.getElementById('time').textContent = `時間: ${elapsed.toFixed(1)}s`;
    
    if (!isPaused) {
        requestAnimationFrame(updateTime);
    }
}

function getInterventionIcon(type) {
    const icons = {
        'barrier': '🛡️',
        'slowdown': '🐢',
        'alert': '🚨',
        'evacuation': '🏃',
        'monitoring': '👁️'
    };
    return icons[type] || '⚙️';
}

function getInterventionLabel(type) {
    const labels = {
        'barrier': '安全バリア配置',
        'slowdown': 'ロボット減速',
        'alert': '警告表示',
        'evacuation': '緊急退避',
        'monitoring': '監視継続'
    };
    return labels[type] || '介入';
}

// Fetch and display memory stream
async function fetchMemoryStream() {
    try {
        const response = await fetch('/memory');
        const data = await response.json();
        displayMemoryStream(data);
    } catch (error) {
        console.error('Memory fetch error:', error);
    }
}

// Display memory stream
function displayMemoryStream(data) {
    const container = document.getElementById('memoryStream');
    if (!container) return;
    
    const { memories, reflections, stats } = data;
    
    let html = '';
    
    // Stats
    if (stats && stats.total_memories > 0) {
        html += '<div class="memory-stats">';
        html += `<span>総記憶数: ${stats.total_memories}</span> | `;
        html += `<span>平均重要度: ${stats.avg_importance?.toFixed(1) || 0}</span> | `;
        html += `<span>洞察: ${stats.reflections_count}</span>`;
        html += '</div>';
    }
    
    // Reflections
    if (reflections && reflections.length > 0) {
        html += '<div class="reflections-section">';
        html += '<h4>💡 高レベルな洞察（Reflection）</h4>';
        reflections.forEach(reflection => {
            html += `<div class="reflection-card">`;
            html += `<p>${reflection.content || reflection}</p>`;
            html += `</div>`;
        });
        html += '</div>';
    }
    
    // Memories
    if (memories && memories.length > 0) {
        html += '<div class="memories-section">';
        html += '<h4>📚 最近の記憶（最新5件）</h4>';
        const recentMemories = memories.slice(-5).reverse();
        recentMemories.forEach(mem => {
            const importanceStars = '⭐'.repeat(Math.min(Math.floor(mem.importance / 2), 5));
            const time = mem.timestamp ? new Date(mem.timestamp).toLocaleTimeString('ja-JP') : 'N/A';
            html += `<div class="memory-card importance-${mem.importance}">`;
            html += `<div class="memory-header">`;
            html += `<span class="memory-time">${time}</span>`;
            html += `<span class="memory-importance">${importanceStars}</span>`;
            html += `</div>`;
            html += `<div class="memory-obs">${mem.observation}</div>`;
            html += `<div class="memory-action">→ ${mem.action.type || 'N/A'} at [${Array.isArray(mem.action.position) ? mem.action.position.join(', ') : 'N/A'}]</div>`;
            html += `<div class="memory-outcome">${mem.outcome}</div>`;
            if (mem.learning_note) {
                html += `<div class="memory-learning">学び: ${mem.learning_note}</div>`;
            }
            html += `</div>`;
        });
        html += '</div>';
    } else {
        html += '<p class="no-memories">まだ記憶がありません</p>';
    }
    
    container.innerHTML = html;
}

// Event listeners
document.getElementById('startBtn').addEventListener('click', startSimulation);
document.getElementById('pauseBtn').addEventListener('click', pauseSimulation);
document.getElementById('resetBtn').addEventListener('click', resetSimulation);
document.getElementById('analyzeBtn').addEventListener('click', analyzeWithAI);

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    init();
    logThinking('TARS起動完了 - 準備OK', 'success');
});
