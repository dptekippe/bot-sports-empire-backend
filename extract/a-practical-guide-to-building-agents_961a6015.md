51
52
53
54
55
56
 This should trip the guardrail
    
          Runner.run(agent, 
         ( )
    except GuardrailTripwireTriggered:
        ( )
try:
await
print
 print"I think I might cancel my subscription")
"Guardrail didn't trip - this is unexpected"
"Churn detection guardrail tripped"
3 0A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s

The A gen ts SDK  tr ea ts guar dr ails as fir st -class concep ts,  r elying on op timistic e x ecution b y  
de f ault.  U nder  this appr oach,  the primary  agen t pr oac tiv ely  gener a t es outputs while guar dr ails  
run concurr en tly ,  triggering e x cep tions if  constr ain ts ar e br eached.    
Guar dr ails can be implemen t ed as func tions or  agen ts tha t en f or ce policies such as jailbr eak  
pr e v en tion,  r ele v ance v alida tion,  k e yw or d filt ering,  blocklist en f or cemen t,  or  sa f e ty  classifica tion.  
F or  e x ample ,  the agen t abo v e pr ocesses a ma th question input op timistically  un til the 
ma th_home w ork_ trip wir e guar dr ail iden tifies a viola tion and r aises an e x cep tion.P l a n  f o r  h u m a n  i n t e r v e n t i o n
H uman in t erv en tion is a critical sa f eguar d enabling y ou t o impr o v e an agen t’ s r eal-w orld 
perf ormance without compr omising user  e xperience .  It’ s especially  importan t early   
in deplo ymen t,  helping iden tify  f ailur es,  unco v er  edge cases,  and establish a r obust 
e v alua tion c y cle .
I mplemen ting a human in t erv en tion mechanism allo w s the agen t t o gr ace fully  tr ansf er  
con tr ol when it can ’t comple t e a task.  I n cust omer  service ,  this means escala ting the issue  
t o a human agen t.  F or  a coding agen t,  this means handing con tr ol back  t o the user .
T w o primary  trigger s typically  w arr an t human in t erv en tion:
Ex ceeding f ailur e thr esholds: Se t limits on agen t r e tries or  ac tions.  If  the agen t e x ceeds 
these limits ( e . g.,  f ails t o under stand cust omer  in t en t a ft er  multiple a tt emp ts ) ,  escala t e 
t o human in t erv en tion.
H igh-risk  actions: A c tions tha t ar e sensitiv e ,  irr e v er sible ,  or  ha v e high stak es should 
trigger  human o v er sigh t un til con fidence in the agen t’ s r eliability  gr o w s.  Ex amples 
include canceling user  or der s,  authorizing lar ge r e funds,  or  making pa ymen ts.  
3 1A  p r a c t i c a l  g u i d e  t o  b u i l d i n g  a g e n t s