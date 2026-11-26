"""Free tools for job seekers. Each tool is a static page with a small script (no server needed).
build.py turns every entry into /tools/<slug>/ with FAQ schema, related jobs and internal links."""

TOOLS = [
{
"slug": "hourly-to-salary-calculator",
"name": "Hourly to Salary Calculator",
"title": "Hourly to Salary Calculator – Hourly, Monthly & Yearly Pay",
"desc": "Free hourly to salary calculator: turn an hourly wage into weekly, monthly and yearly pay, or a salary back into an hourly rate. Works for part-time hours too.",
"intro": "Turn an hourly wage into yearly, monthly, bi-weekly and weekly pay, or work out the hourly rate behind a salary. Change the hours per week to see part-time pay.",
"phrases": ["hourly to salary calculator", "salary calculator", "hourly to salary", "salary to hourly"],
"cats": ["remote-customer-service-jobs", "remote-virtual-assistant-jobs", "remote-data-entry-jobs"],
"html": """<div class="tool-box" id="payTool">
<div class="tool-row"><label>Amount ($)<input type="number" id="pAmt" value="20" min="0" step="0.01"></label>
<label>Per<select id="pPer"><option value="hour">Hour</option><option value="day">Day</option><option value="week">Week</option><option value="month">Month</option><option value="year">Year</option></select></label></div>
<div class="tool-row"><label>Hours per week<input type="number" id="pHrs" value="40" min="1" max="100"></label>
<label>Weeks per year<input type="number" id="pWks" value="52" min="1" max="52"></label></div>
<table class="tool-table" id="pOut"></table>
<p class="muted">Before taxes. Unpaid time off lowers the yearly total: set weeks per year to 50 for two unpaid weeks.</p></div>""",
"js": """(function(){var f=function(n){return '$'+n.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});};
function run(){var a=+pAmt.value||0,h=+pHrs.value||40,w=+pWks.value||52,p=pPer.value,yr;
yr={hour:a*h*w,day:a*5*w,week:a*w,month:a*12,year:a}[p];
var rows=[['Hourly',yr/(h*w)],['Daily (8 hours)',yr/(h*w)*8],['Weekly',yr/w],['Bi-weekly',yr/w*2],['Monthly',yr/12],['Yearly',yr]];
pOut.innerHTML=rows.map(function(r){return '<tr><th>'+r[0]+'</th><td>'+f(r[1])+'</td></tr>';}).join('');}
['pAmt','pPer','pHrs','pWks'].forEach(function(i){document.getElementById(i).addEventListener('input',run);});run();})();""",
"howto": """<h2>How the calculation works</h2><p>Yearly pay = hourly rate × hours per week × weeks per year. With a standard 40-hour week and 52 paid weeks, that is 2,080 hours a year, so $20 an hour is $41,600 a year. Monthly pay is the yearly total divided by 12, and bi-weekly pay is two weeks of pay, which is how most US employers pay.</p>
<p>Going the other way, divide a salary by 2,080 to get the hourly rate: a $50,000 salary is about $24.04 an hour. Part-time jobs work the same way with fewer hours, so 20 hours a week at $20 an hour is $20,800 a year.</p>
<h2>Comparing remote job offers</h2><p>Remote jobs often list pay differently: customer support and virtual assistant roles usually show an hourly rate, while software and marketing roles show a yearly salary. Put both into the same unit before you compare. Also check whether the job is a contract (no benefits, you pay your own taxes) or an employee role.</p>""",
"faq": [("How much is $20 an hour per year?", "At 40 hours a week for 52 weeks, $20 an hour is $41,600 a year before taxes, about $3,467 a month."),
        ("How many work hours are in a year?", "A full-time year is usually counted as 2,080 hours: 40 hours a week times 52 weeks."),
        ("Does this include taxes?", "No. All results are gross pay before taxes and deductions, which depend on your country and situation.")],
},
{
"slug": "typing-speed-test",
"name": "Typing Speed Test",
"title": "Typing Speed Test (WPM) – Free 1-Minute Test for Data Entry Jobs",
"desc": "Free 1-minute typing speed test. See your words per minute (WPM) and accuracy, and how they compare with what data entry, transcription and support jobs ask for.",
"intro": "Check your words per minute (WPM) and accuracy in 60 seconds. Many data entry, transcription and chat support jobs ask for a typing speed, so it helps to know yours before you apply.",
"phrases": ["typing speed test", "typing test", "words per minute", "typing speed"],
"cats": ["remote-data-entry-jobs", "remote-transcription-translation-jobs", "remote-customer-service-jobs"],
"html": """<div class="tool-box" id="typeTool">
<p class="type-text" id="tText"></p>
<textarea id="tIn" rows="4" placeholder="Click here and start typing the text above. The timer starts with your first key." autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"></textarea>
<div class="tool-stats"><div><b id="tTime">60</b><span>seconds</span></div><div><b id="tWpm">0</b><span>WPM</span></div><div><b id="tAcc">100%</b><span>accuracy</span></div></div>
<p id="tMsg" class="muted"></p><button class="btn" id="tReset" type="button">Restart with a new text</button></div>""",
"js": """(function(){var T=['Remote work gives you the freedom to plan your day, but it also asks for discipline. Set clear working hours, keep a tidy desk and answer messages quickly so your team always knows they can count on you.',
'A good customer support agent reads each question carefully, writes a short and friendly answer, and checks that the problem is really solved before closing the ticket. Speed matters, but accuracy matters more.',
'Data entry work means copying information from one place to another without mistakes. Names, numbers and dates must be exact, so careful typing and a quick final check are the most valuable skills you can bring.',
'Before you apply for a job, read the whole listing, note the countries the company hires from and the hours it expects. Then tailor your resume so the first lines show the skills the employer asked for.'];
var txt,start=0,timer=null,done=false;
function pick(){txt=T[Math.floor(Math.random()*T.length)];tText.textContent=txt;tIn.value='';tIn.disabled=false;start=0;done=false;clearInterval(timer);tTime.textContent='60';tWpm.textContent='0';tAcc.textContent='100%';tMsg.textContent='';}
function score(){var v=tIn.value,ok=0;for(var i=0;i<v.length;i++){if(v[i]===txt[i])ok++;}
var mins=Math.max((Date.now()-start)/60000,1/60),wpm=Math.round(ok/5/mins),acc=v.length?Math.round(ok/v.length*100):100;tWpm.textContent=wpm;tAcc.textContent=acc+'%';return[wpm,acc];}
function finish(){done=true;clearInterval(timer);tIn.disabled=true;var s=score(),w=s[0],m;
m=w>=60?'Excellent: fast enough for transcription and most data entry tests.':w>=45?'Good: meets the 40-45 WPM many data entry and chat support jobs ask for.':w>=35?'Fair: practise a little to reach the common 40 WPM requirement.':'Keep practising: most typing-based jobs ask for at least 35-40 WPM.';
tMsg.textContent='Result: '+w+' WPM at '+s[1]+'% accuracy. '+m;}
tIn.addEventListener('input',function(){if(done)return;if(!start){start=Date.now();timer=setInterval(function(){var left=60-Math.floor((Date.now()-start)/1000);tTime.textContent=Math.max(left,0);score();if(left<=0)finish();},250);}
if(tIn.value.length>=txt.length)finish();});
tIn.addEventListener('paste',function(e){e.preventDefault();});tReset.addEventListener('click',pick);pick();})();""",
"howto": """<h2>What typing speed do remote jobs ask for?</h2><p>Data entry jobs usually ask for 40 to 50 words per minute with high accuracy. Chat support roles often expect around 40 WPM because you may handle two or three chats at once. General transcription work usually needs 60 WPM or more, and some employers give their own timed test during the application.</p>
<h2>How WPM is calculated</h2><p>One "word" is counted as five characters, including spaces. Only correctly typed characters count toward your speed, so mistakes lower both your WPM and your accuracy. Accuracy matters as much as speed: most employers would rather hire someone typing 40 WPM at 98% accuracy than 70 WPM at 85%.</p>
<h2>How to get faster</h2><ul><li>Keep your fingers on the home row (ASDF and JKL;) and stop looking at the keyboard.</li><li>Practise 10 minutes a day; steady practice beats long sessions.</li><li>Slow down to stay above 95% accuracy, and speed will follow.</li></ul>""",
"faq": [("What is a good typing speed for data entry jobs?", "Most data entry jobs ask for 40 to 50 words per minute with at least 95% accuracy."),
        ("What is the average typing speed?", "The average adult types about 40 words per minute. Professional typists and transcriptionists often reach 65 to 75 WPM."),
        ("Does accuracy matter more than speed?", "For most jobs, yes. Errors cost time to fix, so employers usually look for high accuracy first.")],
},
{
"slug": "job-scam-checker",
"name": "Remote Job Scam Checker",
"title": "Remote Job Scam Checker – Is This Job Offer Real?",
"desc": "Paste a job offer, email or chat message and get an instant check for common remote job scam signs: upfront fees, check deposits, Telegram interviews and more.",
"intro": "Got a job offer that feels too good to be true? Paste the message below. The checker looks for the warning signs that show up again and again in remote job scams. Nothing you paste leaves your browser.",
"phrases": ["job scam checker", "remote job scams", "fake job offer", "job scam"],
"cats": ["remote-data-entry-jobs", "remote-customer-service-jobs", "remote-virtual-assistant-jobs"],
"html": """<div class="tool-box" id="scamTool">
<textarea id="sIn" rows="8" placeholder="Paste the job offer, email or chat message here..."></textarea>
<button class="btn" id="sGo" type="button">Check this message</button>
<div id="sOut" class="scam-out" hidden></div></div>""",
"js": """(function(){var R=[
[/(pay|send|deposit|transfer)[^.]{0,40}(fee|deposit|training|starter kit|equipment|registration|background check)/i,30,'Asks you to pay for training, equipment, a starter kit or a background check. Real employers never charge you to work.'],
[/(check|cheque)[^.]{0,60}(deposit|mobile deposit|bank)|deposit[^.]{0,40}(check|cheque)/i,30,'Mentions depositing a check. Fake-check scams send a check, then ask you to send part of the money back or buy equipment.'],
[/(telegram|whatsapp|signal|google hangouts|wire app)/i,15,'Moves the conversation or interview to Telegram, WhatsApp or another chat app. Real companies interview by video call or phone and email from their own domain.'],
[/(gift ?cards?|bitcoin|crypto|usdt|western union|moneygram|zelle|cash app|wire transfer)/i,25,'Mentions gift cards, crypto, Zelle, Cash App or wire transfers. These payment methods are favourites of scammers because they are hard to reverse.'],
[/(no interview|without (an )?interview|hired immediately|instant(ly)? hired|you have been selected|congratulations[^.]{0,30}(selected|hired))/i,15,'Offers the job without a real interview, or says you were "selected" for a job you did not apply for.'],
[/(\\$\\s?\\d{3,4}\\s?(per|a|\\/)\\s?(day|hour)|earn \\$?\\d{3,}[^.]{0,20}(daily|a day|per day))/i,15,'Promises unusually high pay for simple work. Easy work paying hundreds per day is a classic lure.'],
[/(reship|re-ship|package (handling|forwarding)|receive packages|parcel)/i,25,'Involves receiving or reshipping packages at home, which is often linked to stolen goods.'],
[/(bank (account|login|details)|social security|ssn|passport|routing number)[^.]{0,40}(before|to start|now|asap|immediately)/i,20,'Asks for bank details, a Social Security number or ID documents before you have a signed offer.'],
[/(@gmail\\.com|@yahoo\\.com|@outlook\\.com|@hotmail\\.com|@proton)/i,10,'Uses a free email address (Gmail, Yahoo, Outlook) instead of a company domain.'],
[/(task|order|rating|like|review)s?[^.]{0,40}(commission|recharge|top.?up|unlock)/i,30,'Describes "tasks" that earn commission after you top up or recharge an account. This is the common task scam.'],
[/(urgent|act now|limited spots|respond within|asap)/i,8,'Pushes you to act fast. Pressure is used to stop you from checking the offer.']];
var G=[[/(linkedin\\.com\\/company|careers\\.|greenhouse\\.io|lever\\.co|ashbyhq\\.com|workable\\.com|smartrecruiters\\.com)/i,'Links to a real company careers page or applicant tracking system.'],[/(video (call|interview)|zoom|microsoft teams|google meet)/i,'Mentions a video interview.']];
sGo.addEventListener('click',function(){var t=sIn.value,score=0,hits=[],good=[];if(t.trim().length<20){sOut.hidden=false;sOut.innerHTML='<p>Paste the full message first.</p>';return;}
R.forEach(function(r){if(r[0].test(t)){score+=r[1];hits.push(r[2]);}});G.forEach(function(g){if(g[0].test(t))good.push(g[1]);});
var lvl=score>=40?['high','High risk: this looks like a scam. Do not pay, share bank details or deposit any check.']:score>=15?['medium','Some warning signs. Verify the company before you go further.']:['low','No common scam signs found. That does not prove the job is real, so still verify the company.'];
sOut.hidden=false;sOut.className='scam-out '+lvl[0];
sOut.innerHTML='<h3>'+lvl[1]+'</h3>'+(hits.length?'<p><b>Warning signs found:</b></p><ul>'+hits.map(function(h){return '<li>'+h+'</li>';}).join('')+'</ul>':'')+(good.length?'<p><b>Good signs:</b></p><ul>'+good.map(function(h){return '<li>'+h+'</li>';}).join('')+'</ul>':'')+'<p class="muted">Always check that the job appears on the company\\'s own careers page before you apply.</p>';});})();""",
"howto": """<h2>How to check if a remote job is real</h2><ol><li><b>Find the job on the company's own website.</b> Go to the company's careers page yourself (do not use the link in the message) and look for the same job title.</li><li><b>Check the email domain.</b> Recruiters write from the company's own domain, not from Gmail or Yahoo.</li><li><b>Expect a real interview.</b> Legitimate employers interview you by video or phone. A "chat interview" on Telegram is a red flag.</li><li><b>Never pay to start.</b> No real employer charges for training, equipment or a background check, and none will ask you to deposit a check and send money back.</li></ol>
<p>Every job on our site links to the employer's own application page, so you can always confirm the company is real before you apply.</p>""",
"faq": [("What are the most common remote job scams?", "Fake check scams, upfront fee scams for training or equipment, task or commission scams that ask you to top up an account, and reshipping scams."),
        ("Is a job offer on Telegram or WhatsApp real?", "Very rarely. Real companies interview through video calls and email from their own domain. Treat chat-app job offers with suspicion."),
        ("Does this checker store what I paste?", "No. The check runs entirely in your browser and nothing is sent to our server.")],
},
{
"slug": "cover-letter-generator",
"name": "Cover Letter Generator",
"title": "Free Cover Letter Generator for Remote Jobs",
"desc": "Write a tailored cover letter for a remote job in one minute. Fill in the job title, company and your strengths, then copy a clean, editable letter.",
"intro": "Fill in a few details and get a short, professional cover letter written for a remote role. Edit it freely, then paste it into the employer's application form.",
"phrases": ["cover letter generator", "cover letter", "cover letters"],
"cats": ["remote-customer-service-jobs", "remote-virtual-assistant-jobs", "remote-marketing-jobs"],
"html": """<div class="tool-box" id="clTool">
<div class="tool-row"><label>Your name<input id="cName" placeholder="Maria Santos"></label><label>Job title<input id="cJob" placeholder="Customer Support Specialist"></label></div>
<div class="tool-row"><label>Company<input id="cCo" placeholder="Acme Inc."></label><label>Years of experience<input id="cYrs" type="number" min="0" value="2"></label></div>
<label>Your top skills (comma separated)<input id="cSkills" placeholder="live chat support, Zendesk, written English, problem solving"></label>
<label>One result you are proud of (optional)<input id="cWin" placeholder="kept a 96% customer satisfaction score across 1,200 tickets"></label>
<label>Tone<select id="cTone"><option value="friendly">Friendly</option><option value="formal">Formal</option></select></label>
<button class="btn" id="cGo" type="button">Write my cover letter</button>
<textarea id="cOut" rows="14" hidden></textarea><button class="btn" id="cCopy" type="button" hidden>Copy letter</button></div>""",
"js": """(function(){function v(i,d){var x=document.getElementById(i).value.trim();return x||d;}
cGo.addEventListener('click',function(){var n=v('cName','[Your Name]'),j=v('cJob','[Job Title]'),c=v('cCo','[Company]'),y=+v('cYrs','0'),s=v('cSkills','').split(',').map(function(x){return x.trim();}).filter(Boolean),w=v('cWin',''),f=cTone.value==='formal';
var sk=s.length>1?s.slice(0,-1).join(', ')+' and '+s[s.length-1]:(s[0]||'clear communication and reliability');
var exp=y>0?('With '+y+' year'+(y>1?'s':'')+' of experience, '):'As someone eager to start a remote career, ';
var L=[(f?'Dear Hiring Manager,':'Hi '+c+' team,'),'',
'I am writing to apply for the '+j+' position at '+c+'. '+exp+'I bring strong skills in '+sk+', and I am confident I can contribute from day one.',
'',(w?'In my most recent work I '+w.replace(/^i /i,'')+'. ':'')+'I am used to working independently, managing my own schedule and keeping my team updated in writing, which are the habits that make remote work succeed.',
'','I have a reliable internet connection, a quiet home workspace and I am comfortable with the tools remote teams use every day, such as Slack, Google Workspace and video calls. I can adapt my hours to overlap with your team\\'s time zone.',
'','I would welcome the chance to discuss how I can help '+c+'. Thank you for your time and consideration.','',(f?'Sincerely,':'Best regards,'),n];
cOut.value=L.join('\\n');cOut.hidden=false;cCopy.hidden=false;});
cCopy.addEventListener('click',function(){cOut.select();try{navigator.clipboard.writeText(cOut.value);}catch(e){document.execCommand('copy');}cCopy.textContent='Copied!';setTimeout(function(){cCopy.textContent='Copy letter';},1500);});})();""",
"howto": """<h2>What makes a good cover letter for a remote job</h2><p>Keep it short: three or four paragraphs that a recruiter can read in under a minute. Name the exact job title and company, show one or two skills that match the listing, and add one concrete result with a number if you can.</p>
<p>For remote roles, employers also want proof that you can work on your own. Mention your home setup, your experience with written communication and the hours you can work. Always read the generated letter and change anything that is not true for you, since a personal touch beats a template.</p>""",
"faq": [("Do remote jobs need a cover letter?", "Many do not require one, but a short tailored letter helps you stand out, especially for support, assistant and writing roles."),
        ("How long should a cover letter be?", "Aim for 200 to 300 words: three or four short paragraphs."),
        ("Is the generator free?", "Yes. It runs in your browser, is free and does not store your details.")],
},
{
"slug": "time-zone-converter",
"name": "Remote Work Time Zone Converter",
"title": "Time Zone Converter for Remote Workers – Overlap Hours Calculator",
"desc": "Convert a meeting or shift time between your time zone and your employer's, and see how many of your working hours overlap with a 9-to-5 day in their city.",
"intro": "Remote jobs often say things like \"must overlap with US Eastern hours\". Pick your time zone and the employer's to convert any time and see your overlap with their working day.",
"phrases": ["time zone converter", "time zones", "time zone"],
"cats": ["remote-customer-service-jobs", "remote-software-development-jobs", "remote-virtual-assistant-jobs"],
"html": """<div class="tool-box" id="tzTool">
<div class="tool-row"><label>Your time zone<select id="zMe"></select></label><label>Employer's time zone<select id="zThem"></select></label></div>
<div class="tool-row"><label>Time at the employer<input type="time" id="zTime" value="09:00"></label><label>Their working hours<select id="zHours"><option value="9-17">9 am – 5 pm</option><option value="8-16">8 am – 4 pm</option><option value="10-18">10 am – 6 pm</option></select></label></div>
<div id="zOut" class="tz-out"></div></div>""",
"js": """(function(){var Z=[['Pacific Time (Los Angeles)','America/Los_Angeles'],['Mountain Time (Denver)','America/Denver'],['Central Time (Chicago)','America/Chicago'],['Eastern Time (New York)','America/New_York'],['Brazil (São Paulo)','America/Sao_Paulo'],['UK (London)','Europe/London'],['Central Europe (Berlin)','Europe/Berlin'],['Eastern Europe (Athens)','Europe/Athens'],['Nigeria (Lagos)','Africa/Lagos'],['South Africa (Johannesburg)','Africa/Johannesburg'],['Kenya (Nairobi)','Africa/Nairobi'],['UAE (Dubai)','Asia/Dubai'],['Pakistan (Karachi)','Asia/Karachi'],['India (Kolkata)','Asia/Kolkata'],['Bangladesh (Dhaka)','Asia/Dhaka'],['Indonesia (Jakarta)','Asia/Jakarta'],['Philippines (Manila)','Asia/Manila'],['Singapore','Asia/Singapore'],['Japan (Tokyo)','Asia/Tokyo'],['Australia (Sydney)','Australia/Sydney'],['New Zealand (Auckland)','Pacific/Auckland'],['Mexico (Mexico City)','America/Mexico_City'],['Colombia (Bogotá)','America/Bogota'],['Argentina (Buenos Aires)','America/Argentina/Buenos_Aires'],['Canada (Toronto)','America/Toronto']];
function off(z){var d=new Date(),s=d.toLocaleString('en-US',{timeZone:z,hour12:false}),u=d.toLocaleString('en-US',{timeZone:'UTC',hour12:false});return (new Date(s)-new Date(u))/3600000;}
var guess='';try{guess=Intl.DateTimeFormat().resolvedOptions().timeZone;}catch(e){}
[zMe,zThem].forEach(function(sel,k){sel.innerHTML=Z.map(function(z){return '<option value="'+z[1]+'">'+z[0]+'</option>';}).join('');});
if(guess&&Z.some(function(z){return z[1]===guess;}))zMe.value=guess;else zMe.value='Asia/Manila';zThem.value='America/New_York';
function fmt(h){h=((h%24)+24)%24;var hh=Math.floor(h),mm=Math.round((h-hh)*60);if(mm===60){hh=(hh+1)%24;mm=0;}var ap=hh>=12?'pm':'am',h12=hh%12||12;return h12+':'+(mm<10?'0':'')+mm+' '+ap;}
function run(){var d=off(zMe.value)-off(zThem.value),t=zTime.value.split(':'),h=+t[0]+(+t[1])/60,wh=zHours.value.split('-').map(Number);
var mine=h+d,dayShift=mine>=24?' (next day)':mine<0?' (previous day)':'';
var s=wh[0]+d,e=wh[1]+d;var ov=0;for(var x=0;x<24;x+=0.5){var m=((x-d)%24+24)%24;if(m>=wh[0]&&m<wh[1]&&x>=9&&x<17)ov+=0.5;}
zOut.innerHTML='<p><b>'+fmt(h)+'</b> for the employer is <b>'+fmt(mine)+dayShift+'</b> for you ('+(d>=0?'+':'')+d+' hours).</p><p>Their working day ('+fmt(wh[0])+' – '+fmt(wh[1])+') runs from <b>'+fmt(s)+'</b> to <b>'+fmt(e)+'</b> your time.</p><p>Overlap with your own 9 am – 5 pm day: <b>'+ov+' hours</b>. '+(ov>=4?'Easy to work together.':ov>0?'Some overlap: shifting your day a little would help.':'No overlap: expect a night or early-morning shift.')+'</p>';}
[zMe,zThem,zTime,zHours].forEach(function(el){el.addEventListener('input',run);});run();})();""",
"howto": """<h2>Why time zones matter for remote jobs</h2><p>Many remote employers ask for a few hours of overlap with their team, for example "4 hours overlap with US Eastern Time". Customer support jobs often go further and expect you to work the customer's daytime, which can mean night shifts if you live in Asia or Africa. Check the overlap before you apply so you know what your schedule would really look like.</p>
<p>Daylight saving time shifts the difference by an hour in parts of the year. This converter uses today's date, so it always shows the current difference.</p>""",
"faq": [("What time is 9 am Eastern in the Philippines?", "Manila is usually 12 or 13 hours ahead of New York, so 9 am Eastern is 9 pm or 10 pm in the Philippines, depending on US daylight saving time."),
        ("What does 'overlap with US hours' mean?", "It means some of your working hours must fall inside the employer's normal working day so you can join meetings and reply quickly."),
        ("Does the converter handle daylight saving time?", "Yes. It uses your browser's time zone data for today's date.")],
},
]
