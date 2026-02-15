/**
 * TARS - World Model Experiment: Physics Simulation
 * 
 * 倉庫番タスク用の物理シミュレーション
 * 重力・摩擦・弾性を考慮した荷物移動シミュレーション
 */

import * as Matter from "matter-js";

// Matter.js aliases
const Engine = Matter.Engine;
const Render = Matter.Render;
const World = Matter.World;
const Bodies = Matter.Bodies;
const Body = Matter.Body;
const Events = Matter.Events;
const Runner = Matter.Runner;

// ==================== Types ====================

export interface Point {
  x: number;
  y: number;
}

export interface BoxPhysics {
  mass: number;
  friction: number;
  restitution: number;
  frictionAir: number;
}

export interface LevelConfig {
  name: string;
  description: string;
  boxPosition: Point;
  goalPosition: Point;
  boxPhysics: BoxPhysics;
  timeLimit: number;
  maxSteps: number;
  availableBarriers: number;
  obstacles: Obstacle[];
}

export interface Obstacle {
  type: 'wall' | 'pit';
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SimulationState {
  box: {
    position: Point;
    velocity: Point;
  };
  goal: {
    position: Point;
    radius: number;
  };
  step: number;
  elapsedTime: number;
  isSuccess: boolean;
  isFailure: boolean;
}

export type ActionType = 'push' | 'barrier' | 'wait' | 'observe';

export interface Action {
  type: ActionType;
  forceX?: number;
  forceY?: number;
  duration?: number;
  x?: number;
  y?: number;
  angle?: number;
  reason?: string;
  focus?: string;
}

// ==================== Level Definitions ====================

export const LEVELS: { [key: string]: LevelConfig } = {
  tutorial: {
    name: '基礎：直線移動',
    description: '荷物を右に押してゴールへ',
    boxPosition: { x: 200, y: 300 },
    goalPosition: { x: 600, y: 300 },
    boxPhysics: {
      mass: 10,
      friction: 0.5,
      restitution: 0.3,
      frictionAir: 0.05, // 空気抵抗を増やして速度を自然に減衰
    },
    timeLimit: 60,
    maxSteps: 20,
    availableBarriers: 0,
    obstacles: [],
  },
  friction: {
    name: '物理：摩擦係数',
    description: '滑りやすい荷物をコントロール',
    boxPosition: { x: 200, y: 300 },
    goalPosition: { x: 600, y: 300 },
    boxPhysics: {
      mass: 10,
      friction: 0.1, // 非常に滑る
      restitution: 0.3,
      frictionAir: 0.05, // 空気抵抗で速度制御
    },
    timeLimit: 80,
    maxSteps: 30,
    availableBarriers: 0,
    obstacles: [],
  },
  obstacle: {
    name: '障害：壁の回避',
    description: '壁を避けてゴールへ',
    boxPosition: { x: 200, y: 300 },
    goalPosition: { x: 600, y: 300 },
    boxPhysics: {
      mass: 10,
      friction: 0.5,
      restitution: 0.3,
      frictionAir: 0.05, // 空気抵抗で速度制御
    },
    timeLimit: 100,
    maxSteps: 40,
    availableBarriers: 0,
    obstacles: [
      { type: 'wall', x: 400, y: 200, width: 20, height: 400 },
    ],
  },
  barrier: {
    name: '戦略：誘導路作成',
    description: 'バリアで滑り台を作り、安全にゴールへ',
    boxPosition: { x: 200, y: 100 },
    goalPosition: { x: 600, y: 500 },
    boxPhysics: {
      mass: 10,
      friction: 0.3,
      restitution: 0.3,
      frictionAir: 0.05, // 空気抵抗で速度制御
    },
    timeLimit: 120,
    maxSteps: 50,
    availableBarriers: 3,
    obstacles: [
      { type: 'pit', x: 400, y: 550, width: 100, height: 50 },
    ],
  },
};

// ==================== Simulation Class ====================

export class WarehouseSimulation {
  private engine: Matter.Engine;
  private render: Matter.Render;
  private runner: Matter.Runner;
  private world: Matter.World;

  private box: Matter.Body | null = null;
  private goal: { body: Matter.Body; radius: number } | null = null;
  private ground: Matter.Body | null = null;
  private walls: Matter.Body[] = [];
  private barriers: Matter.Body[] = [];
  private obstacles: Matter.Body[] = [];

