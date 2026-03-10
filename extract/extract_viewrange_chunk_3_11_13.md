steps, but the answers are limited to Yes/No responses [7]. As the industry continues to pivot towards agent focused
use-cases additional measures will be needed to better assess the performance and generalizability of agents to tasks
involving tools that extend beyond their training data.
Some agent specific benchmarks like AgentBench evaluate language model-based agents in a variety of different
environments such as web browsing, command-line interfaces, and video games [17]. This provides a better indication
for how well agents can generalize to new environments, by reasoning, planning, and calling tools to achieve a given
task. Benchmarks like AgentBench and SmartPlay introduce objective evaluation metrics designed to evaluate the
implementation’s success rate, output similarity to human responses, and overall efficiency [17, 30]. While these
objective metrics are important to understanding the overall reliability and accuracy of the implementation, it is also
important to consider more nuanced or subjective measures of performance. Metrics such as efficiency of tool use,
reliability, and robustness of planning are nearly as important as success rate but are much more difficult to measure.
Many of these metrics require evaluation by a human expert, which can be costly and time consuming compared to
LLM-as-judge evaluations.
6.5 Real-world Applicability
Many of the existing benchmarks focus on the ability of Agent systems to reason over logic puzzles or video games
[17]. While evaluating performance on these types of tasks can help get a sense of the reasoning capabilities of agent
systems, it is unclear whether performance on these benchmarks translates to real-world performance. Specifically,
real-world data can be noisy and cover a much wider breadth of topics that many common benchmarks lack.
One popular benchmark that uses real-world data is WildBench, which is sourced from the WildChat dataset of 570,000
real conversations with ChatGPT [35]. Because of this, it covers a huge breadth of tasks and prompts. While WildBench
covers a wide range of topics, most other real-world benchmarks focus on a specific task. For example, SWE-bench is a
benchmark that uses a set of real-world issues raised on GitHub for software engineering tasks in Python [13]. This
can be very helpful when evaluating agents designed to write Python code and provides a sense for how well agents
can reason about code related problems; however, it is less informative when trying to understand agent capabilities
involving other programming languages.
6.6 Bias and Fairness in Agent Systems
Language Models have been known to exhibit bias both in terms of evaluation as well as in social or fairness terms [5].
Moreover, agents have specifically been shown to be “less robust, prone to more harmful behaviors, and capable of
generating stealthier content than LLMs, highlighting significant safety challenges” [25]. Other research has found “a
tendency for LLM agents to conform to the model’s inherent social biases despite being directed to debate from certain
political perspectives” [24]. This tendency can lead to faulty reasoning in any agent-based implementation.
As the complexity of tasks and agent involvement increases, more research is needed to identify and address biases
within these systems. This poses a very large challenge to researchers, since scalable and novel benchmarks often
involve some level of LLM involvement during creation. However, a truly robust benchmark for evaluating bias in
LLM-based agents must include human evaluation.
7 Conclusion and Future Directions
The AI agent implementations explored in this survey demonstrate the rapid enhancement in language model powered
reasoning, planning, and tool calling. Single and multi-agent patterns both show the ability to tackle complex multi-step
problems that require advanced problem-solving skills. The key insights discussed in this paper suggest that the best
agent architecture varies based on use case. Regardless of the architecture selected, the best performing agent systems
tend to incorporate at least one of the following approaches: well defined system prompts, clear leadership and task
division, dedicated reasoning / planning- execution - evaluation phases, dynamic team structures, human or agentic
feedback, and intelligent message filtering. Architectures that leverage these techniques are more effective across a
variety of benchmarks and problem types.
While the current state of AI-driven agents is promising, there are notable limitations and areas for future improvement.
Challenges around comprehensive agent benchmarks, real world applicability, and the mitigation of harmful language
model biases will need to be addressed in the near-term to enable reliable agents. By examining the progression from
static language models to more dynamic, autonomous agents, this survey aims to provide a holistic understanding of the
current AI agent landscape and offer insight for those building with existing agent architectures or developing custom
agent architectures.
11

