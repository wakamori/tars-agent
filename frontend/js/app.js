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

    } catch (error) {
        console.error('Analysis error:', error);
        logThinking(`分析エラー: ${error.message}`, 'error');
        
        // Try mock endpoint as fallback
        try {
            logThinking('モックデータを使用します...', 'warning');
            
            // Reuse the same blob for mock
            const mockFormData = new FormData();
            mockFormData.append('file', blob, 'factory-floor.png');
            
            const mockResponse = await fetch('/mock-analyze', {
                method: 'POST',
                body: mockFormData
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

// Process analysis results from Gemini
function processAnalysisResults(data) {
    if (!data) {
        logThinking('分析データが空です', 'error');
        return;
    }
    
    const { entities, warnings, interventions, confidence } = data;
    
    // Update confidence
    updateConfidence(confidence || 0);
    
    // Update warnings
    updateWarnings(warnings || []);
    
    // Calculate risk level
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
    
    // Apply interventions
    applyInterventions(interventions);
    
    const entityCount = entities ? entities.length : 0;
    logThinking(`検出: ${entityCount}個のエンティティ, リスク最大値: ${maxRisk}`, 'success');
}

// Apply safety interventions
function applyInterventions(interventions) {
    if (!interventions || interventions.length === 0) {
        logThinking('介入は不要です');
        return;
    }

    clearInterventions();
    const interventionsList = document.getElementById('interventionsList');
    interventionsList.innerHTML = '';

    interventions.forEach(intervention => {
        const { type, position, reason } = intervention;
        
        // Create intervention in simulation
        if (type === 'barrier' && position) {
            createSafetyBarrier(
                position[0] * CANVAS_WIDTH,
                position[1] * CANVAS_HEIGHT
            );
        }
        
        // Add to UI
        const item = document.createElement('div');
        item.className = 'intervention-item';
        item.innerHTML = `
            <strong>${getInterventionIcon(type)} ${getInterventionLabel(type)}</strong><br>
            ${reason}
        `;
        interventionsList.appendChild(item);
        
        logThinking(`${getInterventionLabel(type)}を実施: ${reason}`, 'success');
    });
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
        'alert': '🚨'
    };
    return icons[type] || '⚙️';
}

function getInterventionLabel(type) {
    const labels = {
        'barrier': '安全バリア配置',
        'slowdown': 'ロボット減速',
        'alert': '警告表示'
    };
    return labels[type] || '介入';
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
