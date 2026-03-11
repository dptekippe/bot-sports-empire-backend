THELANDSCAPE OF EMERGING AI A GENT ARCHITECTURES
FOR REASONING , PLANNING ,AND TOOL CALLING : A S URVEY
Tula Masterman
Neudesic, an IBM Company
tula.masterman@neudesic.comSandi Besen
IBM
sandi.besen@ibm.com
Mason Sawtell
Neudesic, an IBM Company
mason.sawtell@neudesic.com
 Denotes Equal ContributionAlex Chao
Microsoft
achao@microsoft.com
ABSTRACT
This survey paper examines the recent advancements in AI agent implementations, with a focus on
their ability to achieve complex goals that require enhanced reasoning, planning, and tool execution
capabilities. The primary objectives of this work are to a) communicate the current capabilities and
limitations of existing AI agent implementations, b) share insights gained from our observations
of these systems in action, and c) suggest important considerations for future developments in AI
agent design. We achieve this by providing overviews of single-agent and multi-agent architectures,
identifying key patterns and divergences in design choices, and evaluating their overall impact on
accomplishing a provided goal. Our contribution outlines key themes when selecting an agentic
architecture, the impact of leadership on agent systems, agent communication styles, and key phases
for planning, execution, and reflection that enable robust AI agent systems.
Keywords AI Agent ·Agent Architecture ·AI Reasoning ·Planning ·Tool Calling ·Single Agent ·Multi Agent ·
Agent Survey ·LLM Agent ·Autonomous Agent
1 Introduction
Since the launch of ChatGPT, many of the first wave of generative AI applications have been a variation of a chat over
a corpus of documents using the Retrieval Augmented Generation (RAG) pattern. While there is a lot of activity in
making RAG systems more robust, various groups are starting to build what the next generation of AI applications will
look like, centralizing on a common theme: agents.
Beginning with investigations into recent foundation models like GPT-4 and popularized through open-source projects
like AutoGPT and BabyAGI, the research community has experimented with building autonomous agent-based systems
[19, 1].
As opposed to zero-shot prompting of a large language model where a user types into an open-ended text field and gets
a result without additional input, agents allow for more complex interaction and orchestration. In particular, agentic
systems have a notion of planning, loops, reflection and other control structures that heavily leverage the model’s
inherent reasoning capabilities to accomplish a task end-to-end. Paired with the ability to use tools, plugins, and
function calling, agents are empowered to do more general-purpose work.
Among the community, there is a current debate on whether single or multi-agent systems are best suited for solving
complex tasks. While single agent architectures excel when problems are well-defined and feedback from other
The opinions expressed in this paper are solely those of the authors and do not necessarily reflect the views or policies of their
respective employers.arXiv:2404.11584v1  [cs.AI]  17 Apr 2024

agent-personas or the user is not needed, multi-agent architectures tend to thrive more when collaboration and multiple
distinct execution paths are required.
Figure 1: A visualization of single and multi-agent architectures with their underlying features and abilities
1.1 Taxonomy
Agents . AI agents are language model-powered entities able to plan and take actions to execute goals over multiple
iterations. AI agent architectures are either comprised of a single agent or multiple agents working together to solve a
problem.
Typically, each agent is given a persona and access to a variety of tools that will help them accomplish their job either
independently or as part of a team. Some agents also contain a memory component, where they can save and load
information outside of their messages and prompts. In this paper, we follow the definition of agent that consists of
“brain, perception, and action” [31]. These components satisfy the minimum requirements for agents to understand,
reason, and act on the environment around them.
Agent Persona . An agent persona describes the role or personality that the agent should take on, including any other
instructions specific to that agent. Personas also contain descriptions of any tools the agent has access to. They make
the agent aware of their role, the purpose of their tools, and how to leverage them effectively. Researchers have found
that “shaped personality verifiably influences Large Language Model (LLM) behavior in common downstream (i.e.
subsequent) tasks, such as writing social media posts” [21]. Solutions that use multiple agent personas to solve problems
also show significant improvements compared to Chain-of-Thought (CoT) prompting where the model is asked to break
down its plans step by step [28, 29].
Tools . In the context of AI agents, tools represent any functions that the model can call. They allow the agent to interact
with external data sources by pulling or pushing information to that source. An example of an agent persona and
associated tools is a professional contract writer. The writer is given a persona explaining their role and the types of
tasks it must accomplish. It is also given tools related to adding notes to a document, reading an existing document, or
sending an email with a final draft.
Single Agent Architectures . These architectures are powered by one language model and will perform all the reasoning,
planning, and tool execution on their own. The agent is given a system prompt and any tools required to complete their
2