References
[1] Timo Birr et al. AutoGPT+P: Affordance-based Task Planning with Large Language Models . arXiv:2402.10778
[cs] version: 1. Feb. 2024. URL:http://arxiv.org/abs/2402.10778 .
[2] Weize Chen et al. AgentVerse: Facilitating Multi-Agent Collaboration and Exploring Emergent Behaviors .
arXiv:2308.10848 [cs]. Oct. 2023. URL:http://arxiv.org/abs/2308.10848 .
[3] Karl Cobbe et al. Training Verifiers to Solve Math Word Problems . arXiv:2110.14168 [cs]. Nov. 2021. URL:
http://arxiv.org/abs/2110.14168 .
[4] Xueyang Feng et al. Large Language Model-based Human-Agent Collaboration for Complex Task Solving . 2024.
arXiv: 2402.12914 [cs.CL] .
[5] Isabel O. Gallegos et al. Bias and Fairness in Large Language Models: A Survey . arXiv:2309.00770 [cs]. Mar.
2024. URL:http://arxiv.org/abs/2309.00770 .
[6] Silin Gao et al. Efficient Tool Use with Chain-of-Abstraction Reasoning . arXiv:2401.17464 [cs]. Feb. 2024. URL:
http://arxiv.org/abs/2401.17464 .
[7] Mor Geva et al. Did Aristotle Use a Laptop? A Question Answering Benchmark with Implicit Reasoning Strategies .
arXiv:2101.02235 [cs]. Jan. 2021. URL:http://arxiv.org/abs/2101.02235 .
[8] Shahriar Golchin and Mihai Surdeanu. Time Travel in LLMs: Tracing Data Contamination in Large Language
Models . arXiv:2308.08493 [cs] version: 3. Feb. 2024. URL:http://arxiv.org/abs/2308.08493 .
[9] Xudong Guo et al. Embodied LLM Agents Learn to Cooperate in Organized Teams . 2024. arXiv: 2403.12482
[cs.AI] .
[10] Dan Hendrycks et al. Measuring Massive Multitask Language Understanding . arXiv:2009.03300 [cs]. Jan. 2021.
URL:http://arxiv.org/abs/2009.03300 .
[11] Sirui Hong et al. MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework . 2023. arXiv:
2308.00352 [cs.AI] .
[12] Xu Huang et al. Understanding the planning of LLM agents: A survey . 2024. arXiv: 2402.02716 [cs.AI] .
[13] Carlos E. Jimenez et al. SWE-bench: Can Language Models Resolve Real-World GitHub Issues?
arXiv:2310.06770 [cs]. Oct. 2023. URL:http://arxiv.org/abs/2310.06770 .
[14] Fangyu Lei et al. S3Eval: A Synthetic, Scalable, Systematic Evaluation Suite for Large Language Models .
arXiv:2310.15147 [cs]. Oct. 2023. URL:http://arxiv.org/abs/2310.15147 .
[15] Fangru Lin et al. Graph-enhanced Large Language Models in Asynchronous Plan Reasoning . arXiv:2402.02805
[cs]. Feb. 2024. URL:http://arxiv.org/abs/2402.02805 .
[16] Na Liu et al. From LLM to Conversational Agent: A Memory Enhanced Architecture with Fine-Tuning of Large
Language Models . arXiv:2401.02777 [cs]. Jan. 2024. URL:http://arxiv.org/abs/2401.02777 .
[17] Xiao Liu et al. AgentBench: Evaluating LLMs as Agents . arXiv:2308.03688 [cs]. Oct. 2023. URL:http :
//arxiv.org/abs/2308.03688 .
[18] Zijun Liu et al. Dynamic LLM-Agent Network: An LLM-agent Collaboration Framework with Agent Team
Optimization . 2023. arXiv: 2310.02170 [cs.CL] .
[19] Yohei Nakajima. yoheinakajima/babyagi . original-date: 2023-04-03T00:40:27Z. Apr. 2024. URL:https://
github.com/yoheinakajima/babyagi .
[20] Peter S. Park et al. AI Deception: A Survey of Examples, Risks, and Potential Solutions . arXiv:2308.14752 [cs].
Aug. 2023. URL:http://arxiv.org/abs/2308.14752 .
[21] Greg Serapio-García et al. Personality Traits in Large Language Models . 2023. arXiv: 2307.00184 [cs.CL] .
[22] Zhengliang Shi et al. Learning to Use Tools via Cooperative and Interactive Agents . arXiv:2403.03031 [cs]. Mar.
2024. URL:http://arxiv.org/abs/2403.03031 .
[23] Noah Shinn et al. Reflexion: Language Agents with Verbal Reinforcement Learning . arXiv:2303.11366 [cs]. Oct.
2023. URL:http://arxiv.org/abs/2303.11366 .
[24] Amir Taubenfeld et al. Systematic Biases in LLM Simulations of Debates . arXiv:2402.04049 [cs]. Feb. 2024.
URL:http://arxiv.org/abs/2402.04049 .
[25] Yu Tian et al. Evil Geniuses: Delving into the Safety of LLM-based Agents . arXiv:2311.11855 [cs]. Feb. 2024.
URL:http://arxiv.org/abs/2311.11855 .
[26] Qineng Wang et al. Rethinking the Bounds of LLM Reasoning: Are Multi-Agent Discussions the Key?
arXiv:2402.18272 [cs]. Feb. 2024. URL:http://arxiv.org/abs/2402.18272 .
[27] Siyuan Wang et al. Benchmark Self-Evolving: A Multi-Agent Framework for Dynamic LLM Evaluation .
arXiv:2402.11443 [cs]. Feb. 2024. URL:http://arxiv.org/abs/2402.11443 .
12

