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