task. In single agent patterns there is no feedback mechanism from other AI agents; however, there may be options for
humans to provide feedback that guides the agent.
Multi-Agent Architectures . These architectures involve two or more agents, where each agent can utilize the same
language model or a set of different language models. The agents may have access to the same tools or different tools.
Each agent typically has their own persona.
Multi-agent architectures can have a wide variety of organizations at any level of complexity. In this paper, we divide
them into two primary categories: vertical and horizontal. It is important to keep in mind that these categories represent
two ends of a spectrum, where most existing architectures fall somewhere between these two extremes.
Vertical Architectures . In this structure, one agent acts as a leader and has other agents report directly to them.
Depending on the architecture, reporting agents may communicate exclusively with the lead agent. Alternatively, a
leader may be defined with a shared conversation between all agents. The defining features of vertical architectures
include having a lead agent and a clear division of labor between the collaborating agents.
Horizontal Architectures . In this structure, all the agents are treated as equals and are part of one group discussion
about the task. Communication between agents occurs in a shared thread where each agent can see all messages from
the others. Agents also can volunteer to complete certain tasks or call tools, meaning they do not need to be assigned
by a leading agent. Horizontal architectures are generally used for tasks where collaboration, feedback and group
discussion are key to the overall success of the task [2].
2 Key Considerations for Effective Agents
2.1 Overview
Agents are designed to extend language model capabilities to solve real-world challenges. Successful implementations
require robust problem-solving capabilities enabling agents to perform well on novel tasks. To solve real-world problems
effectively, agents require the ability to reason and plan as well as call tools that interact with an external environment.
In this section we explore why reasoning, planning, and tool calling are critical to agent success.
2.2 The Importance of Reasoning and Planning
Reasoning is a fundamental building block of human cognition, enabling people to make decisions, solve problems, and
understand the world around us. AI agents need a strong ability to reason if they are to effectively interact with complex
environments, make autonomous decisions, and assist humans in a wide range of tasks. This tight synergy between
“acting” and “reasoning” allows new tasks to be learned quickly and enables robust decision making or reasoning, even
under previously unseen circumstances or information uncertainties [32]. Additionally, agents need reasoning to adjust
their plans based on new feedback or information learned.
If agents lacking reasoning skills are tasked with acting on straightforward tasks, they may misinterpret the query,
generate a response based on a literal understanding, or fail to consider multi-step implications.
Planning, which requires strong reasoning abilities, commonly falls into one of five major approaches: task decomposi-
tion, multi-plan selection, external module-aided planning, reflection and refinement and memory-augmented planning
[12]. These approaches allow the model to either break the task down into sub tasks, select one plan from many
generated options, leverage a preexisting external plan, revise previous plans based on new information, or leverage
external information to improve the plan.
Most agent patterns have a dedicated planning step which invokes one or more of these techniques to create a plan
before any actions are executed. For example, Plan Like a Graph (PLaG) is an approach that represents plans as directed
graphs, with multiple steps being executed in parallel [15, 33]. This can provide a significant performance increase over
other methods on tasks that contain many independent subtasks that benefit from asynchronous execution.
2.3 The Importance of Effective Tool Calling
One key benefit of the agent abstraction over prompting base language models is the agents’ ability to solve complex
problems by calling multiple tools. These tools enable the agent to interact with external data sources, send or retrieve
information from existing APIs, and more. Problems that require extensive tool calling often go hand in hand with
those that require complex reasoning.
Both single-agent and multi-agent architectures can be used to solve challenging tasks by employing reasoning and tool
calling steps. Many methods use multiple iterations of reasoning, memory, and reflection to effectively and accurately
3

