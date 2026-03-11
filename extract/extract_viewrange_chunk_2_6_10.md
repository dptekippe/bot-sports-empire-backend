AutoGPT+P starts by using an image of a scene to detect the objects present. A language model then uses those objects
to select which tool to use, from four options: Plan Tool, Partial Plan Tool, Suggest Alternative Tool, and Explore Tool.
These tools allow the robot to not only generate a full plan to complete the goal, but also to explore the environment,
make assumptions, and create partial plans.
However, the language model does not generate the plan entirely on its own. Instead, it generates goals and steps to
work aside a classical planner which executes the plan using Planning Domain Definition Language (PDDL). The
paper found that “LLMs currently lack the ability to directly translate a natural language instruction into a plan for
executing robotic tasks, primarily due to their constrained reasoning capabilities” [1]. By combining the LLM planning
capabilities with a classical planner, their approach significantly improves upon other purely language model-based
approaches to robotic planning.
As with most first of their kind approaches, AutoGPT+P is not without its drawbacks. Accuracy of tool selection varies,
with certain tools being called inappropriately or getting stuck in loops. In scenarios where exploration is required,
the tool selection sometimes leads to illogical exploration decisions like looking for objects in the wrong place. The
framework also is limited in terms of human interaction, with the agent being unable to seek clarification and the user
being unable to modify or terminate the plan during execution.
Figure 4: A diagram of the AutoGPT+P method [1]
LATS. Language Agent Tree Search (LATS) is a single-agent method that synergizes planning, acting, and reasoning
by using trees [36]. This technique, inspired by Monte Carlo Tree Search, represents a state as a node and taking an
action as traversing between nodes. It uses LM-based heuristics to search for possible options, then selects an action
using a state evaluator.
When compared to other tree-based methods, LATS implements a self-reflection reasoning step that dramatically
improves performance. When an action is taken, both environmental feedback as well as feedback from a language
model is used to determine if there are any errors in reasoning and propose alternatives. This ability to self-reflect
combined with a powerful search algorithm makes LATS perform extremely well on various tasks.
However, due to the complexity of the algorithm and the reflection steps involved, LATS often uses more computational
resources and takes more time to complete than other single-agent methods [36]. The paper also uses relatively simple
question answering benchmarks and has not been tested on more robust scenarios that involve involving tool calling or
complex reasoning.
4 Multi Agent Architectures
4.1 Overview
In this section, we examine a few key studies and sample frameworks with multi-agent architectures, such as Embodied
LLM Agents Learn to Cooperate in Organized Teams, DyLAN, AgentVerse, and MetaGPT. We highlight how these
implementations facilitate goal execution through inter-agent communication and collaborative plan execution. This is
not intended to be an exhaustive list of all agent frameworks, our goal is to provide broad coverage of key themes and
examples related to multi-agent patterns.
4.2 Key Themes
Multi-agent architectures create an opportunity for both the intelligent division of labor based on skill and helpful
feedback from a variety of agent personas. Many multi-agent architectures work in stages where teams of agents are
6

