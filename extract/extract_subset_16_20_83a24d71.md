When t o consider  cr ea ting multiple agen tsOur  gener al r ecommenda tion is t o maximiz e a single agen t’ s capabilities fir st.  M or e agen ts can 
pr o vide in tuitiv e separ a tion o f  concep ts,  but can in tr oduce additional comple xity  and o v erhead,   
so o ft en a single agen t with t ools is sufficien t.   
F or  man y  comple x  w orkflo w s,  splitting up pr omp ts and t ools acr oss multiple agen ts allo w s f or  
impr o v ed perf ormance and scalability .  When y our  agen ts f ail t o f ollo w  complica t ed instruc tions  
or  consist en tly  selec t incorr ec t t ools,  y ou ma y  need t o further  divide y our  s y st em and in tr oduce 
mor e distinc t agen ts.
Pr ac tical guidelines f or  splitting agen ts include:C o m p l e x  l o g i cWhen pr omp ts con tain man y  conditional sta t emen ts  
(multiple if - then-else br anches ) ,  and pr omp t t empla t es ge t 
difficult t o scale ,  consider  dividing each logical segmen t acr oss 
separ a t e agen ts.T o o l  o v e r l o a dThe issue isn ’t solely  the number  o f  t ools,  but their  similarity   
or  o v erlap .  Some implemen ta tions successfully  manage  
mor e than 15 w ell-de fined,  distinc t t ools while o ther s struggle 
with f e w er  than 10 o v erlapping t ools.  U se multiple agen ts  
if  impr o ving t ool clarity  b y  pr o viding descrip tiv e names,   
clear  par ame t er s,  and de tailed descrip tions doesn ’t  
impr o v e perf ormance .
1 6A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

M u l t i - a g e n t  s y s t e m sWhile multi-agen t s y st ems can be designed in numer ous w a y s f or  specific w orkflo w s and 
r equir emen ts,  our  e xperience with cust omer s highligh ts tw o br oadly  applicable ca t egories:M a n a g e r  ( a g e n t s  a s  t o o l s )A  cen tr al “ manager”  agen t coor dina t es multiple specializ ed 
agen ts via t ool calls,  each handling a specific task  or  domain.D e c e n t r a l i z e d  ( a g e n t s  h a n d i n g  
o ff  t o  a g e n t s )M ultiple agen ts oper a t e as peer s,  handing o ff  task s t o one 
ano ther  based on their  specializ a tions.M ulti-agen t s y st ems can be modeled as gr aphs,  with agen ts r epr esen t ed as nodes.  I n the manager  
pa tt ern,  edges r epr esen t t ool calls wher eas in the decen tr aliz ed pa tt ern,  edges r epr esen t hando ffs 
tha t tr ansf er  e x ecution be tw een agen ts.
R egar dless o f  the or chestr a tion pa tt ern,  the same principles apply: k eep componen ts fle xible ,  
composable ,  and driv en b y  clear ,  w ell-struc tur ed pr omp ts.
1 7A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

M anager  pa tt ernThe manager  pa tt ern empo w er s a cen tr al LLM— the “ manager” — t o or chestr a t e a ne tw ork  o f  
specializ ed agen ts seamlessly  thr ough t ool calls.  I nst ead o f  losing con t e xt or  con tr ol,  the manager  
in t elligen tly  delega t es task s t o the righ t agen t a t the righ t time ,  e ff ortlessly  s yn thesizing the r esults 
in t o a cohesiv e in t er ac tion.  This ensur es a smoo th,  unified user  e xperience ,  with specializ ed 
capabilities alw a y s a v ailable on-demand.
This pa tt ern is ideal f or  w orkflo w s wher e y ou only  w an t one agen t t o con tr ol w orkflo w  e x ecution 
and ha v e access t o the user .Translate ‘hello’ to 
Spanish, French and 
Italian for me!...ManagerTaskSpanish agent
TaskFrench agent
TaskItalian agent
1 8A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

F or  e x ample ,  her e ’ s ho w  y ou could implemen t this pa tt ern in the A gen ts SDK:P y t h o n1
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
23from import
"manager_agent"
"You are a translation agent. You use the tools given to you to 
translate."
"translate_to_spanish"
"Translate the user's message to Spanish"
"translate_to_french"
"Translate the user's message to French"
"translate_to_italian"
"Translate the user's message to Italian" agents  Agent, Runner

manager_agent = Agent(
    name= ,
    instructions=(
        
        "If asked for multiple translations, you call the relevant tools."
    ),
    tools=[
        spanish_agent.as_tool(
            tool_name= ,
            tool_description= ,
        ),
        french_agent.as_tool(
            tool_name= ,
            tool_description= ,
        ),
        italian_agent.as_tool(
            tool_name= ,
            tool_description= ,
        ),
    ],
1 9A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

24
25
26
27
28
29
30
32
32
33)

  main():
    msg = input( )

    orchestrator_output = await Runner.run(
        manager_agent,msg)

      message  orchestrator_output.new_messages:
         (f"  -  {message.content}")async def
for in
print"Translate 'hello' to Spanish, French and Italian for me!"
Translation step:D e c l a r a t i v e  v s  n o n - d e c l a r a t i v e  g r a p h s  
S o m e  f r a m e w o r k s  a r e  d e c l a r a t i v e ,  r e q u i r i n g  d e v e l o p e r s  t o  e x p l i c i t l y  d e fi n e  e v e r y  b r a n c h ,  l o o p ,  
a n d  c o n d i t i o n a l  i n  t h e  w o r k fl o w  u p f r o n t  t h r o u g h  g r a p h s  c o n s i s t i n g  o f  n o d e s  ( a g e n t s )  a n d  
e d g e s  ( d e t e r m i n i s t i c  o r  d y n a m i c  h a n d o ff s ) .  W h i l e  b e n e fi c i a l  f o r  v i s u a l  c l a r i t y ,  t h i s  a p p r o a c h  
c a n  q u i c k l y  b e c o m e  c u m b e r s o m e  a n d  c h a l l e n g i n g  a s  w o r k fl o w s  g r o w  m o r e  d y n a m i c  a n d  
c o m p l e x ,  o f t e n  n e c e s s i t a t i n g  t h e  l e a r n i n g  o f  s p e c i a l i z e d  d o m a i n - s p e c i fi c  l a n g u a g e s .
I n  c o n t r a s t ,  t h e  A g e n t s  S D K  a d o p t s  a  m o r e  fl e x i b l e ,  c o d e - fi r s t  a p p r o a c h .  D e v e l o p e r s  c a n   
d i r e c t l y  e x p r e s s  w o r k fl o w  l o g i c  u s i n g  f a m i l i a r  p r o g r a m m i n g  c o n s t r u c t s  w i t h o u t  n e e d i n g  t o   
p r e - d e fi n e  t h e  e n t i r e  g r a p h  u p f r o n t ,  e n a b l i n g  m o r e  d y n a m i c  a n d  a d a p t a b l e  a g e n t  o r c h e s t r a t i o n .
2 0A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s