A  p r a c t i c a l   
g u i d e  t o   
b u i l d i n g  a g e n t s

C o n t e n t sWha t is an agen t?4When should y ou build an agen t?5A gen t design f ounda tions7Guar dr ails2 4Conclusion32
2P r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

I n t r o d u c t i o n
L ar ge language models ar e becoming incr easingly  capable o f  handling comple x,  multi-st ep task s.  
A dv ances in r easoning,  multimodality ,  and t ool use ha v e unlock ed a ne w  ca t egory  o f  LLM-po w er ed 
s y st ems kno wn as agen ts.
This guide is designed f or  pr oduc t and engineering t eams e xploring ho w  t o build their  fir st agen ts,  
distilling insigh ts fr om numer ous cust omer  deplo ymen ts in t o pr ac tical and ac tionable best 
pr ac tices.  It includes fr ame w ork s f or  iden tifying pr omising use cases,  clear  pa tt erns f or  designing 
agen t logic and or chestr a tion,  and best pr ac tices t o ensur e y our  agen ts run sa f ely ,  pr edic tably ,   
and e ff ec tiv ely .  
A ft er  r eading this guide ,  y ou’ll ha v e the f ounda tional kno wledge y ou need t o con fiden tly  start 
building y our  fir st agen t.3A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

W h a t  i s  a n  
a g e n t ?While con v en tional so ftw ar e enables user s t o str eamline and aut oma t e w orkflo w s,  agen ts ar e able 
t o perf orm the same w orkflo w s on the user s ’  behalf  with a high degr ee o f  independence .A gen ts ar e s y st ems tha t independen tly accomplish task s on y our  behalf .A  w orkflo w  is a sequence o f  st eps tha t must be e x ecut ed t o mee t the user’ s goal,  whe ther  tha t ' s 
r esolving a cust omer  service issue ,  booking a r estaur an t r eserv a tion,  committing a code change ,   
or  gener a ting a r eport.
Applica tions tha t in t egr a t e LLM s but don ’t use them t o con tr ol w orkflo w  e x ecution— think  simple 
cha tbo ts,  single- turn LLM s,  or  sen timen t classifier s—ar e no t agen ts.
M or e concr e t ely ,  an agen t possesses cor e char ac t eristics tha t allo w  it t o ac t r eliably  and 
consist en tly  on behalf  o f  a user:01It le v er ages an LLM t o manage w orkflo w  e x ecution and mak e decisions.  It r ecogniz es 
when a w orkflo w  is comple t e and can pr oac tiv ely  corr ec t its ac tions if  needed.  I n case  
o f  f ailur e ,  it can halt e x ecution and tr ansf er  con tr ol back  t o the user .02It has access t o v arious t ools t o in t er ac t with e xt ernal s y st ems—bo th t o ga ther  con t e xt 
and t o tak e ac tions—and dynamically  selec ts the appr opria t e t ools depending on the 
w orkflo w’ s curr en t sta t e ,  alw a y s oper a ting within clearly  de fined guar dr ails.4A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

W h e n  s h o u l d  y o u  
b u i l d  a n  a g e n t ?
Building agen ts r equir es r e thinking ho w  y our  s y st ems mak e decisions and handle comple xity .  
U nlik e con v en tional aut oma tion,  agen ts ar e uniquely  suit ed t o w orkflo w s wher e tr aditional 
de t erministic and rule-based appr oaches f all short.
Consider  the e x ample o f  pa ymen t fr aud analy sis.  A  tr aditional rules engine w ork s lik e a checklist,  
flagging tr ansac tions based on pr ese t crit eria.  I n con tr ast,  an LLM agen t func tions mor e lik e a 
seasoned in v estiga t or ,  e v alua ting con t e xt,  considering sub tle pa tt erns,  and iden tifying suspicious 
ac tivity  e v en when clear -cut rules ar en ’t viola t ed.  This nuanced r easoning capability  is e x ac tly  wha t 
enables agen ts t o manage comple x,  ambiguous situa tions e ff ec tiv ely .

