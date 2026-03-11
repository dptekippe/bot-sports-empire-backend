D e c e n t r a l i z e d  p a t t e r nI n a decen tr aliz ed pa tt ern,  agen ts can ‘hando ff’  w orkflo w  e x ecution t o one ano ther .  H ando ffs ar e a 
one w a y  tr ansf er  tha t allo w  an agen t t o delega t e t o ano ther  agen t.  I n the A gen ts SDK,  a hando ff  is 
a type o f  t ool,  or  func tion.  If  an agen t calls a hando ff  func tion,  w e immedia t ely  start e x ecution on 
tha t ne w  agen t tha t w as handed o ff  t o while also tr ansf erring the la t est con v er sa tion sta t e .  
This pa tt ern in v olv es using man y  agen ts on equal f oo ting,  wher e one agen t can dir ec tly  hand  
o ff  con tr ol o f  the w orkflo w  t o ano ther  agen t.  This is op timal when y ou don ’t need a single agen t 
main taining cen tr al con tr ol or  s yn thesis—inst ead allo wing each agen t t o tak e o v er  e x ecution and 
in t er ac t with the user  as needed.
Where is my order?On its way!TriageIssues and RepairsSalesOrders
2 1A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

F or  e x ample ,  her e ’ s ho w  y ou’ d implemen t the decen tr aliz ed pa tt ern using the A gen ts SDK  f or   
a cust omer  service w orkflo w  tha t handles bo th sales and support:P y t h o n1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25

from import agents  Agent, Runner          

technical_support_agent = Agent(
    name=
    instructions=(
        
    ),
    tools=[search_knowledge_base]
)

sales_assistant_agent = Agent(
    name= ,
    instructions=(
       
    ),
    tools=[initiate_purchase_order]
)

order_management_agent = Agent(
    name= ,
    instructions=(
       
  
"Technical Support Agent",
"You provide expert assistance with resolving technical issues, 
system outages, or product troubleshooting."
"Sales Assistant Agent"
 "You help enterprise clients browse the product catalog, recommend 
suitable solutions, and facilitate purchase transactions."
"Order Management Agent"
 "You assist clients with inquiries regarding order tracking, 
delivery schedules, and processing returns or refunds."
2 2A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42),
tools=[track_order_status, initiate_refund_process]
)

triage_agent = Agent(
    name=Triage Agent",
    instructions=
,
    handoffs=[technical_support_agent, sales_assistant_agent, 
order_management_agent],
)

 Runner.run(
    triage_agent,
     (
)
)
"You act as the first point of contact, assessing customer 
queries and directing them promptly to the correct specialized agent."
"Could you please provide an update on the delivery timeline for 
our recent purchase?"await
inputI n the abo v e e x ample ,  the initial user  message is sen t t o triage _ agen t.  R ecognizing tha t  
the input concerns a r ecen t pur chase ,  the triage _ agen t w ould in v ok e a hando ff  t o the 
or der _managemen t_ agen t, tr ansf erring con tr ol t o it.
This pa tt ern is especially  e ff ec tiv e f or  scenarios lik e con v er sa tion triage ,  or  whene v er  y ou pr e f er  
specializ ed agen ts t o fully  tak e o v er  certain task s without the original agen t needing t o r emain 
in v olv ed.  Op tionally ,  y ou can equip the second agen t with a hando ff  back  t o the original agen t,  
allo wing it t o tr ansf er  con tr ol again if  necessary .  
2 3A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s