created and reorganized dynamically for each planning, execution, and evaluation phase [2, 9, 18]. This reorganization
provides superior results because specialized agents are employed for certain tasks, and removed when they are no
longer needed. By matching agents roles and skills to the task at hand, agent teams can achieve greater accuracy
and decrease time to meet the goal. Key features of effective multi-agent architectures include clear leadership in
agent teams, dynamic team construction, and effective information sharing between team members so that important
information does not get lost in superfluous chatter.
4.3 Examples
Embodied LLM Agents Learn to Cooperate in Organized Teams. Research by Guo et al. demonstrates the impact
of a lead agent on the overall effectiveness of the agent team [9]. This architecture contains a vertical component
through the leader agent, as well as a horizontal component from the ability for agents to converse with other agents
besides the leader. The results of their study demonstrate that agent teams with an organized leader complete their tasks
nearly 10% faster than teams without a leader.
Furthermore, they discovered that in teams without a designated leader, agents spent most of their time giving orders
to one another (~50% of communication), splitting their remaining time between sharing information, or requesting
guidance. Conversely, in teams with a designated leader, 60% of the leader’s communication involved giving directions,
prompting other members to focus more on exchanging and requesting information. Their results demonstrate that
agent teams are most effective when the leader is a human.
Figure 5: Agent teams with a designated leader achieve superior performance [9]
.
Beyond team structure, the paper emphasizes the importance of employing a “criticize-reflect” step for generating plans,
evaluating performance, providing feedback, and re-organizing the team [9]. Their results indicate that agents with a
dynamic team structure with rotating leadership provide the best results, with both the lowest time to task completion
and the lowest communication cost on average. Ultimately, leadership and dynamic team structures improve the overall
team’s ability to reason, plan, and perform tasks effectively.
DyLAN. The Dynamic LLM-Agent Network (DyLAN) framework creates a dynamic agent structure that focuses on
complex tasks like reasoning and code generation [18]. DyLAN has a specific step for determining how much each
agent has contributed in the last round of work and only moves top contributors the next round of execution. This
method is horizontal in nature since agents can share information with each other and there is no defined leader. DyLAN
shows improved performance on a variety of benchmarks which measure arithmetic and general reasoning capabilities.
This highlights the impact of dynamic teams and demonstrates that by consistently re-evaluating and ranking agent
contributions, we can create agent teams that are better suited to complete a given task.
AgentVerse. Multi-agent architectures like AgentVerse demonstrate how distinct phases for group planning can
improve an AI agent’s reasoning and problem-solving capabilities [2]. AgentVerse contains four primary stages for
task execution: recruitment, collaborative decision making, independent action execution, and evaluation. This can be
repeated until the overall goal is achieved. By strictly defining each phase, AgentVerse helps guide the set of agents to
reason, discuss, and execute more effectively.
As an example, the recruitment step allows agents to be removed or added based on the progress towards the goal. This
helps ensure that the right agents are participating at any given stage of problem solving. The researchers found that
horizontal teams are generally best suited for collaborative tasks like consulting, while vertical teams are better suited
for tasks that require clearer isolation of responsibilities for tool calling.
7

!
 ==  
"
 
Expert Recruitment
$
Collaborative Decision-Making
⚙
Action ExecutionBuild 
!
&
'
  
(
)

+
Goal 
Goal
!
Outcome
"
,
 EvaluationNew StateNew StateGroup?Reward Feedback
: ArchitectRound 1: Designer
: EngineerNew State
: EngineerNew State: Logger: Worker
"
: EngineerNew State: Worker: Designer
!
Round 2Round 3
✨
$
.
/
✨
Group???Actions:Agents:x N rounds
x M turnsFigure 6: A diagram of the AgentVerse method [2]
MetaGPT. Many multi-agent architectures allow agents to converse with one another while collaborating on a common
problem. This conversational capability can lead to chatter between the agents that is superfluous and does not further
the team goal. MetaGPT addresses the issue of unproductive chatter amongst agents by requiring agents to generate
structured outputs like documents and diagrams instead of sharing unstructured chat messages [11].
Additionally, MetaGPT implements a ”publish-subscribe” mechanism for information sharing. This allows all the
agents to share information in one place, but only read information relevant to their individual goals and tasks. This
streamlines the overall goal execution and reduces conversational noise between agents. When compared to single-agent
architectures on the HumanEval and MBPP benchmarks, MetaGPT’s multi-agent architecture demonstrates significantly
better results.
5 Discussion and Observations
5.1 Overview
In this section we discuss the key themes and impacts of the design choices exhibited in the previously outlined agent
patterns. These patterns serve as key examples of the growing body of research and implementation of AI agent
architectures. Both single and multi-agent architectures seek to enhance the capabilities of language models by giving
them the ability to execute goals on behalf of or alongside a human user. Most observed agent implementations broadly
follow the plan, act, and evaluate process to iteratively solve problems.
We find that both single and multi-agent architectures demonstrate compelling performance on complex goal execution.
We also find that across architectures clear feedback, task decomposition, iterative refinement, and role definition yield
improved agent performance.
5.2 Key Findings
Typical Conditions for Selecting a Single vs Multi-Agent Architecture. Based on the aforementioned agent patterns,
we find that single-agent patterns are generally best suited for tasks with a narrowly defined list of tools and where
processes are well-defined. Single agents are also typically easier to implement since only one agent and set of tools
needs to be defined. Additionally, single agent architectures do not face limitations like poor feedback from other agents
or distracting and unrelated chatter from other team members. However, they may get stuck in an execution loop and
fail to make progress towards their goal if their reasoning and refinement capabilities are not robust.
8