complete problems [16, 23, 32]. They often do this by breaking a larger problem into smaller subproblems, and then
solving each one with the appropriate tools in sequence.
Other works focused on advancing agent patterns highlight that while breaking a larger problem into smaller subproblems
can be effective at solving complex tasks, single agent patterns often struggle to complete the long sequence required
[22, 6].
Multi-agent patterns can address the issues of parallel tasks and robustness since individual agents can work on
individual subproblems. Many multi-agent patterns start by taking a complex problem and breaking it down into several
smaller tasks. Then, each agent works independently on solving each task using their own independent set of tools.
3 Single Agent Architectures
3.1 Overview
In this section, we highlight some notable single agent methods such as ReAct, RAISE, Reflexion, AutoGPT + P, and
LATS. Each of these methods contain a dedicated stage for reasoning about the problem before any action is taken to
advance the goal. We selected these methods based on their contributions to the reasoning and tool calling capabilities
of agents.
3.2 Key Themes
We find that successful goal execution by agents is contingent upon proper planning and self-correction [32, 16, 23, 1].
Without the ability to self-evaluate and create effective plans, single agents may get stuck in an endless execution loop
and never accomplish a given task or return a result that does not meet user expectations [32]. We find that single agent
architectures are especially useful when the task requires straightforward function calling and does not need feedback
from another agent [22].
3.3 Examples
ReAct. In the ReAct (Reason + Act) method, an agent first writes a thought about the given task. It then performs
an action based on that thought, and the output is observed. This cycle can repeat until the task is complete [32].
When applied to a diverse set of language and decision-making tasks, the ReAct method demonstrates improved
effectiveness compared to zero-shot prompting on the same tasks. It also provides improved human interoperability and
trustworthiness because the entire thought process of the model is recorded. When evaluated on the HotpotQA dataset,
the ReAct method only hallucinated 6% of the time, compared to 14% using the chain of thought (CoT) method [29,
32].
However, the ReAct method is not without its limitations. While intertwining reasoning, observation, and action
improves trustworthiness, the model can repetitively generate the same thoughts and actions and fail to create new
thoughts to provoke finishing the task and exiting the ReAct loop. Incorporating human feedback during the execution
of the task would likely increase its effectiveness and applicability in real-world scenarios.
RAISE. The RAISE method is built upon the ReAct method, with the addition of a memory mechanism that mirrors
human short-term and long-term memory [16]. It does this by using a scratchpad for short-term storage and a dataset of
similar previous examples for long-term storage.
By adding these components, RAISE improves upon the agent’s ability to retain context in longer conversations. The
paper also highlights how fine-tuning the model results in the best performance for their task, even when using a smaller
model. They also showed that RAISE outperforms ReAct in both efficiency and output quality.
While RAISE significantly improves upon existing methods in some respects, the researchers also highlighted several
issues. First, RAISE struggles to understand complex logic, limiting its usefulness in many scenarios. Additionally,
RAISE agents often hallucinated with respect to their roles or knowledge. For example, a sales agent without a clearly
defined role might retain the ability to code in Python, which may enable them to start writing Python code instead of
focusing on their sales tasks. These agents might also give the user misleading or incorrect information. This problem
was addressed by fine-tuning the model, but the researchers still highlighted hallucination as a limitation in the RAISE
implementation.
Reflexion. Reflexion is a single-agent pattern that uses self-reflection through linguistic feedback [23]. By utilizing
metrics such as success state, current trajectory, and persistent memory, this method uses an LLM evaluator to provide
4