A s y ou e v alua t e wher e agen ts can add v alue ,  prioritiz e w orkflo w s tha t ha v e pr e viously  r esist ed 
aut oma tion,  especially  wher e tr aditional me thods encoun t er  fric tion:01C o m p l e x   
d e c i s i o n - m a k i n g :  W orkflo w s in v olving nuanced judgmen t,  e x cep tions,  or   
con t e xt -sensitiv e decisions,  f or  e x ample r e fund appr o v al  
in cust omer  service w orkflo w s.02D i ffi c u l t - t o - m a i n t a i n  
r u l e s :S y st ems tha t ha v e become unwieldy  due t o e xt ensiv e and 
in trica t e rulese ts,  making upda t es costly  or  err or -pr one ,   
f or  e x ample perf orming v endor  security  r e vie w s.  03H e a v y  r e l i a n c e  o n  
u n s t r u c t u r e d  d a t a :Scenarios tha t in v olv e in t erpr e ting na tur al language ,   
e xtr ac ting meaning fr om documen ts,  or  in t er ac ting with  
user s con v er sa tionally ,  f or  e x ample pr ocessing a home 
insur ance claim.  Be f or e committing t o building an agen t,  v alida t e tha t y our  use case can mee t these crit eria clearly .  
Otherwise ,  a de t erministic solution ma y  suffice .
6A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

A g e n t  d e s i g n  
f o u n d a t i o n sI n its most fundamen tal f orm,  an agen t consists o f  thr ee cor e componen ts:01M o d e lThe LLM po w ering the agen t’ s r easoning and decision-making02T o o l sExt ernal func tions or  API s the agen t can use t o tak e ac tion03I n s t r u c t i o n sExplicit guidelines and guar dr ails de fining ho w  the  
agen t beha v esH er e ’ s wha t this look s lik e in code when using OpenAI’ s A gen ts SDK. Y ou can also implemen t the 
same concep ts using y our  pr e f err ed libr ary  or  building dir ec tly  fr om scr a t ch.P y t h o n1
2
3
4
5
6weather_agent = Agent(
   name=
instructions=
    tools=[get_weather],
)  ,
"Weather agent"
"You are a helpful agent who can talk to users about the 
weather.",
7A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

S e l e c t i n g  y o u r  m o d e l sDiff er en t models ha v e diff er en t str engths and tr adeo ffs r ela t ed t o task  comple xity ,  la t enc y ,  and 
cost.  A s w e ’ll see in the ne xt sec tion on Or chestr a tion,  y ou migh t w an t t o consider  using a v arie ty   
o f  models f or  diff er en t task s in the w orkflo w .
N o t e v ery  task  r equir es the smart est model—a simple r e trie v al or  in t en t classifica tion task  ma y  be 
handled b y  a smaller ,  f ast er  model,  while har der  task s lik e deciding whe ther  t o appr o v e a r e fund 
ma y  bene fit fr om a mor e capable model.
An appr oach tha t w ork s w ell is t o build y our  agen t pr o t o type with the most capable model f or  
e v ery  task  t o establish a perf ormance baseline .  F r om ther e ,  try  s w apping in smaller  models t o see  
if  the y  still achie v e accep table r esults.  This w a y ,  y ou don ’t pr ema tur ely  limit the agen t’ s abilities,  
and y ou can diagnose wher e smaller  models succeed or  f ail.I n  s u m m a r y ,  t h e  p r i n c i p l e s  f o r  c h o o s i n g  a  m o d e l  a r e  s i m p l e :  01Se t up e v als t o establish a perf ormance baseline02F ocus on mee ting y our  accur ac y  tar ge t with the best models a v ailable03Op timiz e f or  cost and la t enc y  b y  r eplacing lar ger  models with smaller  ones  
wher e possibleY ou can find a compr ehensiv e guide t o selec ting OpenAI models her e .
8A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