Multi-agent architectures are generally well-suited for tasks where feedback from multiple personas is beneficial in
accomplishing the task. For example, document generation may benefit from a multi-agent architecture where one
agent provides clear feedback to another on a written section of the document. Multi-agent systems are also useful
when parallelization across distinct tasks or workflows is required. Crucially, Wang et. al finds that multi-agent patterns
perform better than single agents in scenarios when no examples are provided [26]. By nature, multi-agent systems are
more complex and often benefit from robust conversation management and clear leadership.
While single and multi-agent patterns have diverging capabilities in terms of scope, research finds that “multi-agent
discussion does not necessarily enhance reasoning when the prompt provided to an agent is sufficiently robust” [26].
This suggests that those implementing agent architectures should decide between single or multiple agents based on the
broader context of their use case, and not based on the reasoning capabilities required.
Agents and Asynchronous Task Execution. While a single agent can initiate multiple asynchronous calls simulta-
neously, its operational model does not inherently support the division of responsibilities across different execution
threads. This means that, although tasks are handled asynchronously, they are not truly parallel in the sense of being
autonomously managed by separate decision-making entities. Instead, the single agent must sequentially plan and
execute tasks, waiting for one batch of asynchronous operations to complete before it can evaluate and move on to the
next step. Conversely, in multi-agent architectures, each agent can operate independently, allowing for a more dynamic
division of labor. This structure not only facilitates simultaneous task execution across different domains or objectives
but also allows individual agents to proceed with their next steps without being hindered by the state of tasks handled
by others, embodying a more flexible and parallel approach to task management.
Impact of Feedback and Human Oversight on Agent Systems. When solving a complex problem, it is extremely
unlikely that one provides a correct, robust solution on their first try. Instead, one might pose a potential solution before
criticizing it and refining it. One could also consult with someone else and receive feedback from another perspective.
The same idea of iterative feedback and refinement is essential for helping agents solve complex problems.
This is partially because language models tend to commit to an answer earlier in their response, which can cause a
‘snowball effect’ of increasing diversion from their goal state [34] . By implementing feedback, agents are much more
likely to correct their course and reach their goal.
Additionally, the inclusion of human oversight improves the immediate outcome by aligning the agent’s responses more
closely with human expectations, mitigating the potential for agents to delve down an inefficient or invalid approach to
solving a task. As of today, including human validation and feedback in the agent architecture yields more reliable and
trustworthy results [4, 9].
Language models also exhibit sycophantic behavior, where they “tend to mirror the user’s stance, even if it means
forgoing the presentation of an impartial or balanced viewpoint” [20]. Specifically, the AgentVerse paper describes how
agents are susceptible to feedback from other agents, even if the feedback is not sound. This can lead the agent team to
generate a faulty plan which diverts them from their objective [2]. Robust prompting can help mitigate this, but those
developing agent applications should be aware of the risks when implementing user or agent feedback systems.
Challenges with Group Conversations and Information Sharing. One challenge with multi-agent architectures
lies in their ability to intelligently share messages between agents. Multi-agent patterns have a greater tendency to get
caught up in niceties and ask one another things like “how are you”, while single agent patterns tend to stay focused on
the task at hand since there is no team dynamic to manage. The extraneous dialogue in multi-agent systems can impair
both the agent’s ability to reason effectively and execute the right tools, ultimately distracting the agents from the task
and decreasing team efficiency. This is especially true in a horizontal architecture, where agents typically share a group
chat and are privy to every agent’s message in a conversation. Message subscribing or filtering improves multi-agent
performance by ensuring agents only receive information relevant to their tasks.
In vertical architectures, tasks tend to be clearly divided by agent skill which helps reduce distractions in the team.
However, challenges arise when the leading agent fails to send critical information to their supporting agents and does
not realize the other agents aren’t privy to necessary information. This failure can lead to confusion in the team or
hallucination in the results. One approach to address this issue is to explicitly include information about access rights in
the system prompt so that the agents have contextually appropriate interactions.
Impact of Role Definition and Dynamic Teams. Clear role definition is critical for both single and multi-agent
architectures. In single-agent architectures role definition ensures that the agent stays focused on the provided task,
executes the proper tools, and minimizes hallucination of other capabilities. Similarly, role definition in multi-agent
architectures ensures each agent knows what it’s responsible for in the overall team and does not take on tasks outside
of their described capabilities or scope. Beyond individual role definition, establishing a clear group leader also
improves the overall performance of multi-agent teams by streamlining task assignment. Furthermore, defining a clear
9