D6WDQGDUG$QVZHUE&R75HDVRQ2QO\7KRXJKW/HW
VWKLQNVWHSE\VWHS7KHKRWHOWKDWLVKRPHWRWKH&LUTXHGX6ROHLOVKRZ0\VWHUHLV7UHDVXUH,VODQG7UHDVXUH,VODQGKDVURRPVVRWKHDQVZHULV$QVZHUF$FW2QO\$FW6HDUFK>&LUTXHGX6ROHLO@2EV&LUTXHGX6ROHLOLVD&DQDGLDQHQWHUWDLQPHQWFRPSDQ\ª$FW/RRNXS>0\VWHUH@2EV1RPRUHUHVXOWV$FW6HDUFK>0\VWHUH&LUTXHGX6ROHLOVKRZ@2EV&RXOGQRWILQGª$FW6HDUFK>0\VWHUH&LUTXHGX6ROHLO@2EV0\VWqUHP\VWHHULVRQHRIVL[ª$FW/RRNXS>7UHDVXUH,VODQG+RWHODQG&DVLQR@ªªHQGZLWKRXWDQVZHUG5H$FW5HDVRQ$FW7KRXJKW,QHHGWRVHDUFK&LUTXHGX6ROHLOVKRZ0\VWHUHILQGWKHKRWHOLWLVLQWKHQILQGWKHQXPEHURIURRPVLQWKHKRWHO$FW6HDUFK>&LUTXHGX6ROHLOVKRZ0\VWHUH@2EV&RXOGQRWILQG&LUTXHGX6ROHLOVKRZ0\VWHUH6LPLODU>
&LUTXHGX6ROHLO
ª7KRXJKW7RILQGWKHKRWHO,FDQVHDUFK0\VWHUH&LUTXHGX6ROHLO$FW6HDUFK>0\VWHUH&LUTXHGX6ROHLO@2EV0\VWqUHP\VWHHULVª+HOGLQDFXVWRPWKHDWUHDWWKH7UHDVXUH,VODQG+RWHODQG&DVLQRª7KRXJKW0\VWHUHLVKHOGLQDFXVWRPWKHDWUHDWWKH7UHDVXUH,VODQG+RWHODQG&DVLQR6R,QHHGWRVHDUFK7UHDVXUH,VODQG+RWHODQG&DVLQRQH[WDQGILQGWKHQXPEHURIURRPVLQWKHKRWHO$FW6HDUFK>7UHDVXUH,VODQG+RWHODQG&DVLQR@2EV7UHDVXUH,VODQG+RWHODQG&DVLQRªZLWKURRPVDQGVXLWHVª7KRXJKW7UHDVXUH,VODQG+RWHODQG&DVLQRKDVURRPVDQGVXLWHV6RWKHDQVZHULV$FW)LQLVK>@Ҽ4XHVWLRQ+RZPDQ\URRPVDUHLQWKHKRWHOWKDWLVKRPHWRWKH&LUTXHGX6ROHLOVKRZ0\VWHUH"+RWSRW4$ODEHO+RWVSRW4$2XWGDWHG
8SWRGDWHFigure 2: An example of the ReAct method compared to other methods [32]
RAISE FrameworkUser QueryMemory UpdateExamples Retirval
Tool  Pool•Database Access•Scripting and Programming Tools•Knowledge Bases and Information Repositories•AI and Machine Learning ToolsExample  Pool••••. . . •Working Memory•System Prompt •Profile•Task Instruction•. . .•ConversationHistory •Scratchpad•Retrieved Examples•TaskTrajectoryLLMs•API-based LLMs •GPT-4、 GPT-3.5•Claude•. . . •Open-sourced LLMs•Llama•Qwen•Baichuan•. . .
Agent Loop
Figure 3: A diagram showing the RAISE method [16]
specific and relevant feedback to the agent. This results in an improved success rate as well as reduced hallucination
compared to Chain-of-Thought and ReAct.
Despite these advancements, the Reflexion authors identify various limitations of the pattern. Primarily, Reflexion
is susceptible to “non-optimal local minima solutions”. It also uses a sliding window for long-term memory, rather
than a database. This means that the volume of long-term memory is limited by the token limit of the language model.
Finally, the researchers identify that while Reflexion surpasses other single-agent patterns, there are still opportunities
to improve performance on tasks that require a significant amount of diversity, exploration, and reasoning.
AUTOGPT + P. AutoGPT + P (Planning) is a method that addresses reasoning limitations for agents that command
robots in natural language [1]. AutoGPT+P combines object detection and Object Affordance Mapping (OAM) with
a planning system driven by a LLM. This allows the agent to explore the environment for missing objects, propose
alternatives, or ask the user for assistance with reaching its goal.
5