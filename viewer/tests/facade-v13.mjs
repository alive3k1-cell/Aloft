import {chromium} from 'playwright-core';import fs from 'node:fs/promises';import assert from 'node:assert/strict';import {defaults,applyVariant} from '../src/state.js';
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
await fs.mkdir('test-output/v13',{recursive:true});const result={},errors=[];const mode=process.argv[2]||'after';
const view={name:'Главный фасад — проверка засветки',position:[26,23.5,-120],target:[26,23.5,-29],type:'ORTHO',orthoHeight:51,fov:37};
async function settle(p){await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
async function save(p,name){await settle(p);const png=await p.evaluate(()=>window.__aloft.getRenderer().domElement.toDataURL('image/png').split(',')[1]);await fs.writeFile(`test-output/v13/${name}.png`,Buffer.from(png,'base64'));}
try{
 for(const quality of (mode==='before'?['balanced']:['fast','balanced','cinematic'])){
  const p=await browser.newPage({viewport:{width:960,height:850},deviceScaleFactor:1});p.setDefaultTimeout(120000);p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  const s=defaults();applyVariant(s,'lime');Object.assign(s,{view:'saved',savedView:view,playing:false,scenario:'reference',quality,time:23.5,exposure:.4,bloom:0});s.groups.POOL.enabled=false;
  await p.addInitScript(s=>localStorage.setItem('aloft-workbench-v10',JSON.stringify(s)),s);await p.goto('http://127.0.0.1:8080/'+(mode==='before'?'v12-base.html':''));await p.waitForFunction(()=>window.__aloft?.getStats().frame>=1,null,{timeout:120000});await p.locator('#panel-toggle').click();await settle(p);
  await save(p,`${mode}-${quality}-on`);result[quality]={stats:await p.evaluate(()=>window.__aloft.getStats()),environment:await p.evaluate(()=>window.__aloft.getEnvironmentStats())};
  if(mode==='after'){
   const status=await p.evaluate(()=>window.__aloft.getSpillStats());assert.ok(status.filter(x=>x.group!=='POOL').every(x=>x.intensity===0));result[quality].facadeSpillZero=true;
   // Scenario changes must not re-enable the unwanted facade lamps.
   for(const scenario of ['wave','chase','fade','dots','show']){await p.locator('#scenario').evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('change'));},scenario);await settle(p);assert.ok((await p.evaluate(()=>window.__aloft.getSpillStats())).filter(x=>x.group!=='POOL').every(x=>x.intensity===0));}
   await p.locator('#scenario').evaluate(e=>{e.value='reference';e.dispatchEvent(new Event('change'));});await settle(p);
  }
  await p.locator('#show-neon').evaluate(e=>{e.checked=false;e.dispatchEvent(new Event('change'));});await save(p,`${mode}-${quality}-off`);
  if(mode==='after'&&quality==='balanced'){
   await p.locator('#show-neon').evaluate(e=>{e.checked=true;e.dispatchEvent(new Event('change'));});await p.locator('#bloom').evaluate(e=>{e.value=.25;e.dispatchEvent(new Event('input'));});await save(p,'front-final');
   await p.locator('#g-POOL-enabled').evaluate(e=>{e.checked=true;e.dispatchEvent(new Event('change'));});await settle(p);assert.ok((await p.evaluate(()=>window.__aloft.getSpillStats())).some(x=>x.group==='POOL'&&x.intensity>0));result.poolFillRetained=true;
  }
  await p.close();console.log('Checked',mode,quality);
 }
 assert.deepEqual(errors,[]);await fs.writeFile(`test-output/v13/${mode}.json`,JSON.stringify({result,errors},null,2));
}finally{await browser.close();}