system prompt for each agent can minimize excess chatter by prompting the agents not to engage in unproductive
communication.
Dynamic teams where agents are brought in and out of the system based on need have also been shown to be effective.
This ensures that all agents participating in the planning or execution of tasks are fit for that round of work.
5.3 Summary
Both single and multi-agent patterns exhibit strong performance on a variety of complex tasks involving reasoning and
tool execution. Single agent patterns perform well when given a defined persona and set of tools, opportunities for
human feedback, and the ability to work iteratively towards their goal. When constructing an agent team that needs to
collaborate on complex goals, it is beneficial to deploy agents with at least one of these key elements: clear leader(s), a
defined planning phase and opportunities to refine the plan as new information is learned, intelligent message filtering,
and dynamic teams whose agents possess specific skills relevant to the current sub-task. If an agent architecture employs
at least one of these approaches it is likely to result in increased performance compared to a single agent architecture or
a multi-agent architecture without these tactics.
6 Limitations of Current Research and Considerations for Future Research
6.1 Overview
In this section we examine some of the limitations of agent research today and identify potential areas for improving AI
agent systems. While agent architectures have significantly enhanced the capability of language models in many ways,
there are some major challenges around evaluations, overall reliability, and issues inherited from the language models
powering each agent.
6.2 Challenges with Agent Evaluation
While LLMs are evaluated on a standard set of benchmarks designed to gauge their general understanding and reasoning
capabilities, the benchmarks for agent evaluation vary greatly.
Many research teams introduce their own unique agent benchmarks alongside their agent implementation which makes
comparing multiple agent implementations on the same benchmark challenging. Additionally, many of these new
agent-specific benchmarks include a hand-crafted, highly complex, evaluation set where the results are manually scored
[2]. This can provide a high-quality assessment of a method’s capabilities, but it also lacks the robustness of a larger
dataset and risks introducing bias into the evaluation, since the ones developing the method are also the ones writing
and scoring the results. Agents can also have problems generating a consistent answer over multiple iterations, due
to variability in the models, environment, or problem state. This added randomness poses a much larger problem to
smaller, complex evaluation sets.
6.3 Impact of Data Contamination and Static Benchmarks
Some researchers evaluate their agent implementations on the typical LLM benchmarks. Emerging research indicates
that there is significant data contamination in the model’s training data, supported by the observation that a model’s
performance significantly worsens when benchmark questions are modified [8, 38, 37]. This raises doubts on the
authenticity of benchmark scores for both the language models and language model powered agents.
Furthermore, researchers have found that “As LLMs progress at a rapid pace, existing datasets usually fail to match the
models’ ever-evolving capabilities, because the complexity level of existing benchmarks is usually static and fixed”
[37]. To address this, work has been done to create dynamic benchmarks that are resistant to simple memorization [38,
37]. Researchers have also explored the idea of generating an entirely synthetic benchmark based on a user’s specific
environment or use case [14, 27]. While these techniques can help with contamination, decreasing the level of human
involvement can pose additional risks regarding correctness and the ability to solve problems.
6.4 Benchmark Scope and Transferability
Many language model benchmarks are designed to be solved in a single iteration, with no tool calls, such as MMLU
or GSM8K [3, 10]. While these are important for measuring the abilities of base language models, they are not good
proxies for agent capabilities because they do not account for agent systems’ ability to reason over multiple steps or
access outside information. StrategyQA improves upon this by assessing models’ reasoning abilities over multiple
10