  private currentLevel: LevelConfig;
  private step: number = 0;
  private startTime: number = 0;
  private isRunning: boolean = false;
  private isPaused: boolean = false;
  
  // Timer pause tracking (for AI thinking time)
  private pausedTime: number = 0; // Total paused time in milliseconds
  private pauseStartTime: number | null = null; // When pause started

  // Canvas dimensions
  private readonly CANVAS_WIDTH = 800;
  private readonly CANVAS_HEIGHT = 600;

  constructor(canvas: HTMLElement, levelKey: string = 'tutorial') {
    this.currentLevel = (LEVELS[levelKey] || LEVELS.tutorial)!;

    // Create engine with custom gravity
    this.engine = Engine.create();
    this.world = this.engine.world;
    this.world.gravity.y = 1.0; // 下向きの重力

    // Create renderer
    this.render = Render.create({
      element: canvas,
      engine: this.engine,
      options: {
        width: this.CANVAS_WIDTH,
        height: this.CANVAS_HEIGHT,
        wireframes: false,
        background: '#1a1a2e',
      },
    });

    // Create runner
    this.runner = Runner.create();

    // Initialize world
    this.initWorld();
  }

  private initWorld(): void {
    // Clear existing bodies
    World.clear(this.world, false);
    this.barriers = [];
    this.obstacles = [];
    this.step = 0;

    const WALL_THICKNESS = 30; // Unified wall thickness for all boundaries

    // Create ground
    this.ground = Bodies.rectangle(
      this.CANVAS_WIDTH / 2,
      this.CANVAS_HEIGHT - WALL_THICKNESS / 2,
      this.CANVAS_WIDTH,
      WALL_THICKNESS,
      {
        isStatic: true,
        render: {
          fillStyle: '#2a2a3e',
        },
      }
    );

    // Create walls (left, right, and ceiling boundaries with unified thickness)
    const leftWall = Bodies.rectangle(
      WALL_THICKNESS / 2,
      this.CANVAS_HEIGHT / 2,
      WALL_THICKNESS,
      this.CANVAS_HEIGHT,
      {
        isStatic: true,
        render: {
          fillStyle: '#2a2a3e',
        },
      }
    );

    const rightWall = Bodies.rectangle(
      this.CANVAS_WIDTH - WALL_THICKNESS / 2 + 1,  // Slight offset to fill gap
      this.CANVAS_HEIGHT / 2,
      WALL_THICKNESS + 2,  // Slightly wider to ensure no gap
      this.CANVAS_HEIGHT,
      {
        isStatic: true,
        render: {
          fillStyle: '#2a2a3e',
        },
      }
    );

    const ceiling = Bodies.rectangle(
      this.CANVAS_WIDTH / 2,
      WALL_THICKNESS / 2,
      this.CANVAS_WIDTH,
      WALL_THICKNESS,
      {
        isStatic: true,
        render: {
          fillStyle: '#2a2a3e',
        },
      }
    );

    this.walls = [leftWall, rightWall, ceiling];

    // Create box (荷物)
    const { boxPosition, boxPhysics } = this.currentLevel;
    this.box = Bodies.rectangle(
      boxPosition.x,
      boxPosition.y,
      40,
      40,
      {
        density: boxPhysics.mass / (40 * 40), // 質量から密度を計算
        friction: boxPhysics.friction,
        restitution: boxPhysics.restitution,
        frictionAir: boxPhysics.frictionAir,
        render: {
          fillStyle: '#4169E1', // Royal Blue
          strokeStyle: '#ffffff',
          lineWidth: 2,
        },
      }
    );

    // Create goal (ゴール)
    const { goalPosition } = this.currentLevel;
    const goalRadius = 30;
    this.goal = {
      body: Bodies.circle(goalPosition.x, goalPosition.y, goalRadius, {
        isStatic: true,
        isSensor: true, // 衝突を検知するが物理的には通過可能
        render: {
          fillStyle: '#FFD700', // Gold
          opacity: 0.5,
        },
      }),
      radius: goalRadius,
    };

    // Create obstacles
    for (const obs of this.currentLevel.obstacles) {
      let body: Matter.Body;

      if (obs.type === 'wall') {
        body = Bodies.rectangle(
          obs.x + obs.width / 2,
          obs.y + obs.height / 2,
          obs.width,
          obs.height,
          {
            isStatic: true,
            render: {
              fillStyle: '#8B0000', // Dark Red
            },
          }
        );
      } else if (obs.type === 'pit') {
        body = Bodies.rectangle(
          obs.x + obs.width / 2,
          obs.y + obs.height / 2,
          obs.width,
          obs.height,
          {
            isStatic: true,
            isSensor: true,
            render: {
              fillStyle: '#000000',
              opacity: 0.8,
            },
          }
        );
      }

      this.obstacles.push(body!);
    }

    // Add all bodies to world
    World.add(this.world, [
      this.ground,
      ...this.walls,
      this.box,
      this.goal.body,
      ...this.obstacles,
    ]);

    // Setup collision detection for goal
    this.setupCollisionDetection();
  }

