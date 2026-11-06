import {chromium} from 'playwright-core';import fs from 'node:fs/promises';import assert from 'node:assert/strict';
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
await fs.mkdir('test-output/v12',{recursive:true});const errors=[],result=process.argv[2]?JSON.parse(await fs.readFile('test-output/v12/review.json','utf8')).result:{};
const roof={position:[-18,49,9],target:[8,42,-21],fov:48};const terrace={position:[-7,12,-54],target:[27,5,-31],fov:58};
const views=[['twilight_1835',null,18+35/60],['night',null,23.5],['pool',roof,23.5],['pool_cinematic',roof,23.5],['terrace',terrace,13]];
try{
 for(const [id,view,time] of views){
  if(process.argv[2]&&process.argv[2]!==id)continue;
  const p=await browser.newPage({viewport:{width:1280,height:900},deviceScaleFactor:1});p.setDefaultTimeout(120000);p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  const state={view:view?'saved':'general',savedView:view,playing:false,scenario:'reference',quality:id.endsWith('cinematic')?'cinematic':'balanced',time,exposure:.4};await p.addInitScript(s=>localStorage.setItem('aloft-workbench-v10',JSON.stringify(s)),state);
  await p.goto('http://127.0.0.1:8080');await p.waitForFunction(()=>window.__aloft?.getStats().frame>=1,null,{timeout:120000});await p.locator('#panel-toggle').click();await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await p.screenshot({path:`test-output/v12/${id}.png`});
  result[id]=await p.evaluate(()=>({stats:window.__aloft.getStats(),environment:window.__aloft.getEnvironmentStats()}));assert.equal(result[id].stats.architecture,90);assert.equal(result[id].stats.neon,65);assert.equal(result[id].stats.spillOcclusion,'static_visibility_5_samples_per_strip');await p.close();console.log('Captured',id);
 }
 assert.deepEqual(errors,[]);await fs.writeFile('test-output/v12/review.json',JSON.stringify({result,errors},null,2));
}finally{await browser.close();}