D e f i n i n g  t o o l sT ools e xt end y our  agen t’ s capabilities b y  using API s fr om underlying applica tions or  s y st ems.  F or  
legac y  s y st ems without API s,  agen ts can r ely  on comput er -use models t o in t er ac t dir ec tly  with 
those applica tions and s y st ems thr ough w eb and applica tion UI s—just as a human w ould.
E ach t ool should ha v e a standar diz ed de finition,  enabling fle xible ,  man y- t o-man y  r ela tionships 
be tw een t ools and agen ts.  W ell-documen t ed,  thor oughly  t est ed,  and r eusable t ools impr o v e 
disco v er ability ,  simplify  v er sion managemen t,  and pr e v en t r edundan t de finitions.
B r oadly  speaking,  agen ts need thr ee types o f  t ools:T ypeDescrip tionEx amplesDa taE nable agen ts t o r e trie v e con t e xt and 
in f orma tion necessary  f or  e x ecuting 
the w orkflo w .Query  tr ansac tion da tabases or  
s y st ems lik e CRM s,  r ead PDF  
documen ts,  or  sear ch the w eb .A c tionE nable agen ts t o in t er ac t with 
s y st ems t o tak e ac tions such as 
adding ne w  in f orma tion t o 
da tabases,  upda ting r ecor ds,  or  
sending messages.    Send emails and t e xts,  upda t e a CRM 
r ecor d,  hand-o ff  a cust omer  service 
tick e t t o a human.Or chestr a tionA gen ts themselv es can serv e as t ools 
f or  o ther  agen ts—see the M anager  
P a tt ern in the Or chestr a tion sec tion.R e fund agen t,  R esear ch agen t,  
W riting agen t.
9A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

F or  e x ample ,  her e ’ s ho w  y ou w ould equip the agen t de fined abo v e with a series o f  t ools when using 
the A gen ts SDK:P y t h o n1
2
3
4
5
6
7
8
8
10
11
12from import
def agents  Agent, WebSearchTool, function_tool
@function_tool
 save_results(output):
     db.insert({ : output, : datetime.time()})
     return "File saved"

search_agent = Agent(
    name= ,
    instructions=
    tools=[WebSearchTool(),save_results],
)"output" "timestamp"
"Search agent"
"Help the user search the internet and save results if 
asked.",
A s the number  o f  r equir ed t ools incr eases,  consider  splitting task s acr oss multiple agen ts  
( see O r chestr a tion) .
1 0A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

C o n f i g u r i n g  i n s t r u c t i o n sH igh-quality  instruc tions ar e essen tial f or  an y  LLM-po w er ed app ,  but especially  critical f or  agen ts.  
Clear  instruc tions r educe ambiguity  and impr o v e agen t decision-making,  r esulting in smoo ther  
w orkflo w  e x ecution and f e w er  err or s.Best pr actices f or  agen t instructionsU se e xisting documen tsWhen cr ea ting r outines,  use e xisting oper a ting pr ocedur es,  
support scrip ts,  or  polic y  documen ts t o cr ea t e LLM- friendly  
r outines.  I n cust omer  service f or  e x ample ,  r outines can r oughly  
map t o individual articles in y our  kno wledge base .  P r o m p t  a g e n t s  t o  b r e a k   
d o w n  t a s k sPr o viding smaller ,  clear er  st eps fr om dense r esour ces  
helps minimiz e ambiguity  and helps the model be tt er   
f ollo w  instruc tions.De fine clear  actionsM ak e sur e e v ery  st ep in y our  r outine corr esponds t o a specific 
ac tion or  output.  F or  e x ample ,  a st ep migh t instruc t the agen t 
t o ask  the user  f or  their  or der  number  or  t o call an API t o 
r e trie v e accoun t de tails.  Being e xplicit about the ac tion ( and 
e v en the w or ding o f  a user - f acing message ) lea v es less r oom  
f or  err or s in in t erpr e ta tion.  Cap tur e edge casesR eal-w orld in t er ac tions o ft en cr ea t e decision poin ts such as 
ho w  t o pr oceed when a user  pr o vides incomple t e in f orma tion  
or  ask s an une xpec t ed question.  A  r obust r outine an ticipa t es 
common v aria tions and includes instruc tions on ho w  t o handle 
them with conditional st eps or  br anches such as an alt erna tiv e 
st ep if  a r equir ed piece o f  in f o is missing.
1 1A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