  private setupCollisionDetection(): void {
    Events.on(this.engine, 'collisionStart', (event) => {
      const pairs = event.pairs;

      for (const pair of pairs) {
        // Check if box reached goal
        if (
          (pair.bodyA === this.box && pair.bodyB === this.goal?.body) ||
          (pair.bodyB === this.box && pair.bodyA === this.goal?.body)
        ) {
          console.log('🎯 Goal reached!');
          this.onGoalReached();
        }

        // Check if box fell into pit
        for (const obstacle of this.obstacles) {
          if (
            (pair.bodyA === this.box && pair.bodyB === obstacle) ||
            (pair.bodyB === this.box && pair.bodyA === obstacle)
          ) {
            console.log('💀 Box fell into pit!');
            this.onFailure('Fell into pit');
          }
        }
      }
    });
  }

  // ==================== Public API ====================

  public start(): void {
    if (!this.isRunning) {
      this.isRunning = true;
      this.startTime = Date.now();
      Render.run(this.render);
      Runner.run(this.runner, this.engine);
      console.log(`🚀 Simulation started: ${this.currentLevel.name}`);
    }
  }

  public pause(): void {
    if (this.isRunning && !this.isPaused) {
      this.isPaused = true;
      Runner.stop(this.runner);
      console.log('⏸️  Simulation paused');
    }
  }

  public resume(): void {
    if (this.isRunning && this.isPaused) {
      this.isPaused = false;
      Runner.run(this.runner, this.engine);
      console.log('▶️  Simulation resumed');
    }
  }

  public reset(levelKey?: string): void {
    if (levelKey && LEVELS[levelKey]) {
      this.currentLevel = LEVELS[levelKey];
    }

    Runner.stop(this.runner);
    this.initWorld();
    this.step = 0;
    this.startTime = 0;
    this.isRunning = false;
    this.isPaused = false;
    this.pausedTime = 0;
    this.pauseStartTime = null;

    console.log(`🔄 Reset to: ${this.currentLevel.name}`);
  }

  public executeAction(action: Action): void {
    if (!this.box || this.isPaused) return;

    this.step++;
    
    console.log('🎬 Executing action:', JSON.stringify(action));

    switch (action.type) {
      case 'push':
        this.applyForce(action.forceX || 0, action.forceY || 0, action.duration || 1000);
        break;

      case 'barrier':
        this.placeBarrier(action.x || 0, action.y || 0, action.angle || 0);
        break;

      case 'wait':
        console.log(`⏳ Waiting: ${action.reason}`);
        break;

      case 'observe':
        console.log(`👁️  Observing: ${action.focus}`);
        break;
    }
  }

  private applyForce(forceX: number, forceY: number, duration: number): void {
    if (!this.box) return;

    console.log(`⚡ applyForce input: forceX=${forceX}, forceY=${forceY}, duration=${duration}`);

    // Matter.js force scale: 0.02 provides controlled movement
    // With frictionAir=0.05, velocity naturally decays
    // forceX=50 → actual force=1.0 (gradual acceleration)
    const force = { x: forceX * 0.02, y: forceY * 0.02 };
    Body.applyForce(this.box, this.box.position, force);

    console.log(`💨 Push applied: force=(${force.x.toFixed(6)}, ${force.y.toFixed(6)})`);
  }

