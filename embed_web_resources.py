#!/usr/bin/env python3
"""
Chunk and store web resources into pgvector cognitive memory.
Usage: python3 embed_web_resources.py
"""

import os
import sys
import json
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '/Users/danieltekippe/.openclaw/workspace')
from cognitive_memory import store_memory

SOURCE_TYPE = 'web_ref'
IMPORTANCE = 8.0
TTL_DAYS = 365

def chunk_text(text: str, chunk_size: int = 512) -> list[str]:
    char_limit = chunk_size * 4
    chunks = []
    paragraphs = text.split('\n\n')
    current = []
    current_len = 0
    
    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > char_limit and current:
            chunks.append('\n\n'.join(current))
            current = [para]
            current_len = para_len
        else:
            current.append(para)
            current_len += para_len + 2
    
    if current:
        chunks.append('\n\n'.join(current))
    return [c for c in chunks if len(c.strip()) >= 50]

def store_web_resource(url: str, title: str, content: str, tags: list[str]):
    chunks = chunk_text(content, chunk_size=512)
    print(f"\n📄 {title}")
    print(f"   URL: {url}")
    print(f"   {len(content)} chars → {len(chunks)} chunks")
    
    stored = 0
    for i, chunk in enumerate(chunks):
        metadata = {
            'source_type': SOURCE_TYPE,
            'source_url': url,
            'title': title,
            'chunk_index': i,
            'total_chunks': len(chunks),
            'tags': tags,
            'importance': IMPORTANCE,
            'ttl_days': TTL_DAYS
        }
        
        result = store_memory(
            user_id='00000000-0000-0000-0000-000000000001',
            content=chunk,
            namespace='fact',
            importance=IMPORTANCE,
            ttl_days=TTL_DAYS,
            metadata=metadata
        )
        
        if result:
            stored += 1
            print(f"   ✓ Chunk {i+1}/{len(chunks)}")
    
    print(f"   Stored: {stored}/{len(chunks)}")
    return stored

