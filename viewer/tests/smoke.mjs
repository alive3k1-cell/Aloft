import {chromium} from 'playwright-core';import path from 'node:path';
const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage({viewport:{width:1400,height:950},deviceScaleFactor:.75});
await p.addInitScript(()=>{localStorage.setItem('aloft-workbench-v10',JSON.stringify({playing:false,quality:'balanced'}));window.__runtimeErrors=[];window.addEventListener('error',e=>window.__runtimeErrors.push(e.message));});
p.on('pageerror',e=>console.log('PAGEERROR',e.message));p.on('console',m=>{if(m.type()==='error')console.log('CONSOLE',m.text().slice(0,2000));});
await p.goto(process.env.VIEWER_URL||'http://127.0.0.1:8080');
try{await p.waitForFunction(()=>window.__aloft?.getStats().frame>=1||window.__runtimeErrors?.length||document.getElementById('error')?.hidden===false,null,{timeout:90000});console.log('STATS',await p.evaluate(()=>window.__aloft?.getStats()));console.log('ERRORS',await p.evaluate(()=>window.__runtimeErrors));console.log('ERROR_PANEL',await p.locator('#error').textContent());await p.screenshot({path:'test-output/first.png',timeout:90000});}catch(e){console.log('FAIL',e.message,await p.locator('#error').textContent());await p.screenshot({path:'test-output/failure.png'});process.exitCode=1;}
await b.close();