  private placeBarrier(x: number, y: number, angle: number): void {
    if (this.barriers.length >= this.currentLevel.availableBarriers) {
      console.log('❌ No more barriers available');
      return;
    }

    const barrier = Bodies.rectangle(x, y, 150, 10, {
      isStatic: true,
      angle: (angle * Math.PI) / 180, // Convert to radians
      render: {
        fillStyle: '#FF6B6B', // Red barrier
      },
    });

    this.barriers.push(barrier);
    World.add(this.world, barrier);

    console.log(`🚧 Barrier placed at (${x}, ${y}) with angle ${angle}°`);
  }

  public getState(): SimulationState {
    let elapsedTime = 0;
    if (this.isRunning) {
      if (this.pauseStartTime !== null) {
        // Timer is paused - use pause start time
        elapsedTime = (this.pauseStartTime - this.startTime - this.pausedTime) / 1000;
      } else {
        // Timer is running - exclude paused time
        elapsedTime = (Date.now() - this.startTime - this.pausedTime) / 1000;
      }
    }

    return {
      box: {
        position: { x: this.box?.position.x || 0, y: this.box?.position.y || 0 },
        velocity: { x: this.box?.velocity.x || 0, y: this.box?.velocity.y || 0 },
      },
      goal: {
        position: {
          x: this.goal?.body.position.x || 0,
          y: this.goal?.body.position.y || 0,
        },
        radius: this.goal?.radius || 30,
      },
      step: this.step,
      elapsedTime: elapsedTime,
      isSuccess: this.checkSuccess(),
      isFailure: this.checkFailure(),
    };
  }

  public captureScreenshot(): string {
    const canvas = this.render.canvas;
    return canvas.toDataURL('image/png');
  }

  public getPhysicsInfo(): BoxPhysics {
    return this.currentLevel.boxPhysics;
  }

  public getLevelInfo(): LevelConfig {
    return this.currentLevel;
  }

  // Timer control for AI thinking (excludes AI time from elapsed time)
  public pauseTimer(): void {
    if (this.isRunning && this.pauseStartTime === null) {
      this.pauseStartTime = Date.now();
      console.log('⏸️  Timer paused for AI thinking');
    }
  }

  public resumeTimer(): void {
    if (this.isRunning && this.pauseStartTime !== null) {
      this.pausedTime += Date.now() - this.pauseStartTime;
      this.pauseStartTime = null;
      console.log('▶️  Timer resumed after AI thinking');
    }
  }

  // ==================== Private Helpers ====================

  private checkSuccess(): boolean {
    if (!this.box || !this.goal) return false;

    const distance = this.euclideanDistance(
      this.box.position,
      this.goal.body.position
    );

    return distance < this.goal.radius;
  }

  private checkFailure(): boolean {
    if (!this.box) return false;

    // Calculate elapsed time excluding paused time (same logic as getState)
    let elapsedTime = 0;
    if (this.isRunning) {
      if (this.pauseStartTime !== null) {
        // Timer is paused - use pause start time
        elapsedTime = (this.pauseStartTime - this.startTime - this.pausedTime) / 1000;
      } else {
        // Timer is running - exclude paused time
        elapsedTime = (Date.now() - this.startTime - this.pausedTime) / 1000;
      }
    }

    // Out of bounds (fell off screen)
    if (this.box.position.y > this.CANVAS_HEIGHT) {
      return true;
    }

    // Timeout
    if (elapsedTime > this.currentLevel.timeLimit) {
      return true;
    }

    // Max steps exceeded
    if (this.step >= this.currentLevel.maxSteps) {
      return true;
    }

    return false;
  }

  private euclideanDistance(p1: { x: number; y: number }, p2: { x: number; y: number }): number {
    return Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);
  }

  private onGoalReached(): void {
    console.log('✅ Task completed successfully!');
    const state = this.getState();
    console.log(`Steps: ${state.step}, Time: ${state.elapsedTime.toFixed(2)}s`);
    this.pause();
  }

  private onFailure(reason: string): void {
    console.log(`❌ Task failed: ${reason}`);
    this.pause();
  }

  public destroy(): void {
    Render.stop(this.render);
    Runner.stop(this.runner);
    World.clear(this.world, false);
    Engine.clear(this.engine);
    this.render.canvas.remove();
    this.render.textures = {};
  }
}
