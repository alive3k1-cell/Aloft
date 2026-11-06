export const GROUPS=['ROOF','BIG_FRAME','UPPER_FRAME','POOL'];
export const GROUP_NAMES={ROOF:'Кровля',BIG_FRAME:'Большая рама',UPPER_FRAME:'Верхняя рама',POOL:'Бассейн'};
export const DESCRIPTIONS={reference:'Розовая кромка, бирюзовая большая рама и салатовая верхняя — цвета исходного примера.',wave:'Мягкие волны цвета и яркости движутся по проектным контурам.',chase:'Плавный световой акцент проходит по контурам. Остальная линия остаётся приглушённой.',fade:'Спокойная смена оттенков с сохранением разницы между группами.',dots:'Лаймовые и мятные волны на проектных линиях, с мягкими белыми акцентами.',show:'30 секунд: исходные цвета, волна, бегущий свет и смена оттенка с плавными переходами.'};
export const PRESETS={general:{name:'Общий вид',position:[-32,43,-68],target:[26,23,-16],fov:44},front:{name:'Главный фасад',position:[26,27,-120],target:[26,25,-29],fov:37},side:{name:'Торец',position:[115,30,-20],target:[44,24,-15],fov:39},street:{name:'С улицы',position:[-25,2,-74],target:[25,24,-26],fov:53},courtyard:{name:'Двор',position:[-40,35,38],target:[18,24,-15],fov:45},top:{name:'Сверху',position:[26,118,-15.05],target:[26,20,-15],fov:42},roof:{name:'Кровля',position:[85,85,65],target:[25,43,-16],fov:42},pool:{name:'Бассейн',position:[-14,44.8,-38],target:[2.5,43.2,-24],fov:48}};
export const BASE_COLORS={ROOF:[.9,.015,.5],BIG_FRAME:[.015,.8,.55],UPPER_FRAME:[.5,.9,.035],POOL:[0,0,0]};
export function defaults(){return {schema:'aloft-workbench/1',tab:'lighting',view:'general',reference:'',navigation:'orbit',time:23.5,exposure:.4,quality:'balanced',variant:'reference',scenario:'wave',playing:true,speed:1,master:.65,bloom:.25,kelvin:4000,poolEffects:false,context:true,showNeon:true,materials:'original',savedView:null,groups:Object.fromEntries(GROUPS.map(g=>[g,{enabled:true,rgb:[...BASE_COLORS[g]],level:g==='ROOF'?.85:g==='POOL'?.22:.8,white:g==='POOL'?1:0}]))};}
const numeric=(v,d,a,b)=>Number.isFinite(Number(v))?Math.min(b,Math.max(a,Number(v))):d;
const oneOf=(v,values,d)=>values.includes(v)?v:d;
export function sanitize(input={}){
 if(!input||typeof input!=='object'||Array.isArray(input))throw new Error('Неверный формат настроек');
 const s=defaults();for(const [key,min,max] of [['time',0,23.99],['exposure',-2,2],['speed',.1,3],['master',0,1],['bloom',0,1],['kelvin',2700,6500]])s[key]=numeric(input[key],s[key],min,max);
 for(const k of ['playing','poolEffects','context','showNeon'])if(typeof input[k]==='boolean')s[k]=input[k];
 s.tab=oneOf(input.tab,['architecture','lighting'],s.tab);s.view=oneOf(input.view,[...Object.keys(PRESETS),'saved'],s.view);s.quality=oneOf(input.quality,['fast','balanced','cinematic'],s.quality);s.variant=oneOf(input.variant,['reference','cool','warm','lime','custom'],s.variant);s.scenario=oneOf(input.scenario,Object.keys(DESCRIPTIONS),s.scenario);s.materials=oneOf(input.materials,['original','clay','wire'],s.materials);s.reference=oneOf(String(input.reference),['','1','2','3','4','5','6'],'');
 for(const g of GROUPS){const q=input.groups?.[g];if(!q||typeof q!=='object')continue;const d=s.groups[g];if(typeof q.enabled==='boolean')d.enabled=q.enabled;d.level=numeric(q.level,d.level,0,1);d.white=numeric(q.white,d.white,0,1);if(Array.isArray(q.rgb)&&q.rgb.length===3)d.rgb=q.rgb.map((v,i)=>numeric(v,d.rgb[i],0,1));}
 const v=input.savedView;if(v&&[v.position,v.target].every(a=>Array.isArray(a)&&a.length===3&&a.every(x=>typeof x==='number'&&Number.isFinite(x)&&Math.abs(x)<2000))&&Math.hypot(...v.position.map((x,i)=>x-v.target[i]))>.01){s.savedView={name:'Мой ракурс',position:[...v.position],target:[...v.target],fov:numeric(v.fov,44,15,100),type:v.type==='ORTHO'?'ORTHO':'PERSP',orthoHeight:numeric(v.orthoHeight,50,2,500)};if(v.framing&&[v.framing.resolution,v.framing.principalPoint].every(a=>Array.isArray(a)&&a.length===2&&a.every(x=>typeof x==='number'&&Number.isFinite(x)&&x>=0&&x<10000))&&v.framing.resolution.every(x=>x>0))s.savedView.framing={resolution:[...v.framing.resolution],principalPoint:[...v.framing.principalPoint]};}
 if(s.view==='saved'&&!s.savedView)s.view='general';return s;
}
export function applyVariant(s,id){
 s.variant=id;for(const g of GROUPS){s.groups[g]={enabled:true,rgb:[...BASE_COLORS[g]],level:g==='ROOF'?.85:g==='POOL'?.22:.8,white:g==='POOL'?1:0};}
 if(id==='cool'){s.groups.ROOF.rgb=[.15,.03,.9];s.groups.BIG_FRAME.rgb=[.01,.5,.8];s.groups.UPPER_FRAME.rgb=[.05,.8,.5];s.kelvin=5500;}
 if(id==='warm'){for(const g of GROUPS){s.groups[g].rgb=[0,0,0];s.groups[g].white=1;s.groups[g].level=g==='POOL'?.22:.55;}s.kelvin=3000;}
 if(id==='lime'){s.groups.ROOF.rgb=[.45,.95,.025];s.groups.BIG_FRAME.rgb=[.15,.9,.08];s.groups.UPPER_FRAME.rgb=[.02,.9,.5];s.kelvin=4000;}
}
export function daylight(h){const x=Math.sin((h-6)*Math.PI/12);const f=Math.min(1,Math.max(0,(x+.5)/.9));return f*f*(3-2*f);}
export function clockLabel(h){const minutes=Math.min(1439,Math.round(h*60));return `${Math.floor(minutes/60).toString().padStart(2,'0')}:${(minutes%60).toString().padStart(2,'0')}`;}
export function programWeights(t){const knots=[[0,0],[3,0],[5,2],[12,2],[14,3],[22,3],[24,1],[28,1],[30,0]];t=((t%30)+30)%30;const out=[0,0,0,0];for(let i=0;i<knots.length-1;i++){const [a,ma]=knots[i],[b,mb]=knots[i+1];if(t>=a&&t<=b){let f=(t-a)/(b-a);f=f*f*(3-2*f);out[ma]+=1-f;out[mb]+=f;break;}}return out;}
export function kelvinRGB(k){k=Math.max(1000,Math.min(40000,k))/100;const r=k<=66?255:329.698727446*Math.pow(k-60,-.1332047592);const g=k<=66?99.4708025861*Math.log(k)-161.1195681661:288.1221695283*Math.pow(k-60,-.0755148492);const b=k>=66?255:k<=19?0:138.5177312231*Math.log(k-10)-305.0447927307;return [r,g,b].map(x=>Math.min(1,Math.max(0,x/255)));}

export function environmentLighting(h){
 const day=daylight(h);const altitude=Math.sin((h-6)*Math.PI/12);let direct=Math.max(0,Math.min(1,altitude/.35));direct=direct*direct*(3-2*direct);
 return {day,sun:2.6*direct+.012*(1-direct),hemisphere:.075+.775*day,fill:.045+.505*day,environment:.035+.505*day};
}
