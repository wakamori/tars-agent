/**
 * Type definitions for TARS Agent API
 */

// API Response Types

export interface AccidentScenario {
  scenario: string;
  probability: number;
  severity: number;
  reasoning: string;
}

export interface SelfInquiry {
  observations: string[];
  memory_connections: string[];
  accident_scenarios: AccidentScenario[];
  causal_analysis: string;
}

export interface Entity {
  type: string;
  position: [number, number];
  risk_level: number;
  reasoning: string;
}

export interface DiscoveredPattern {
  pattern_name: string;
  description: string;
  indicators: string[];
  is_novel: boolean;
}

export interface InterventionAction {
  type: "barrier" | "slowdown" | "alert" | "evacuation" | "monitoring";
  position: [number, number] | null;
  reasoning: string;
  expected_outcome: string;
}

export interface InterventionDecision {
  primary_action: InterventionAction;
  alternative_actions: InterventionAction[];
  priority: number;
}

export interface AgentResponse {
  self_inquiry: SelfInquiry;
  entities: Entity[];
  discovered_patterns: DiscoveredPattern[];
  intervention_decision: InterventionDecision;
  confidence: number;
  learning_note: string;
}

// Memory API Types

export interface Memory {
  observation: string;
  action: {
    type: string;
    position: number[] | null;
  };
  outcome: string;
  importance: number;
  timestamp: string;
  learning_note?: string;
}

export interface MemoryStats {
  total_memories: number;
  avg_importance: number;
  reflections_count: number;
}

export interface MemoryResponse {
  memories: Memory[];
  reflections: string[];
  stats: MemoryStats;
}