Y ou can use adv anced models,  lik e o 1 or  o3-mini,  t o aut oma tically  gener a t e instruc tions fr om 
e xisting documen ts.  H er e ’ s a sample pr omp t illustr a ting this appr oach:U n s e t1“You are an expert in writing instructions for an LLM agent. Convert the 
following help center document into a clear set of instructions, written in 
a numbered list. The document will be a policy followed by an LLM. Ensure 
that there is no ambiguity, and that the instructions are written as 
directions for an agent. The help center document to convert is the 
following {{help_center_doc}}” 
1 2A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

O r c h e s t r a t i o nWith the f ounda tional componen ts in place ,  y ou can consider  or chestr a tion pa tt erns t o enable  
y our  agen t t o e x ecut e w orkflo w s e ff ec tiv ely .
While it’ s t emp ting t o immedia t ely  build a fully  aut onomous agen t with comple x  ar chit ec tur e ,  
cust omer s typically  achie v e gr ea t er  success with an incr emen tal appr oach.  
I n gener al,  or chestr a tion pa tt erns f all in t o tw o ca t egories:01Single-agen t s y st ems, wher e a single model equipped with appr opria t e t ools and 
instruc tions e x ecut es w orkflo w s in a loop02M ulti-agen t s y st ems,  wher e w orkflo w  e x ecution is distribut ed acr oss multiple 
coor dina t ed agen tsL e t’ s e xplor e each pa tt ern in de tail.
1 3A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

S i n g l e - a g e n t  s y s t e m sA  single agen t can handle man y  task s b y  incr emen tally  adding t ools,  k eeping comple xity  
manageable and simplifying e v alua tion and main t enance .  E ach ne w  t ool e xpands its capabilities 
without pr ema tur ely  f or cing y ou t o or chestr a t e multiple agen ts.
ToolsGuardrailsHooksInstructionsAgentInputOutput
E v ery  or chestr a tion appr oach needs the concep t o f  a ‘ run ’ ,  typically  implemen t ed as a loop tha t 
le ts agen ts oper a t e un til an e xit condition is r eached.  Common e xit conditions include t ool calls,   
a certain struc tur ed output,  err or s,  or  r eaching a maximum number  o f  turns.  
1 4A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

F or  e x ample ,  in the A gen ts SDK,  agen ts ar e start ed using the  me thod,  which loops 
o v er  the LLM un til either:Runner.run()01A  fi n a l - o u t p u t  t o o l  is in v ok ed,  de fined b y  a specific output type02The model r e turns a r esponse without an y  t ool calls ( e . g.,  a dir ec t user  message )Ex ample usage:P y t h o n1Agents.run(agent, [UserMessage( )])"What's the capital of the USA?"This concep t o f  a while loop is cen tr al t o the func tioning o f  an agen t.  I n multi-agen t s y st ems,  as 
y ou’ll see ne xt,  y ou can ha v e a sequence o f  t ool calls and hando ffs be tw een agen ts but allo w  the 
model t o run multiple st eps un til an e xit condition is me t.
An e ff ec tiv e str a t egy  f or  managing comple xity  without s wit ching t o a multi-agen t fr ame w ork  is t o 
use pr omp t t empla t es.  R a ther  than main taining numer ous individual pr omp ts f or  distinc t use 
cases,  use a single fle xible base pr omp t tha t accep ts polic y  v ariables.  This t empla t e appr oach 
adap ts easily  t o v arious con t e xts,  significan tly  simplifying main t enance and e v alua tion.  A s ne w  use 
cases arise ,  y ou can upda t e v ariables r a ther  than r e writing en tir e w orkflo w s.U n s e t1""" You are a call center agent. You are interacting with 
{{user_first_name}} who has been a member for {{user_tenure}}. The user's 
most common complains are about {{user_complaint_categories}}. Greet the 
user, thank them for being a loyal customer, and answer any questions the 
user may have!
1 5A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s