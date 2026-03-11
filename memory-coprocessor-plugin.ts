/**
 * Memory Coprocessor Plugin
 * 
 * Purpose: Use local/small LLM to search memory and return structured summary
 * to main LLM for processing.
 * 
 * Architecture:
 *   User Prompt → [Local LLM: Memory Search] → Structured Summary → [Main LLM: Process] → Response
 */

import { api } from 'openclaw/plugin-sdk/core';

// ============================================================================
// Configuration
// ============================================================================

interface MemoryCoprocessorConfig {
  // Local model to use for memory search
  localModel: string;  // e.g., "ollama/qwen3.5:4b"
  
  // Main model for final processing
  mainModel: string;   // e.g., "minimax-portal/MiniMax-M2.5"
  
  // Maximum memory context to return
  maxMemoryTokens: number;
  
  // Whether to enable (can be toggled)
  enabled: boolean;
}

// Default configuration
const DEFAULT_CONFIG: MemoryCoprocessorConfig = {
  localModel: 'ollama/qwen3.5:4b',
  mainModel: 'minimax-portal/MiniMax-M2.5',
  maxMemoryTokens: 2000,
  enabled: true,
};

// ============================================================================
// Plugin Manifest
// ============================================================================

export const manifest = {
  id: 'memory-coprocessor',
  name: 'Memory Coprocessor',
  version: '0.1.0',
  description: 'Use local LLM to search memory and return structured summary to main LLM',
  
  configSchema: {
    type: 'object',
    properties: {
      localModel: {
        type: 'string',
        default: 'ollama/qwen3.5:4b',
        description: 'Local model for memory search'
      },
      mainModel: {
        type: 'string',
        default: 'minimax-portal/MiniMax-M2.5',
        description: 'Main model for processing'
      },
      maxMemoryTokens: {
        type: 'number',
        default: 2000,
        description: 'Maximum memory context tokens'
      },
      enabled: {
        type: 'boolean',
        default: true,
        description: 'Enable/disable coprocessor'
      }
    }
  },
  
  // Dependencies
  dependencies: [
    'lossless-claw'  // Uses Lossless Claw for memory access
  ]
};

// ============================================================================
// Memory Search Prompt
// ============================================================================

const MEMORY_SEARCH_PROMPT = `You are a memory search assistant. 
Given the user's prompt, search through the available memory and return relevant context.

Available memory sources:
- memory/*.md (long-term memory)
- Session context (recent conversations)

Return a STRUCTURED summary in this format:

\`\`\`json
{
  "relevant_facts": ["fact 1", "fact 2"],
  "past_decisions": ["decision with context"],
  "user_preferences": ["preference"],
  "confidence": "HIGH/MEDIUM/LOW",
  "sources": ["file or source name"],
  "summary": "2-3 sentence summary"
}
\`\`\`

User prompt: {{PROMPT}}

Search memory and return structured results.`;

// ============================================================================
// Plugin Class
// ============================================================================

export class MemoryCoprocessorPlugin {
  private config: MemoryCoprocessorConfig;
  private losslessClaw: any;  // Reference to Lossless Claw plugin
  
