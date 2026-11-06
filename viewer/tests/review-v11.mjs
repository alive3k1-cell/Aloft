import {chromium} from 'playwright-core';import fs from 'node:fs/promises';
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
await fs.mkdir('test-output/v11',{recursive:true});
const views={pool:{position:[-18,41,-24.2],target:[3,43.5,-24.2],fov:52},courtyard:{position:[-3,60,23],target:[25,44,-9],fov:50},terrace:{position:[-7,12,-54],target:[27,5,-31],fov:58}};
const which=process.argv[2]||'after';const path=which==='before'?'/v10-base.html':'/';const errors=[];const result={};
try{
 for(const [id,view] of [...Object.entries(views),['general_day',null],['general_night',null],['pool_night',views.pool],['courtyard_night',views.courtyard]]){
  const page=await browser.newPage({viewport:{width:1280,height:900},deviceScaleFactor:1});page.setDefaultTimeout(120000);page.on('pageerror',e=>errors.push(e.message));
  const state={view:view?'saved':'general',savedView:view,playing:false,scenario:'reference',quality:'balanced',time:id.includes('night')?23.5:13,exposure:.4};
  await page.addInitScript(s=>localStorage.setItem('aloft-workbench-v10',JSON.stringify(s)),state);
  await page.goto('http://127.0.0.1:8080'+path);await page.waitForFunction(()=>window.__aloft?.getStats().frame>=1,null,{timeout:120000});
  await page.locator('#panel-toggle').click();await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
  if(id==='pool_night'){await page.locator('#panel-toggle').click();await page.locator('#variant').selectOption('warm');await page.locator('#panel-toggle').click();}
  await page.screenshot({path:`test-output/v11/${which}-${id}.png`});result[id]=await page.evaluate(()=>({stats:window.__aloft.getStats(),environment:window.__aloft.getEnvironmentStats?.()}));await page.close();console.log('Captured',which,id);
 }
 await fs.writeFile(`test-output/v11/${which}.json`,JSON.stringify({result,errors},null,2));if(errors.length)throw Error(errors.join('\n'));
}finally{await browser.close();}