[28] Zhenhailong Wang et al. Unleashing the Emergent Cognitive Synergy in Large Language Models: A Task-Solving
Agent through Multi-Persona Self-Collaboration . 2024. arXiv: 2307.05300 [cs.AI] .
[29] Jason Wei et al. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models . arXiv:2201.11903
[cs]. Jan. 2023. URL:http://arxiv.org/abs/2201.11903 .
[30] Yue Wu et al. SmartPlay: A Benchmark for LLMs as Intelligent Agents . arXiv:2310.01557 [cs]. Mar. 2024. URL:
http://arxiv.org/abs/2310.01557 .
[31] Zhiheng Xi et al. The Rise and Potential of Large Language Model Based Agents: A Survey . 2023. arXiv:
2309.07864 [cs.AI] .
[32] Shunyu Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models . arXiv:2210.03629 [cs]. Mar.
2023. URL:http://arxiv.org/abs/2210.03629 .
[33] Shunyu Yao et al. Tree of Thoughts: Deliberate Problem Solving with Large Language Models . arXiv:2305.10601
[cs]. Dec. 2023. URL:http://arxiv.org/abs/2305.10601 .
[34] Muru Zhang et al. How Language Model Hallucinations Can Snowball . arXiv:2305.13534 [cs]. May 2023. URL:
http://arxiv.org/abs/2305.13534 .
[35] Wenting Zhao et al. “(InThe)WildChat: 570K ChatGPT Interaction Logs In The Wild”. In: The Twelfth In-
ternational Conference on Learning Representations . 2024. URL:https://openreview.net/forum?id=
Bl8u7ZRlbM .
[36] Andy Zhou et al. Language Agent Tree Search Unifies Reasoning Acting and Planning in Language Models .
arXiv:2310.04406 [cs]. Dec. 2023. URL:http://arxiv.org/abs/2310.04406 .
[37] Kaijie Zhu et al. DyVal 2: Dynamic Evaluation of Large Language Models by Meta Probing Agents .
arXiv:2402.14865 [cs]. Feb. 2024. URL:http://arxiv.org/abs/2402.14865 .
[38] Kaijie Zhu et al. DyVal: Dynamic Evaluation of Large Language Models for Reasoning Tasks . arXiv:2309.17167
[cs]. Mar. 2024. URL:http://arxiv.org/abs/2309.17167 .
13