def main():
    resources = [
        {
            'url': 'https://docs.openclaw.ai/automation/hooks',
            'title': 'OpenClaw Hooks Documentation',
            'content': '''OpenClaw Hooks System - Event-driven automation for agent commands and events.

EVENT TYPES:
- Command Events: command:new, command:reset, command:stop
- Session Events: session:compact:before, session:compact:after  
- Agent Events: agent:bootstrap
- Gateway Events: gateway:startup
- Message Events: message:received, message:transcribed, message:preprocessed, message:sent

HOOK STRUCTURE:
- HOOK.md: YAML frontmatter metadata + documentation
- handler.ts: HookHandler function implementation

HANDLER PATTERN:
const handler = async (event) => {
  if (event.type !== "command" || event.action !== "new") return;
  console.log(`[hook] Event triggered`);
  event.messages.push("Hook executed!");
};
export default handler;

CLI COMMANDS:
- openclaw hooks list: List all hooks
- openclaw hooks enable <name>: Enable hook
- openclaw hooks disable <name>: Disable hook
- openclaw hooks info <name>: Show details

DISCOVERY DIRECTORIES:
1. Workspace: <workspace>/hooks/
2. Managed: ~/.openclaw/hooks/
3. Bundled: <openclaw>/dist/hooks/bundled/

BUNDLED HOOKS:
- session-memory: Saves context when /new issued
- bootstrap-extra-files: Injects additional bootstrap files
- command-logger: Logs commands to audit file
- boot-md: Runs BOOT.md at gateway startup

BEST PRACTICES:
- Keep handlers fast (async, non-blocking)
- Handle errors gracefully (try/catch)
- Filter events early (return if not relevant)
- Use specific event keys (command:new not command)

CREATE CUSTOM HOOK:
1. mkdir -p ~/.openclaw/hooks/my-hook
2. Create HOOK.md with metadata
3. Create handler.ts with HookHandler
4. openclaw hooks enable my-hook
5. Restart gateway
''',
            'tags': ['openclaw', 'hooks', 'automation', 'events']
        },
        {
            'url': 'https://www.codecademy.com/learn/learn-reinforcement-learning-with-gymnasium',
            'title': 'Codecademy Gymnasium RL Course',
            'content': '''Learn Reinforcement Learning with Gymnasium - Codecademy Course

COURSE OVERVIEW:
Build learning agents using reinforcement learning algorithms. Implement Q-learning and SARSA using Python and Gymnasium. Design and customize RL environments. Apply Monte Carlo methods.

SKILLS GAINED:
- Build learning agents using RL algorithms
- Implement Q-learning and SARSA with Python and Gymnasium
- Design custom Gymnasium environments
- Apply Monte Carlo methods from episodic experiences
- Solve CartPole, FrozenLake, Twenty-One, multi-armed bandits

KEY CONCEPTS:
- Agent-environment loop: agents learn through trial and error
- Reward systems: maximize cumulative rewards over time
- Policy optimization: discover optimal strategies
- Q-learning: off-policy TD control algorithm
- SARSA: on-policy TD control algorithm
- Monte Carlo: learn from episodic experiences
- Gymnasium: RL environment library (formerly OpenAI Gym)

PROJECTS:
- Solve Twenty-One with RL (Q-learning, SARSA)
- Solve Cart Pole with RL (Monte Carlo methods)

PREREQUISITES:
- Intermediate Python 3
- Basic understanding of ML concepts

CARTPOLE EXAMPLE:
Classic RL benchmark where agent balances pole on moving cart. Used to test policy gradient and value function methods.

FROZENLAKE:
Gridworld environment where agent navigates frozen lake to reach goal. Demonstrates stochastic environments and value iteration.

Q-LEARNING UPDATE RULE:
Q(s,a) = Q(s,a) + alpha * (r + gamma * max(Q(s',a')) - Q(s,a))

SARSA UPDATE RULE:
Q(s,a) = Q(s,a) + alpha * (r + gamma * Q(s',a') - Q(s,a))

GYMNASIUM API:
env = gymnasium.make('CartPole-v1')
observation, info = env.reset()
action = env.action_space.sample()
observation, reward, terminated, truncated, info = env.step(action)
''',
            'tags': ['reinforcement-learning', 'gymnasium', 'q-learning', 'sarsa', 'monte-carlo', 'python']
        },
        {
            'url': 'https://advancedsportslogic.com/nfl/',
            'title': 'Advanced Sports Logic NFL Dynasty Resources',
            'content': '''Advanced Sports Logic - Fantasy NFL Analysis and Draft Strategy

WEEKLY RANKINGS:
- Top 25 QB rankings
- Top 40 RB rankings  
- Top 50 WR rankings
- Top 25 TE rankings
- Top 70 FLEX rankings
- Top 25 DEF rankings

START/SIT DECISIONS:
- Weekly Starts and Sits for championship weeks
- Value plays for daily fantasy
- Matchup analysis

SUPERFLEX STRATEGY:
- 2 QB formats increase QB value significantly
- QB1 tier players become elite assets
- Streaming QBs viable but ceiling limited

DYNASTY DRAFT VALUE:
- Rookie picks have high variance but potential elite returns
- 2026 draft class: premium on QB, RB, WR depending on landing spot
- Trade value: future 2nds can be packaged to move up

KEY PRINCIPLES:
- Best ball tournaments: volume and consistency matter
- Dynasty: win-now vs rebuild should drive all decisions
- Trade evaluation: compare asset value charts (KTC, DynastyProcess)
- Draft strategy: zero-RB and hero-RB both viable depending on ADPs

FF Martketplace dynamics:
- Contender mode: acquire veteran talent, win now
- Rebuild mode: accumulate picks and young players
- Target players whose team situation improving
''',
            'tags': ['fantasy-football', 'dynasty', 'draft', 'rankings', 'strategy']
        }
    ]
    
    total = 0
    for r in resources:
        stored = store_web_resource(
            url=r['url'],
            title=r['title'],
            content=r['content'],
            tags=r['tags']
        )
        total += stored
    
    print(f"\n✅ Total chunks stored: {total}")

if __name__ == '__main__':
    main()