  constructor(api: any, config: MemoryCoprocessorConfig) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }
  
  // ========================================================================
  // Initialize - Get Lossless Claw reference
  // ========================================================================
  
  async initialize() {
    // Get reference to Lossless Claw plugin for memory access
    this.losslessClaw = await api.getPlugin('lossless-claw');
    
    if (!this.losslessClaw) {
      console.warn('Memory Coprocessor: Lossless Claw not found, using fallback');
    }
  }
  
  // ========================================================================
  // Core: Search Memory with Local LLM
  // ========================================================================
  
  async searchMemoryWithLocalLLM(prompt: string): Promise<MemorySearchResult> {
    // 1. Get recent context from Lossless Claw (if available)
    let memoryContext = '';
    
    if (this.losslessClaw) {
      memoryContext = await this.losslessClaw.getRecentContext(this.config.maxMemoryTokens);
    } else {
      // Fallback: Read from memory files directly
      memoryContext = await this.readMemoryFiles();
    }
    
    // 2. Prepare prompt for local LLM
    const searchPrompt = MEMORY_SEARCH_PROMPT
      .replace('{{PROMPT}}', prompt)
      .replace('{{MEMORY}}', memoryContext);
    
    // 3. Call local LLM (Ollama qwen3.5:4b)
    const localResult = await api.callModel({
      model: this.config.localModel,
      messages: [
        { role: 'user', content: searchPrompt }
      ],
      temperature: 0.3,  // Low temperature for factual recall
      maxTokens: 500
    });
    
    // 4. Parse structured response
    const structuredResult = this.parseStructuredResponse(localResult.content);
    
    return structuredResult;
  }
  
  // ========================================================================
  // Hook: Pre-prompt injection
  // ========================================================================
  
  async onPrePrompt(context: PromptContext): Promise<PromptContext> {
    if (!this.config.enabled) {
      return context;  // Skip if disabled
    }
    
    // Only process important prompts (not simple greetings/facts)
    if (!this.isImportantPrompt(context.prompt)) {
      return context;
    }
    
    try {
      // Search memory with local LLM
      const memoryResult = await this.searchMemoryWithLocalLLM(context.prompt);
      
      // Inject structured memory into context
      const memoryInjection = this.formatMemoryInjection(memoryResult);
      
      // Add to context messages
      context.messages.push({
        role: 'system',
        content: `[Memory Context] ${memoryInjection}`
      });
      
      // Add metadata for tracking
      context.metadata = {
        ...context.metadata,
        memoryCoprocessor: {
          used: true,
          confidence: memoryResult.confidence,
          sources: memoryResult.sources
        }
      };
      
    } catch (error) {
      console.error('Memory Coprocessor error:', error);
      // Continue without memory if error
    }
    
    return context;
  }
  
  // ========================================================================
  // Hook: Post-response tracking
  // ========================================================================
  
  async onPostResponse(context: ResponseContext): Promise<void> {
    // Log the memory usage for analysis
    if (context.metadata?.memoryCoprocessor?.used) {
      await this.logMemoryUsage({
        prompt: context.originalPrompt,
        response: context.response,
        memoryConfidence: context.metadata.memoryCoprocessor.confidence,
        sources: context.metadata.memoryCoprocessor.sources
      });
    }
  }
  
  // ========================================================================
  // Helper: Check if prompt is important
  // ========================================================================
  
  private isImportantPrompt(prompt: string): boolean {
    const importantKeywords = [
      'think', 'analyze', 'decide', 'plan', 'evaluate',
      'help me', 'what should', 'how do', 'why is',
      'research', 'build', 'create', 'debug'
    ];
    
    const promptLower = prompt.toLowerCase();
    return importantKeywords.some(keyword => promptLower.includes(keyword));
  }
  
  // ========================================================================
  // Helper: Read memory files (fallback)
  // ========================================================================
  
  private async readMemoryFiles(): Promise<string> {
    // Read from memory/*.md files
    const memoryDir = api.resolvePath('memory');
    const files = await api.listFiles(memoryDir, '*.md');
    
    let content = '';
    for (const file of files.slice(-5)) {  // Last 5 files
      content += await api.readFile(file) + '\n';
    }
    
    return content;
  }
  
  // ========================================================================
  // Helper: Parse structured response from local LLM
  // ========================================================================
  
  private parseStructuredResponse(response: string): MemorySearchResult {
    try {
      // Extract JSON from response
      const jsonMatch = response.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[1]);
      }
      
      // Fallback: return minimal structure
      return {
        relevant_facts: [response.substring(0, 200)],
        past_decisions: [],
        user_preferences: [],
        confidence: 'LOW',
        sources: [],
        summary: response.substring(0, 200)
      };
    } catch (error) {
      return {
        relevant_facts: [],
        past_decisions: [],
        user_preferences: [],
        confidence: 'LOW',
        sources: [],
        summary: 'Error parsing memory response'
      };
    }
  }
  
  // ========================================================================
  // Helper: Format memory for injection
  // ========================================================================
  
  private formatMemoryInjection(result: MemorySearchResult): string {
    return `
[Memory Search Results]
Confidence: ${result.confidence}
Sources: ${result.sources.join(', ') || 'None'}

Summary: ${result.summary}

Relevant Facts:
${result.relevant_facts.map(f => `- ${f}`).join('\n')}

Past Decisions:
${result.past_decisions.map(d => `- ${d}`).join('\n')}

User Preferences:
${result.user_preferences.map(p => `- ${p}`).join('\n')}
`.trim();
  }
  
  // ========================================================================
  // Helper: Log memory usage
  // ========================================================================
  
  private async logMemoryUsage(data: MemoryUsageLog): Promise<void> {
    const logFile = api.resolvePath('logs/memory-coprocessor.jsonl');
    await api.appendFile(logFile, JSON.stringify({
      timestamp: new Date().toISOString(),
      ...data
    }) + '\n');
  }
}

// ============================================================================
// Types
// ============================================================================

interface MemorySearchResult {
  relevant_facts: string[];
  past_decisions: string[];
  user_preferences: string[];
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  sources: string[];
  summary: string;
}

interface MemoryUsageLog {
  prompt: string;
  response: string;
  memoryConfidence: string;
  sources: string[];
}

// ============================================================================
// Export
// ============================================================================

export default function register(api: any) {
  const config = api.getConfig<MemoryCoprocessorConfig>('memory-coprocessor');
  
  const plugin = new MemoryCoprocessorPlugin(api, config);
  
  // Register hooks
  api.registerHook('prompt:pre', plugin.onPrePrompt.bind(plugin));
  api.registerHook('response:post', plugin.onPostResponse.bind(plugin));
  
  // Register command
  api.registerCommand({
    name: 'memory-coprocessor',
    description: 'Memory Coprocessor status and controls',
    execute: async (args: string[]) => {
      if (args[0] === 'enable') {
        config.enabled = true;
        return 'Memory Coprocessor enabled';
      } else if (args[0] === 'disable') {
        config.enabled = false;
        return 'Memory Coprocessor disabled';
      } else {
        return `Status: ${config.enabled ? 'enabled' : 'disabled'}\nLocal: ${config.localModel}\nMain: ${config.mainModel}`;
      }
    }
  });
  
  return plugin;
}
